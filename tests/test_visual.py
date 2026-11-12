"""Тесты визуализации: PlantUML, ASCII-дерево, получение PNG."""
import contextlib
import io
import os
import subprocess
import tempfile
import unittest
import zlib
from unittest import mock

from depgraph.cli import EXIT_FAILURE, EXIT_OK, run
from depgraph.config import parse_args
from depgraph.fetch import FetchError
from depgraph.filerepo import load_file_repo
from depgraph.graph import build_graph
from depgraph.plantuml import to_plantuml
from depgraph.render import (
    ALPHABET, RenderError, encode_plantuml, render_png,
)
from depgraph.tree import render_tree
from tests import EXAMPLES_DIR
from tests.support import FAKE_PNG
GROUP_CHARS = 4


def graph_of(name, root="A", reverse=False, depth=10):
    """Граф по файлу из examples."""
    repo = load_file_repo(os.path.join(EXAMPLES_DIR, name))
    neighbors = repo.dependents if reverse else repo.dependencies
    return build_graph(root, neighbors, depth, "", reverse)


def decode_plantuml(encoded):
    """Обратное преобразование кодировки PlantUML (для проверки)."""
    values = [ALPHABET.index(char) for char in encoded]
    raw = bytearray()
    for start in range(0, len(values), GROUP_CHARS):
        one, two, three, four = values[start:start + GROUP_CHARS]
        raw.append((one << 2) | (two >> 4))
        raw.append(((two & 0x0F) << 4) | (three >> 2))
        raw.append(((three & 0x03) << 6) | four)
    return zlib.decompressobj(-zlib.MAX_WBITS).decompress(bytes(raw))


class EncodeTests(unittest.TestCase):
    """Кодирование текста для сервера PlantUML."""

    def test_roundtrip(self):
        """Закодированный текст восстанавливается обратным преобразованием."""
        for text in ("@startuml\nA --> B\n@enduml\n", "x", "Привет, мир"):
            data = decode_plantuml(encode_plantuml(text)).decode("utf-8")
            self.assertEqual(data, text)

    def test_alphabet_only(self):
        """В результате только символы алфавита PlantUML."""
        encoded = encode_plantuml("@startuml\nA --> B\n@enduml\n")
        self.assertTrue(set(encoded) <= set(ALPHABET))


class PlantUmlTests(unittest.TestCase):
    """Текст диаграммы."""

    def test_forward(self):
        """Узлы объявлены, рёбра идут от пакета к его зависимости."""
        text = to_plantuml(graph_of("cycle.txt"))
        self.assertTrue(text.startswith("@startuml\n"))
        self.assertTrue(text.endswith("@enduml\n"))
        self.assertIn('rectangle "A" as n0 #LightBlue', text)
        self.assertIn("n0 --> n1", text)
        self.assertIn("n2 --> n0", text)

    def test_reverse_edges_follow_dependencies(self):
        """В обратном режиме стрелки всё равно идут от зависящего пакета."""
        text = to_plantuml(graph_of("diamond.txt", "D", reverse=True))
        self.assertIn("Обратные зависимости пакета D", text)
        self.assertIn("n1 --> n0", text)


class TreeTests(unittest.TestCase):
    """ASCII-дерево."""

    def test_tree(self):
        """Дерево рисуется символами ветвления."""
        lines = render_tree(graph_of("tree.txt"))
        self.assertEqual(lines, [
            "A", "├── B", "│   ├── D", "│   └── E", "└── C", "    └── F",
        ])

    def test_repeat_is_marked(self):
        """Повторно встреченный узел помечается и не раскрывается."""
        lines = render_tree(graph_of("diamond.txt"))
        self.assertEqual(lines[-1], "    └── D (повтор)")

    def test_cycle_is_marked(self):
        """Узел, замыкающий цикл, помечается."""
        lines = render_tree(graph_of("cycle.txt"))
        self.assertIn("        ├── A (цикл)", lines)

    def test_self_loop(self):
        """Зависимость от самого себя помечается как цикл."""
        lines = render_tree(graph_of("self_loop.txt"))
        self.assertEqual(lines[1], "├── A (цикл)")


