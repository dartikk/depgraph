"""Тесты чтения индекса Alpine и загрузки данных."""
import contextlib
import io
import os
import pathlib
import tempfile
import unittest

from depgraph.apk import (
    ApkError, ApkIndex, extract_index_text, parse_index, token_name,
)
from depgraph.cli import EXIT_FAILURE, EXIT_OK, run
from depgraph.fetch import FetchError, fetch_bytes, index_url
from tests.support import INDEX_TEXT, plain_archive, signed_archive


def make_index():
    """Индекс из тестового текста."""
    return ApkIndex(parse_index(INDEX_TEXT))


class ParseTests(unittest.TestCase):
    """Разбор текста APKINDEX."""

    def test_token_name(self):
        """Версии отбрасываются, конфликты пропускаются."""
        self.assertEqual(token_name("busybox>=1.30"), "busybox")
        self.assertEqual(token_name("so:libc.so.1=2"), "so:libc.so.1")
        self.assertIsNone(token_name("!conflict"))

    def test_parse_index(self):
        """Из текста получаются все записи с полями."""
        packages = parse_index(INDEX_TEXT)
        self.assertEqual([p.name for p in packages],
                         ["app", "libfoo", "musl", "busybox"])
        self.assertEqual(packages[1].provides, ["so:libfoo.so.2"])
        self.assertNotIn("conflict", packages[0].depends)

    def test_record_without_version_is_skipped(self):
        """Запись без P или V игнорируется."""
        self.assertEqual(parse_index("P:only-name\n\nV:1\n"), [])


class ArchiveTests(unittest.TestCase):
    """Извлечение APKINDEX из архива."""

    def test_plain_archive(self):
        """Обычный tar.gz читается."""
        text = extract_index_text(plain_archive(INDEX_TEXT))
        self.assertEqual(text, INDEX_TEXT)

    def test_signed_archive(self):
        """Архив из двух gzip-потоков (с подписью) читается."""
        text = extract_index_text(signed_archive(INDEX_TEXT))
        self.assertEqual(text, INDEX_TEXT)

    def test_garbage(self):
        """Мусор вместо архива даёт ApkError."""
        with self.assertRaises(ApkError):
            extract_index_text(b"not an archive")


class IndexTests(unittest.TestCase):
    """Поиск пакета и его прямых зависимостей."""

    def test_check_root(self):
        """Пакет находится по имени и версии."""
        package = make_index().check_root("app", "1.0-r0")
        self.assertEqual(package.version, "1.0-r0")

    def test_unknown_package(self):
        """Неизвестный пакет даёт ApkError."""
        with self.assertRaises(ApkError):
            make_index().check_root("nope", "1")

    def test_wrong_version_lists_known(self):
        """При неверной версии сообщение содержит доступные версии."""
        with self.assertRaises(ApkError) as caught:
            make_index().check_root("app", "9.9")
        self.assertIn("1.0-r0", str(caught.exception))

    def test_dependencies_are_resolved(self):
        """so:-зависимости заменяются пакетом-поставщиком."""
        deps = make_index().dependencies("app")
        self.assertEqual(deps, ["libfoo", "musl", "busybox", "missing-pkg"])

    def test_self_dependency_is_dropped(self):
        """Зависимость пакета от собственного so: не считается."""
        self.assertEqual(make_index().dependencies("libfoo"), ["musl"])


class FetchTests(unittest.TestCase):
    """Загрузка по URL (используется file://)."""

    def test_index_url(self):
        """К адресу репозитория добавляется имя архива."""
        self.assertEqual(index_url("http://h/r/"), "http://h/r/APKINDEX.tar.gz")
        self.assertEqual(index_url("http://h/APKINDEX.tar.gz"),
                         "http://h/APKINDEX.tar.gz")

    def test_missing_file(self):
        """Недоступный адрес даёт FetchError."""
        with self.assertRaises(FetchError):
            fetch_bytes("file:///no/such/APKINDEX.tar.gz")


class CliTests(unittest.TestCase):
    """Запуск приложения целиком на локальном репозитории."""

    def setUp(self):
        """Создаёт папку «репозитория» с архивом индекса."""
        self.folder = tempfile.TemporaryDirectory()
        path = os.path.join(self.folder.name, "APKINDEX.tar.gz")
        with open(path, "wb") as handle:
            handle.write(signed_archive(INDEX_TEXT))
        self.repo = pathlib.Path(self.folder.name).as_uri()

    def tearDown(self):
        """Удаляет временную папку."""
        self.folder.cleanup()

    def call(self, argv):
        """Запускает run и возвращает (код, stdout, stderr)."""
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = run(argv)
        return code, out.getvalue(), err.getvalue()

    def test_prints_direct_dependencies(self):
        """Для пакета заданной версии выводятся его зависимости."""
        code, out, _ = self.call(["-p", "app", "-r", self.repo,
                                  "-V", "1.0-r0", "-d", "1"])
        self.assertEqual(code, EXIT_OK)
        self.assertIn("app (глубина 0) -> libfoo, musl, busybox", out)

    def test_transitive_dependencies(self):
        """При большей глубине раскрываются зависимости зависимостей."""
        _, out, _ = self.call(["-p", "app", "-r", self.repo,
                               "-V", "1.0-r0", "-d", "2"])
        self.assertIn("libfoo (глубина 1) -> musl", out)

    def test_wrong_version(self):
        """Неверная версия — ошибка со списком доступных версий."""
        code, _, err = self.call(["-p", "app", "-r", self.repo, "-V", "2"])
        self.assertEqual(code, EXIT_FAILURE)
        self.assertIn("1.0-r0", err)

    def test_unreachable_repo(self):
        """Недоступный репозиторий — ошибка загрузки."""
        code, _, err = self.call(["-p", "app", "-V", "1",
                                  "-r", "file:///no/such/dir"])
        self.assertEqual(code, EXIT_FAILURE)
        self.assertIn("Ошибка", err)

    def test_show_params(self):
        """Флаг --show-params печатает параметры."""
        _, out, _ = self.call(["-p", "app", "-r", self.repo, "-V", "1.0-r0",
                               "--show-params"])
        self.assertIn("package=app", out)


if __name__ == "__main__":
    unittest.main()
