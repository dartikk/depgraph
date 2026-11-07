"""Запуск приложения из командной строки."""
from __future__ import annotations

from depgraph.config import format_params, parse_args

EXIT_OK = 0


def run(argv=None):
    """Разбирает параметры, печатает их и возвращает код завершения."""
    config = parse_args(argv)
    for line in format_params(config):
        print(line)
    return EXIT_OK
