"""Текстовое представление графа на языке диаграмм PlantUML."""
from __future__ import annotations

ROOT_COLOR = "#LightBlue"
FORWARD_TITLE = "Зависимости пакета"
REVERSE_TITLE = "Обратные зависимости пакета"


def quote(name):
    """Имя узла для строки в двойных кавычках."""
    return name.replace('"', "'")


def edge_pairs(graph):
    """Пары (от кого, к кому) в направлении зависимостей."""
    for node, children in graph.children.items():
        for child in children:
            yield (child, node) if graph.reverse else (node, child)


def to_plantuml(graph):
    """Возвращает текст диаграммы PlantUML для графа."""
    aliases = {name: f"n{number}" for number, name in enumerate(graph.children)}
    title = REVERSE_TITLE if graph.reverse else FORWARD_TITLE
    lines = ["@startuml", f"title {title} {quote(graph.root)}",
             "skinparam shadowing false"]
    for name, alias in aliases.items():
        color = f" {ROOT_COLOR}" if name == graph.root else ""
        lines.append(f'rectangle "{quote(name)}" as {alias}{color}')
    for source, target in edge_pairs(graph):
        lines.append(f"{aliases[source]} --> {aliases[target]}")
    lines.append("@enduml")
    return "\n".join(lines) + "\n"
