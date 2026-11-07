"""Тестовый репозиторий: граф зависимостей из текстового файла."""
from __future__ import annotations

import re

LINE_PATTERN = re.compile(r"^([A-Z]+)\s*:\s*([A-Z\s]*)$")
COMMENT_PREFIX = "#"


class FileRepoError(Exception):
    """Ошибка чтения или разбора файла тестового репозитория."""


def parse_line(number, line):
    """Разбирает строку «A: B C» в пару (имя, список зависимостей)."""
    match = LINE_PATTERN.match(line)
    if not match:
        raise FileRepoError(
            f"строка {number}: ожидается вид «A: B C» "
            "(имена из больших латинских букв)"
        )
    return match.group(1), list(dict.fromkeys(match.group(2).split()))


def parse_text(text):
    """Разбирает весь файл; возвращает словарь «имя -> зависимости»."""
    graph = {}
    for number, line in enumerate(text.splitlines(), start=1):
        stripped = line.strip()
        if not stripped or stripped.startswith(COMMENT_PREFIX):
            continue
        name, dependencies = parse_line(number, stripped)
        if name in graph:
            raise FileRepoError(f"строка {number}: пакет {name} уже описан")
        graph[name] = dependencies
    if not graph:
        raise FileRepoError("файл не содержит ни одного пакета")
    return graph


class FileRepo:
    """Источник зависимостей, заданных в тестовом файле."""

    def __init__(self, graph):
        """Запоминает граф и множество всех упомянутых пакетов."""
        self.graph = graph
        self.reverse = None
        self.names = set(graph)
        for dependencies in graph.values():
            self.names.update(dependencies)

    def check_root(self, name, version):
        """Проверяет, что пакет есть в файле; версия не используется."""
        if name not in self.names:
            known = ", ".join(sorted(self.names))
            raise FileRepoError(
                f"пакет {name} не найден в тестовом репозитории; "
                f"есть пакеты: {known}"
            )
        return name

    def dependencies(self, name):
        """Прямые зависимости пакета."""
        return list(self.graph.get(name, []))

    def dependents(self, name):
        """Пакеты, которые напрямую зависят от name."""
        if self.reverse is None:
            self.reverse = {}
            for owner, dependencies in self.graph.items():
                for target in dependencies:
                    self.reverse.setdefault(target, []).append(owner)
        return list(self.reverse.get(name, []))


def load_file_repo(path):
    """Читает файл тестового репозитория."""
    try:
        with open(path, encoding="utf-8-sig") as handle:
            text = handle.read()
    except (OSError, UnicodeDecodeError) as error:
        raise FileRepoError(f"не удалось прочитать {path}: {error}") from None
    return FileRepo(parse_text(text))
