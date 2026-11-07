"""Тесты построения графа обходом в ширину."""
import os
import unittest

from depgraph.cli import EXIT_FAILURE, EXIT_OK
from depgraph.filerepo import load_file_repo
from depgraph.graph import GraphError, build_graph, find_cycles
from tests import EXAMPLES_DIR
from tests.support import run_quiet


def build(name, root="A", depth=10, substring=""):
    """Строит граф по файлу из examples."""
    repo = load_file_repo(os.path.join(EXAMPLES_DIR, name))
    return build_graph(root, repo.dependencies, depth, substring)


class BuildGraphTests(unittest.TestCase):
    """Обход, глубина, фильтр и циклы."""

    def test_bfs_order(self):
        """Узлы обнаруживаются по уровням."""
        graph = build("tree.txt")
        self.assertEqual(list(graph.children), list("ABCDEF"))
        self.assertEqual(graph.depths["F"], 2)

    def test_shared_node_once(self):
        """Узел, достижимый разными путями, в графе один."""
        graph = build("diamond.txt")
        self.assertEqual(list(graph.children), list("ABCD"))
        self.assertEqual(graph.edge_count(), 4)

    def test_depth_limit(self):
        """Узлы глубже предела не попадают в граф."""
        graph = build("chain.txt", depth=2)
        self.assertEqual(list(graph.children), list("ABC"))
        self.assertEqual(graph.children["C"], [])

    def test_depth_one_is_direct_dependencies(self):
        """Глубина 1 даёт только прямые зависимости."""
        graph = build("tree.txt", depth=1)
        self.assertEqual(list(graph.children), list("ABC"))

    def test_filter(self):
        """Пакеты с подстрокой в имени исключаются вместе с рёбрами."""
        graph = build("filter.txt", root="APP", substring="LIB")
        self.assertEqual(list(graph.children), ["APP", "CORE"])
        self.assertEqual(graph.children["APP"], ["CORE"])

    def test_filter_excludes_root(self):
        """Если корень исключён фильтром — ошибка."""
        with self.assertRaises(GraphError):
            build("filter.txt", root="APP", substring="APP")

    def test_cycle_terminates(self):
        """Цикл не приводит к зависанию, замыкающее ребро сохранено."""
        graph = build("cycle.txt")
        self.assertEqual(list(graph.children), list("ABCD"))
        self.assertIn("A", graph.children["C"])
        self.assertEqual(find_cycles(graph), [["A", "B", "C", "A"]])

    def test_self_loop(self):
        """Зависимость пакета от самого себя считается циклом."""
        graph = build("self_loop.txt")
        self.assertEqual(find_cycles(graph), [["A", "A"]])

    def test_no_cycles_in_tree(self):
        """В дереве и ромбе циклов нет."""
        self.assertEqual(find_cycles(build("tree.txt")), [])
        self.assertEqual(find_cycles(build("diamond.txt")), [])


class CliTests(unittest.TestCase):
    """Запуск приложения в тестовом режиме."""

    def call(self, *argv):
        """Запускает run, возвращает (код, stdout, stderr)."""
        return run_quiet(list(argv))

    def path(self, name):
        """Путь к файлу примера."""
        return os.path.join(EXAMPLES_DIR, name)

    def test_cycle_report(self):
        """В отчёте перечислены циклические зависимости."""
        code, out, _ = self.call("-p", "A", "-r", self.path("cycle.txt"), "-t")
        self.assertEqual(code, EXIT_OK)
        self.assertIn("Циклические зависимости (1):", out)
        self.assertIn("A -> B -> C -> A", out)

    def test_depth_option(self):
        """Параметр --max-depth ограничивает граф."""
        _, out, _ = self.call("-p", "A", "-r", self.path("chain.txt"), "-t",
                              "-d", "2")
        self.assertIn("Узлов: 3, рёбер: 2", out)

    def test_unknown_package(self):
        """Неизвестный пакет — код ошибки и сообщение."""
        code, _, err = self.call("-p", "Z", "-r", self.path("tree.txt"), "-t")
        self.assertEqual(code, EXIT_FAILURE)
        self.assertIn("не найден", err)

    def test_broken_file(self):
        """Файл неверного формата — код ошибки."""
        code, _, err = self.call("-p", "A", "-r", __file__, "-t")
        self.assertEqual(code, EXIT_FAILURE)
        self.assertIn("строка", err)


if __name__ == "__main__":
    unittest.main()
