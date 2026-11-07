"""Запуск приложения из командной строки."""
from __future__ import annotations

import os
import sys

from depgraph.apk import ApkError, load_index
from depgraph.config import format_params, parse_args
from depgraph.fetch import FetchError
from depgraph.filerepo import FileRepoError, load_file_repo
from depgraph.graph import GraphError, build_graph
from depgraph.plantuml import to_plantuml
from depgraph.render import RenderError, render_png, save_bytes, save_text
from depgraph.report import describe
from depgraph.tree import render_tree

EXIT_OK = 0
EXIT_FAILURE = 1
PUML_SUFFIX = ".puml"
APP_ERRORS = (ApkError, FetchError, FileRepoError, GraphError, RenderError)


def fail(message, code):
    """Печатает сообщение об ошибке и возвращает код завершения."""
    print(f"Ошибка: {message}", file=sys.stderr)
    return code


def load_source(config):
    """Открывает тестовый файл или реальный репозиторий."""
    if config.test_mode:
        return load_file_repo(config.repo)
    return load_index(config.repo)


def show_tree(graph):
    """Печатает зависимости в виде ASCII-дерева."""
    kind = "обратных зависимостей" if graph.reverse else "зависимостей"
    print(f"Дерево {kind}:")
    for line in render_tree(graph):
        print(line)


def write_outputs(graph, config):
    """Сохраняет текст PlantUML и PNG-изображение графа."""
    text = to_plantuml(graph)
    puml_path = os.path.splitext(config.output)[0] + PUML_SUFFIX
    save_text(puml_path, text)
    print(f"Текст PlantUML сохранён: {puml_path}")
    save_bytes(config.output, render_png(text, config.plantuml_jar))
    print(f"Изображение графа сохранено: {config.output}")


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
    if config.ascii_tree:
        show_tree(graph)
    write_outputs(graph, config)
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
