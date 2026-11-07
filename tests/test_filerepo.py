"""Тесты тестового репозитория из файла."""
import os
import unittest

from depgraph.filerepo import (
    FileRepoError, FileRepo, load_file_repo, parse_text,
)
from tests import EXAMPLES_DIR


class ParseTextTests(unittest.TestCase):
    """Разбор текста файла."""

    def test_valid(self):
        """Строки, комментарии и пустые строки разбираются."""
        graph = parse_text("# комментарий\n\nA: B C\nB:\nC: B B\n")
        self.assertEqual(graph, {"A": ["B", "C"], "B": [], "C": ["B"]})

    def test_bad_line(self):
        """Строка не по формату даёт ошибку с номером."""
        with self.assertRaises(FileRepoError) as caught:
            parse_text("A: B\nэто неверно\n")
        self.assertIn("строка 2", str(caught.exception))

    def test_lowercase_names_rejected(self):
        """Имена должны состоять из больших латинских букв."""
        for text in ("a: B\n", "A: b\n", "A1: B\n"):
            with self.assertRaises(FileRepoError):
                parse_text(text)

    def test_duplicate(self):
        """Повторное описание пакета — ошибка."""
        with self.assertRaises(FileRepoError):
            parse_text("A: B\nA: C\n")

    def test_empty(self):
        """Файл без пакетов — ошибка."""
        with self.assertRaises(FileRepoError):
            parse_text("# только комментарий\n")


class FileRepoTests(unittest.TestCase):
    """Поведение источника зависимостей."""

    def test_names_include_referenced(self):
        """Пакет, упомянутый только в зависимостях, считается существующим."""
        repo = FileRepo({"A": ["B"]})
        self.assertEqual(repo.check_root("B", ""), "B")
        self.assertEqual(repo.dependencies("B"), [])

    def test_unknown_root(self):
        """Неизвестный пакет даёт ошибку со списком пакетов."""
        with self.assertRaises(FileRepoError) as caught:
            FileRepo({"A": []}).check_root("Z", "")
        self.assertIn("A", str(caught.exception))

    def test_load_missing_file(self):
        """Отсутствующий файл даёт FileRepoError."""
        with self.assertRaises(FileRepoError):
            load_file_repo("no_such_file.txt")

    def test_load_examples(self):
        """Все примеры из папки examples корректны."""
        for name in sorted(os.listdir(EXAMPLES_DIR)):
            repo = load_file_repo(os.path.join(EXAMPLES_DIR, name))
            self.assertTrue(repo.names, name)


if __name__ == "__main__":
    unittest.main()
