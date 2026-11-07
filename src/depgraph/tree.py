"""Вывод графа зависимостей в виде ASCII-дерева (без рекурсии)."""
from __future__ import annotations

BRANCH = "├── "
LAST = "└── "
PIPE = "│   "
SPACE = "    "
CYCLE_MARK = " (цикл)"
REPEAT_MARK = " (повтор)"


def child_frames(graph, name, prefix, ancestors):
    """Кадры детей узла в обратном порядке: так их удобно брать из стека."""
    children = graph.children[name]
    last_index = len(children) - 1
    frames = [
        (child, prefix, position == last_index, ancestors)
        for position, child in enumerate(children)
    ]
    frames.reverse()
    return frames


def node_mark(name, ancestors, expanded):
    """Пометка для узла: цикл, повтор или пустая строка."""
    if name in ancestors:
        return CYCLE_MARK
    if name in expanded:
        return REPEAT_MARK
    return ""


def render_tree(graph):
    """Строки дерева: узел, уже встречавшийся выше, не раскрывается."""
    lines = [graph.root]
    expanded = {graph.root}
    stack = child_frames(graph, graph.root, "", (graph.root,))
    while stack:
        name, prefix, is_last, ancestors = stack.pop()
        mark = node_mark(name, ancestors, expanded)
        lines.append(prefix + (LAST if is_last else BRANCH) + name + mark)
        if mark:
            continue
        expanded.add(name)
        next_prefix = prefix + (SPACE if is_last else PIPE)
        stack.extend(
            child_frames(graph, name, next_prefix, ancestors + (name,))
        )
    return lines
