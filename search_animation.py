"""Steppable search generators for pygame animation."""
from __future__ import annotations

from collections import deque
from heapq import heappop, heappush
from typing import Dict, Generator, List, Optional, Set, Tuple

from algorithms import ExpandEvent, SearchStats, _meet_path, neighbors4, reconstruct

Cell = Tuple[int, int]
SearchResult = Tuple[Optional[List[Cell]], SearchStats]


def animate_bfs(
    start: Cell,
    goal: Cell,
    walls: Set[Cell],
    rows: int,
    cols: int,
) -> Generator[ExpandEvent, None, SearchResult]:
    if start == goal:
        return [start], SearchStats(expanded=0, path_steps=0)
    if start in walls or goal in walls:
        return None, SearchStats(expanded=0, path_steps=0)

    q: deque[Cell] = deque([start])
    parent: Dict[Cell, Optional[Cell]] = {start: None}
    expanded = 0

    while q:
        cell = q.popleft()
        expanded += 1
        yield ("bfs", cell)
        if cell == goal:
            path = reconstruct(parent, goal, start)
            return path, SearchStats(expanded=expanded, path_steps=max(0, len(path) - 1))
        r, c = cell
        for nxt in neighbors4(r, c, rows, cols):
            if nxt in walls or nxt in parent:
                continue
            parent[nxt] = cell
            q.append(nxt)

    return None, SearchStats(expanded=expanded, path_steps=0)


def animate_astar(
    start: Cell,
    goal: Cell,
    walls: Set[Cell],
    rows: int,
    cols: int,
) -> Generator[ExpandEvent, None, SearchResult]:
    if start == goal:
        return [start], SearchStats(expanded=0, path_steps=0)
    if start in walls or goal in walls:
        return None, SearchStats(expanded=0, path_steps=0)

    def h(cell: Cell) -> int:
        return abs(cell[0] - goal[0]) + abs(cell[1] - goal[1])

    open_heap: List[Tuple[int, int, int, Cell]] = []
    g_score: Dict[Cell, int] = {start: 0}
    parent: Dict[Cell, Optional[Cell]] = {start: None}
    closed: Set[Cell] = set()
    counter = 0
    heappush(open_heap, (h(start), -0, counter, start))
    expanded = 0

    while open_heap:
        _, neg_g, _, cell = heappop(open_heap)
        if cell in closed:
            continue
        closed.add(cell)
        expanded += 1
        yield ("astar", cell)
        if cell == goal:
            path = reconstruct(parent, goal, start)
            return path, SearchStats(expanded=expanded, path_steps=max(0, len(path) - 1))
        g = -neg_g
        r, c = cell
        for nxt in neighbors4(r, c, rows, cols):
            if nxt in walls or nxt in closed:
                continue
            ng = g + 1
            if nxt not in g_score or ng < g_score[nxt]:
                g_score[nxt] = ng
                parent[nxt] = cell
                counter += 1
                heappush(open_heap, (ng + h(nxt), -ng, counter, nxt))

    return None, SearchStats(expanded=expanded, path_steps=0)


def animate_hybrid(
    start: Cell,
    goal: Cell,
    walls: Set[Cell],
    rows: int,
    cols: int,
) -> Generator[ExpandEvent, None, SearchResult]:
    if start == goal:
        return [start], SearchStats(expanded=0, forward_expanded=0, backward_expanded=0, path_steps=0)
    if start in walls or goal in walls:
        return None, SearchStats(expanded=0, forward_expanded=0, backward_expanded=0, path_steps=0)

    forward_parent: Dict[Cell, Optional[Cell]] = {start: None}
    backward_parent: Dict[Cell, Optional[Cell]] = {goal: None}
    forward_seen: Set[Cell] = {start}
    backward_seen: Set[Cell] = {goal}
    forward_frontier: Set[Cell] = {start}
    backward_frontier: Set[Cell] = {goal}
    forward_expanded_set: Set[Cell] = set()
    backward_expanded_set: Set[Cell] = set()
    fd = 0
    bd = 0
    meet: Optional[Cell] = None

    while (forward_frontier or backward_frontier) and meet is None:
        if not forward_frontier:
            expand_forward = False
        elif not backward_frontier:
            expand_forward = True
        else:
            expand_forward = fd <= bd

        if expand_forward:
            next_frontier: Set[Cell] = set()
            for cell in list(forward_frontier):
                if cell in forward_expanded_set:
                    continue
                forward_expanded_set.add(cell)
                yield ("bfs", cell)
                r, c = cell
                for nxt in neighbors4(r, c, rows, cols):
                    if nxt in walls:
                        continue
                    if nxt in backward_seen and meet is None:
                        meet = nxt
                    if nxt not in forward_seen:
                        forward_seen.add(nxt)
                        forward_parent[nxt] = cell
                        next_frontier.add(nxt)
            forward_frontier = next_frontier
            fd += 1
        else:
            next_frontier = set()
            for cell in list(backward_frontier):
                if cell in backward_expanded_set:
                    continue
                backward_expanded_set.add(cell)
                yield ("dinamik", cell)
                r, c = cell
                for nxt in neighbors4(r, c, rows, cols):
                    if nxt in walls:
                        continue
                    if nxt in forward_seen and meet is None:
                        meet = nxt
                    if nxt not in backward_seen:
                        backward_seen.add(nxt)
                        backward_parent[nxt] = cell
                        next_frontier.add(nxt)
            backward_frontier = next_frontier
            bd += 1

    all_expanded = forward_expanded_set | backward_expanded_set
    if meet is None:
        return None, SearchStats(
            expanded=len(all_expanded),
            forward_expanded=len(forward_expanded_set),
            backward_expanded=len(backward_expanded_set),
            path_steps=0,
        )

    path = _meet_path(meet, forward_parent, backward_parent, start, goal)
    if not path or path[0] != start or path[-1] != goal:
        return None, SearchStats(
            expanded=len(all_expanded),
            forward_expanded=len(forward_expanded_set),
            backward_expanded=len(backward_expanded_set),
            path_steps=0,
        )

    return path, SearchStats(
        expanded=len(all_expanded),
        forward_expanded=len(forward_expanded_set),
        backward_expanded=len(backward_expanded_set),
        path_steps=max(0, len(path) - 1),
    )
