"""Параметры командной строки и их проверка."""
from __future__ import annotations

import argparse
import os
import re
from dataclasses import asdict, dataclass
from urllib.parse import urlparse

PROGRAM = "depgraph"
PACKAGE_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._+-]*$")
VERSION_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._+~-]*$")
URL_SCHEMES = ("http", "https", "file")
PNG_SUFFIX = ".png"
DEFAULT_OUTPUT = "graph.png"
DEFAULT_DEPTH = 3
MIN_DEPTH = 1


class ConfigError(ValueError):
    """Ошибка в сочетании параметров командной строки."""


@dataclass
class Config:
    """Все параметры, которые задаёт пользователь."""

    package: str
    repo: str
    test_mode: bool
    version: str
    output: str
    ascii_tree: bool
    max_depth: int
    filter_substring: str
    show_params: bool


def package_name(value):
    """Проверяет имя пакета."""
    if not PACKAGE_PATTERN.match(value):
        raise argparse.ArgumentTypeError(
            f"недопустимое имя пакета {value!r}: разрешены латинские "
            "буквы, цифры и символы . _ + -"
        )
    return value


def version_text(value):
    """Проверяет строку версии пакета."""
    if not VERSION_PATTERN.match(value):
        raise argparse.ArgumentTypeError(
            f"недопустимая версия {value!r}: разрешены латинские "
            "буквы, цифры и символы . _ + ~ -"
        )
    return value


def non_empty(value):
    """Требует непустое значение."""
    if not value.strip():
        raise argparse.ArgumentTypeError("значение не может быть пустым")
    return value


def positive_int(value):
    """Проверяет, что значение — целое число не меньше MIN_DEPTH."""
    try:
        number = int(value)
    except ValueError:
        raise argparse.ArgumentTypeError(
            f"ожидалось целое число, получено {value!r}"
        ) from None
    if number < MIN_DEPTH:
        raise argparse.ArgumentTypeError(
            f"глубина должна быть не меньше {MIN_DEPTH}, получено {number}"
        )
    return number


def png_name(value):
    """Проверяет, что имя файла изображения оканчивается на .png."""
    if not value.lower().endswith(PNG_SUFFIX):
        raise argparse.ArgumentTypeError(
            f"имя файла изображения должно оканчиваться на {PNG_SUFFIX}"
        )
    return value


def filter_text(value):
    """Подстрока фильтра не должна содержать пробельных символов."""
    if any(char.isspace() for char in value):
        raise argparse.ArgumentTypeError(
            "подстрока фильтра не должна содержать пробелов"
        )
    return value


def add_source_options(parser):
    """Добавляет параметры источника данных."""
    parser.add_argument(
        "-p", "--package", required=True, type=package_name,
        metavar="NAME", help="имя анализируемого пакета",
    )
    parser.add_argument(
        "-r", "--repo", required=True, type=non_empty, metavar="URL|FILE",
        help="URL репозитория или путь к файлу тестового репозитория",
    )
    parser.add_argument(
        "-t", "--test-mode", action="store_true",
        help="считать --repo путём к файлу тестового репозитория",
    )
    parser.add_argument(
        "-V", "--pkg-version", type=version_text, metavar="VERSION",
        help="версия пакета (обязательна для реального репозитория)",
    )


def add_graph_options(parser):
    """Добавляет параметры анализа графа."""
    parser.add_argument(
        "-d", "--max-depth", type=positive_int, default=DEFAULT_DEPTH,
        metavar="N",
        help=f"максимальная глубина анализа (по умолчанию {DEFAULT_DEPTH})",
    )
    parser.add_argument(
        "-f", "--filter", dest="filter_substring", type=filter_text,
        default="", metavar="TEXT",
        help="не учитывать пакеты, в имени которых есть эта подстрока",
    )


def add_output_options(parser):
    """Добавляет параметры вывода."""
    parser.add_argument(
        "-o", "--output", type=png_name, default=DEFAULT_OUTPUT,
        metavar="FILE.png",
        help=f"имя файла с изображением графа (по умолчанию {DEFAULT_OUTPUT})",
    )
    parser.add_argument(
        "-a", "--ascii-tree", action="store_true",
        help="вывести зависимости в виде ASCII-дерева",
    )
    parser.add_argument(
        "--show-params", action="store_true",
        help="напечатать все параметры в формате ключ=значение",
    )


def build_parser():
    """Создаёт разборщик командной строки."""
    parser = argparse.ArgumentParser(
        prog=PROGRAM,
        description="Визуализация графа зависимостей пакетов Alpine Linux.",
    )
    add_source_options(parser)
    add_graph_options(parser)
    add_output_options(parser)
    return parser


def validate_repo(config):
    """Проверяет значение --repo в зависимости от режима работы."""
    if config.test_mode:
        if not os.path.isfile(config.repo):
            raise ConfigError(
                f"файл тестового репозитория не найден: {config.repo}"
            )
        return
    parts = urlparse(config.repo)
    if parts.scheme not in URL_SCHEMES:
        raise ConfigError(
            "ожидается URL со схемой http, https или file; для файла "
            "тестового репозитория добавьте --test-mode"
        )
    if parts.scheme != "file" and not parts.netloc:
        raise ConfigError("в URL репозитория не указан адрес сервера")


def validate_version(config):
    """Для реального репозитория версия пакета обязательна."""
    if not config.test_mode and not config.version:
        raise ConfigError(
            "для реального репозитория нужно указать версию: --pkg-version"
        )


def validate_output(config):
    """Папка для файла с изображением должна существовать."""
    folder = os.path.dirname(os.path.abspath(config.output))
    if not os.path.isdir(folder):
        raise ConfigError(f"папка для изображения не найдена: {folder}")


def validate_config(config):
    """Проверяет согласованность параметров между собой."""
    validate_repo(config)
    validate_version(config)
    validate_output(config)


def parse_args(argv=None):
    """Разбирает аргументы; при ошибке печатает сообщение и выходит."""
    parser = build_parser()
    args = parser.parse_args(argv)
    config = Config(
        package=args.package,
        repo=args.repo,
        test_mode=args.test_mode,
        version=args.pkg_version or "",
        output=args.output,
        ascii_tree=args.ascii_tree,
        max_depth=args.max_depth,
        filter_substring=args.filter_substring,
        show_params=args.show_params,
    )
    try:
        validate_config(config)
    except ConfigError as error:
        parser.error(str(error))
    return config


def format_params(config):
    """Строки «ключ=значение» для всех параметров пользователя."""
    return [f"{key}={value}" for key, value in asdict(config).items()]
