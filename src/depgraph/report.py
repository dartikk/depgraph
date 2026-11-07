"""Текстовое описание графа для вывода на экран."""
from __future__ import annotations

from depgraph.graph import find_cycles

EMPTY_MARK = "(нет)"


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


def describe_cycles(cycles):
    """Строки с описанием циклических зависимостей."""
    if not cycles:
        return ["Циклических зависимостей нет"]
    lines = [f"Циклические зависимости ({len(cycles)}):"]
    lines.extend("  " + " -> ".join(cycle) for cycle in cycles)
    return lines
