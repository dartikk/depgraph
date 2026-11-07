"""Тесты разбора и проверки параметров командной строки."""
import contextlib
import io
import os
import tempfile
import unittest

from depgraph.config import (
    DEFAULT_DEPTH, DEFAULT_OUTPUT, format_params, parse_args,
)

REPO = "https://example.org/alpine/main/x86_64"
REAL = ["-p", "nginx", "-r", REPO, "-V", "1.0-r0"]


class ParseArgsTests(unittest.TestCase):
    """Проверки функции parse_args."""

    def fail_text(self, argv):
        """Возвращает текст ошибки; проверяет, что разбор завершился ошибкой."""
        buffer = io.StringIO()
        with contextlib.redirect_stderr(buffer):
            with self.assertRaises(SystemExit):
                parse_args(argv)
        return buffer.getvalue()

    def test_defaults(self):
        """Необязательные параметры получают значения по умолчанию."""
        config = parse_args(REAL)
        self.assertEqual(config.package, "nginx")
        self.assertEqual(config.version, "1.0-r0")
        self.assertEqual(config.output, DEFAULT_OUTPUT)
        self.assertEqual(config.max_depth, DEFAULT_DEPTH)
        self.assertFalse(config.ascii_tree)
        self.assertFalse(config.test_mode)
        self.assertEqual(config.filter_substring, "")

    def test_all_options(self):
        """Все параметры принимаются в полной форме."""
        argv = REAL + ["-o", "x.png", "-a", "-d", "5", "-f", "lib"]
        config = parse_args(argv)
        self.assertEqual(config.output, "x.png")
        self.assertTrue(config.ascii_tree)
        self.assertEqual(config.max_depth, 5)
        self.assertEqual(config.filter_substring, "lib")

    def test_test_mode_with_existing_file(self):
        """В тестовом режиме версия не нужна, файл должен существовать."""
        with tempfile.TemporaryDirectory() as folder:
            path = os.path.join(folder, "repo.txt")
            with open(path, "w", encoding="utf-8") as handle:
                handle.write("A: B\n")
            config = parse_args(["-p", "A", "-r", path, "-t"])
        self.assertTrue(config.test_mode)
        self.assertEqual(config.version, "")

    def test_missing_required(self):
        """Без имени пакета и репозитория выдаётся ошибка."""
        self.assertIn("required", self.fail_text(["-r", REPO]))
        self.assertIn("required", self.fail_text(["-p", "nginx"]))

    def test_bad_package_name(self):
        """Имя пакета с недопустимыми символами отвергается."""
        text = self.fail_text(["-p", "bad name!", "-r", REPO, "-V", "1"])
        self.assertIn("недопустимое имя пакета", text)

    def test_bad_version(self):
        """Версия с недопустимыми символами отвергается."""
        argv = ["-p", "nginx", "-r", REPO, "-V", "1 0"]
        self.assertIn("недопустимая версия", self.fail_text(argv))

    def test_version_required_for_real_repo(self):
        """Для реального репозитория версия обязательна."""
        text = self.fail_text(["-p", "nginx", "-r", REPO])
        self.assertIn("нужно указать версию", text)

    def test_bad_depth(self):
        """Глубина должна быть положительным целым числом."""
        self.assertIn("целое число", self.fail_text(REAL + ["-d", "abc"]))
        self.assertIn("не меньше", self.fail_text(REAL + ["-d", "0"]))
        self.assertIn("не меньше", self.fail_text(REAL + ["-d", "-2"]))

    def test_bad_output(self):
        """Файл изображения должен иметь расширение .png."""
        text = self.fail_text(REAL + ["-o", "graph.jpg"])
        self.assertIn(".png", text)

    def test_output_folder_must_exist(self):
        """Папка для изображения должна существовать."""
        text = self.fail_text(REAL + ["-o", "no/such/dir/x.png"])
        self.assertIn("папка для изображения не найдена", text)

    def test_bad_filter(self):
        """Подстрока фильтра не может содержать пробелов."""
        self.assertIn("пробелов", self.fail_text(REAL + ["-f", "a b"]))

    def test_bad_repo_url(self):
        """Репозиторий без схемы http/https/file отвергается."""
        argv = ["-p", "nginx", "-r", "ftp://x/y", "-V", "1"]
        self.assertIn("ожидается URL", self.fail_text(argv))
        argv = ["-p", "nginx", "-r", "https://", "-V", "1"]
        self.assertIn("не указан адрес", self.fail_text(argv))

    def test_missing_test_repo_file(self):
        """Несуществующий файл тестового репозитория отвергается."""
        argv = ["-p", "A", "-r", "no_such_file.txt", "-t"]
        self.assertIn("файл тестового репозитория", self.fail_text(argv))

    def test_format_params(self):
        """Параметры выводятся в формате ключ=значение."""
        lines = format_params(parse_args(REAL))
        self.assertIn("package=nginx", lines)
        self.assertIn("max_depth=3", lines)
        self.assertIn("test_mode=False", lines)


if __name__ == "__main__":
    unittest.main()