class RenderTests(unittest.TestCase):
    """Получение PNG (внешние вызовы подменены)."""

    def test_server(self):
        """Сервер вызывается с закодированным текстом."""
        with mock.patch("depgraph.render.fetch_bytes",
                        return_value=FAKE_PNG) as fetch:
            self.assertEqual(render_png("@startuml\n@enduml\n"), FAKE_PNG)
        self.assertIn("plantuml.com/plantuml/png/", fetch.call_args[0][0])

    def test_server_not_png(self):
        """Ответ без сигнатуры PNG — ошибка."""
        with mock.patch("depgraph.render.fetch_bytes", return_value=b"x"):
            with self.assertRaises(RenderError):
                render_png("text")

    def test_server_unreachable(self):
        """Сбой сети превращается в RenderError с подсказкой."""
        with mock.patch("depgraph.render.fetch_bytes",
                        side_effect=FetchError("нет сети")):
            with self.assertRaises(RenderError) as caught:
                render_png("text")
        self.assertIn("--plantuml-jar", str(caught.exception))

    def test_jar(self):
        """Локальный PlantUML получает текст через stdin."""
        done = subprocess.CompletedProcess([], 0, FAKE_PNG, b"")
        with mock.patch("depgraph.render.subprocess.run",
                        return_value=done) as runner:
            self.assertEqual(render_png("text", "x.jar"), FAKE_PNG)
        self.assertEqual(runner.call_args.kwargs["input"], b"text")

    def test_jar_errors(self):
        """Ошибка PlantUML и отсутствие java дают RenderError."""
        failed = subprocess.CompletedProcess([], 1, b"", b"boom")
        with mock.patch("depgraph.render.subprocess.run",
                        return_value=failed):
            with self.assertRaises(RenderError):
                render_png("text", "x.jar")
        with mock.patch("depgraph.render.subprocess.run",
                        side_effect=FileNotFoundError):
            with self.assertRaises(RenderError):
                render_png("text", "x.jar")


class CliTests(unittest.TestCase):
    """Запуск приложения с выводом дерева и файлов."""

    def set_up(self):
        """Создаёт временную папку для результатов."""
        self.folder = tempfile.TemporaryDirectory()
        self.png = os.path.join(self.folder.name, "g.png")
        self.puml = os.path.join(self.folder.name, "g.puml")

    def tear_down(self):
        """Удаляет временную папку."""
        self.folder.cleanup()

    def call(self, *extra):
        """Запускает run на cycle.txt, возвращает (код, stdout, stderr)."""
        argv = ["-p", "A", "-t", "-o", self.png,
                "-r", os.path.join(EXAMPLES_DIR, "cycle.txt")] + list(extra)
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = run(argv)
        return code, out.getvalue(), err.getvalue()

    def test_files_and_tree(self):
        """Создаются .puml и .png, дерево печатается по флагу."""
        with mock.patch("depgraph.cli.render_png", return_value=FAKE_PNG):
            code, out, _ = self.call("-a")
        self.assertEqual(code, EXIT_OK)
        self.assertIn("Дерево зависимостей:", out)
        self.assertIn("A (цикл)", out)
        with open(self.puml, encoding="utf-8") as handle:
            self.assertIn("@startuml", handle.read())
        with open(self.png, "rb") as handle:
            self.assertEqual(handle.read(), FAKE_PNG)

    def test_no_tree_without_flag(self):
        """Без --ascii-tree дерево не печатается."""
        with mock.patch("depgraph.cli.render_png", return_value=FAKE_PNG):
            _, out, _ = self.call()
        self.assertNotIn("Дерево", out)

    def test_render_failure_keeps_puml(self):
        """Если PNG получить не удалось, текст PlantUML всё равно сохранён."""
        with mock.patch("depgraph.cli.render_png",
                        side_effect=RenderError("нет сети")):
            code, _, err = self.call()
        self.assertEqual(code, EXIT_FAILURE)
        self.assertIn("нет сети", err)
        self.assertTrue(os.path.isfile(self.puml))
        self.assertFalse(os.path.exists(self.png))

    def test_missing_jar_rejected(self):
        """Несуществующий jar-файл отвергается при разборе параметров."""
        err = io.StringIO()
        argv = ["-p", "A", "-t", "-r", os.path.join(EXAMPLES_DIR, "tree.txt"),
                "--plantuml-jar", "no_such.jar"]
        with contextlib.redirect_stderr(err):
            with self.assertRaises(SystemExit):
                parse_args(argv)
        self.assertIn("файл не найден", err.getvalue())


setattr(CliTests, "setUp", CliTests.set_up)
setattr(CliTests, "tearDown", CliTests.tear_down)


if __name__ == "__main__":
    unittest.main()
