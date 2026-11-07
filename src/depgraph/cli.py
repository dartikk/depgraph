"""Запуск приложения из командной строки."""
from __future__ import annotations

import sys

from depgraph.apk import ApkError, load_index
from depgraph.config import format_params, parse_args
from depgraph.fetch import FetchError

EXIT_OK = 0
EXIT_FAILURE = 1
EXIT_USAGE = 2


def print_direct(package, dependencies):
    """Печатает прямые зависимости пакета."""
    print(f"Прямые зависимости пакета {package.name} ({package.version}):")
    if not dependencies:
        print("  (нет)")
    for name in dependencies:
        print(f"  {name}")


def fail(message, code):
    """Печатает сообщение об ошибке и возвращает код завершения."""
    print(f"Ошибка: {message}", file=sys.stderr)
    return code


def run(argv=None):
    """Выполняет программу и возвращает код завершения."""
    config = parse_args(argv)
    if config.show_params:
        for line in format_params(config):
            print(line)
    if config.test_mode:
        return fail("тестовый режим будет добавлен на этапе 3", EXIT_USAGE)
    try:
        index = load_index(config.repo)
        package = index.check_root(config.package, config.version)
    except (FetchError, ApkError) as error:
        return fail(str(error), EXIT_FAILURE)
    print_direct(package, index.dependencies(package.name))
    return EXIT_OK
