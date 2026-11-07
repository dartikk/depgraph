"""Граф зависимостей: построение обходом в ширину (BFS) без рекурсии."""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field

ON_PATH = "on_path"
DONE = "done"


class GraphError(Exception):
    """Ошибка построения графа."""


@dataclass
class Graph:
    """Граф: узлы хранятся в порядке обнаружения обходом в ширину."""

    root: str
    children: dict = field(default_factory=dict)
    depths: dict = field(default_factory=dict)
    reverse: bool = False

    def edge_count(self):
        """Число рёбер графа."""
        return sum(len(items) for items in self.children.values())


def is_excluded(name, substring):
    """Истина, если имя содержит подстроку фильтра."""
    return bool(substring) and substring in name


def build_graph(root, neighbors, max_depth, substring="", reverse=False):
    """Строит граф от root обходом в ширину.

    neighbors(name) возвращает соседей узла: зависимости пакета или, при
    reverse=True, пакеты, которые от него зависят. Узлы глубже max_depth не
    раскрываются, пакеты с подстрокой в имени пропускаются. Каждый узел
    обходится один раз, поэтому циклы не приводят к зависанию; ребро,
    замыкающее цикл, сохраняется в графе.
    """
    if is_excluded(root, substring):
        raise GraphError(
            f"пакет {root} исключён фильтром {substring!r}: граф пуст"
        )
    graph = Graph(root, {root: []}, {root: 0}, reverse)
    queue = deque([root])
    while queue:
        node = queue.popleft()
        if graph.depths[node] >= max_depth:
            continue
        for child in dict.fromkeys(neighbors(node)):
            if is_excluded(child, substring):
                continue
            graph.children[node].append(child)
            if child not in graph.depths:
                graph.depths[child] = graph.depths[node] + 1
                graph.children[child] = []
                queue.append(child)
    return graph


def find_cycles(graph):
    """Находит циклы итеративным обходом в глубину; цикл — список узлов."""
    cycles, state = [], {}
    for start in graph.children:
        if start not in state:
            collect_cycles(graph, start, state, cycles)
    return cycles


def collect_cycles(graph, start, state, cycles):
    """Обход в глубину от start; обратные рёбра дают циклы."""
    path = [start]
    iterators = [iter(graph.children[start])]
    state[start] = ON_PATH
    while path:
        child = next(iterators[-1], None)
        if child is None:
            state[path.pop()] = DONE
            iterators.pop()
        elif state.get(child) == ON_PATH:
            cycles.append(path[path.index(child):] + [child])
        elif child not in state:
            state[child] = ON_PATH
            path.append(child)
            iterators.append(iter(graph.children[child]))
