"""Запуск приложения из командной строки."""
from __future__ import annotations

import sys

from depgraph.apk import ApkError, load_index
from depgraph.config import format_params, parse_args
from depgraph.fetch import FetchError
from depgraph.filerepo import FileRepoError, load_file_repo
from depgraph.graph import GraphError, build_graph
from depgraph.report import describe

EXIT_OK = 0
EXIT_FAILURE = 1
APP_ERRORS = (ApkError, FetchError, FileRepoError, GraphError)


def fail(message, code):
    """Печатает сообщение об ошибке и возвращает код завершения."""
    print(f"Ошибка: {message}", file=sys.stderr)
    return code


def load_source(config):
    """Открывает тестовый файл или реальный репозиторий."""
    if config.test_mode:
        return load_file_repo(config.repo)
    return load_index(config.repo)


def execute(config):
    """Строит граф зависимостей и печатает его описание."""
    source = load_source(config)
    source.check_root(config.package, config.version)
    neighbors = source.dependents if config.reverse else source.dependencies
    graph = build_graph(
        config.package, neighbors, config.max_depth,
        config.filter_substring, config.reverse,
    )
    for line in describe(graph, config.max_depth):
        print(line)
    return EXIT_OK


def run(argv=None):
    """Выполняет программу и возвращает код завершения."""
    config = parse_args(argv)
    if config.show_params:
        for line in format_params(config):
            print(line)
    try:
        return execute(config)
    except APP_ERRORS as error:
        return fail(str(error), EXIT_FAILURE)
