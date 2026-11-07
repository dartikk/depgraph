"""Тесты режима обратных зависимостей."""
import contextlib
import io
import os
import unittest

from depgraph.apk import ApkIndex, parse_index
from depgraph.cli import EXIT_OK, run
from depgraph.filerepo import load_file_repo
from depgraph.graph import build_graph
from tests import EXAMPLES_DIR
from tests.support import INDEX_TEXT


def reverse_graph(name, root, depth=10, substring=""):
    """Граф обратных зависимостей по файлу из examples."""
    repo = load_file_repo(os.path.join(EXAMPLES_DIR, name))
    return build_graph(root, repo.dependents, depth, substring, True)


class DependentsTests(unittest.TestCase):
    """Прямые обратные зависимости источников."""

    def test_file_repo(self):
        """В тестовом репозитории находятся все зависящие пакеты."""
        repo = load_file_repo(os.path.join(EXAMPLES_DIR, "diamond.txt"))
        self.assertEqual(repo.dependents("D"), ["B", "C"])
        self.assertEqual(repo.dependents("A"), [])

    def test_apk_index(self):
        """В индексе Alpine учитываются зависимости через so:."""
        index = ApkIndex(parse_index(INDEX_TEXT))
        self.assertEqual(index.dependents("musl"), ["app", "libfoo", "busybox"])
        self.assertEqual(index.dependents("app"), [])


class ReverseGraphTests(unittest.TestCase):
    """Обход в ширину по обратным зависимостям."""

    def test_diamond(self):
        """Узлы обнаруживаются по уровням, повторов нет."""
        graph = reverse_graph("diamond.txt", "D")
        self.assertEqual(list(graph.children), list("DBCA"))
        self.assertTrue(graph.reverse)

    def test_depth_limit(self):
        """Глубина ограничивает обратный обход."""
        graph = reverse_graph("chain.txt", "E", depth=2)
        self.assertEqual(list(graph.children), list("EDC"))

    def test_filter(self):
        """Фильтр исключает пакеты и в обратном режиме."""
        graph = reverse_graph("filter.txt", "CORE", substring="LIB")
        self.assertEqual(list(graph.children), ["CORE", "APP", "UTIL"])

    def test_cycle_terminates(self):
        """Цикл не мешает обратному обходу."""
        graph = reverse_graph("cycle.txt", "A")
        self.assertEqual(list(graph.children), list("ACB"))


class ReverseCliTests(unittest.TestCase):
    """Запуск с параметром --reverse."""

    def call(self, *argv):
        """Запускает run, возвращает (код, stdout)."""
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = run(list(argv))
        return code, out.getvalue()

    def path(self, name):
        """Путь к файлу примера."""
        return os.path.join(EXAMPLES_DIR, name)

    def test_report(self):
        """В отчёте перечислены пакеты, зависящие от заданного."""
        code, out = self.call("-p", "D", "-r", self.path("diamond.txt"),
                              "-t", "--reverse")
        self.assertEqual(code, EXIT_OK)
        self.assertIn("Обратные зависимости пакета D", out)
        self.assertIn("B (глубина 1) -> зависит от: D", out)
        self.assertIn("A (глубина 2) -> зависит от: B, C", out)
        self.assertIn("Всего: 3", out)

    def test_nobody_depends(self):
        """Если зависящих пакетов нет, выводится «(нет)»."""
        _, out = self.call("-p", "A", "-r", self.path("tree.txt"),
                           "-t", "--reverse")
        self.assertIn("(нет)", out)
        self.assertIn("Всего: 0", out)

    def test_cycle_is_listed_in_dependency_direction(self):
        """Цикл печатается в направлении зависимостей."""
        _, out = self.call("-p", "A", "-r", self.path("cycle.txt"),
                           "-t", "--reverse")
        self.assertIn("A -> B -> C -> A", out)


if __name__ == "__main__":
    unittest.main()
