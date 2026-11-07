"""Текстовое описание графа для вывода на экран."""
from __future__ import annotations

from depgraph.graph import find_cycles

EMPTY_MARK = "(нет)"


def describe(graph, max_depth):
    """Строки отчёта для прямого или обратного режима."""
    if graph.reverse:
        return describe_reverse(graph, max_depth)
    return describe_graph(graph, max_depth)


def describe_graph(graph, max_depth):
    """Строки с описанием графа: узлы, рёбра и найденные циклы."""
    lines = [
        f"Граф зависимостей пакета {graph.root} "
        f"(обход в ширину, глубина не более {max_depth})",
        f"Узлов: {len(graph.children)}, рёбер: {graph.edge_count()}",
    ]
    for node, children in graph.children.items():
        targets = ", ".join(children) if children else EMPTY_MARK
        lines.append(f"  {node} (глубина {graph.depths[node]}) -> {targets}")
    lines.extend(describe_cycles(find_cycles(graph)))
    return lines


def parents_of(graph):
    """Для каждого узла — узлы, из которых он достигнут обходом."""
    parents = {node: [] for node in graph.children}
    for node, children in graph.children.items():
        for child in children:
            parents[child].append(node)
    return parents


def describe_reverse(graph, max_depth):
    """Строки с обратными зависимостями: кто зависит от корня."""
    lines = [
        f"Обратные зависимости пакета {graph.root} "
        f"(пакеты, которые от него зависят), глубина не более {max_depth}:"
    ]
    parents = parents_of(graph)
    found = [node for node in graph.children if node != graph.root]
    for node in found:
        owners = ", ".join(parents[node])
        lines.append(
            f"  {node} (глубина {graph.depths[node]}) -> зависит от: {owners}"
        )
    if not found:
        lines.append(f"  {EMPTY_MARK}")
    lines.append(f"Всего: {len(found)}")
    cycles = [cycle[::-1] for cycle in find_cycles(graph)]
    lines.extend(describe_cycles(cycles))
    return lines


def describe_cycles(cycles):
    """Строки с описанием циклических зависимостей."""
    if not cycles:
        return ["Циклических зависимостей нет"]
    lines = [f"Циклические зависимости ({len(cycles)}):"]
    lines.extend("  " + " -> ".join(cycle) for cycle in cycles)
    return lines
