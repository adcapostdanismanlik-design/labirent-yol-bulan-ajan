"""Grid pathfinding: BFS, A*, and bidirectional hybrid (BFS + reverse flow field)."""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from heapq import heappop, heappush
from typing import Callable, Dict, Generator, Iterable, List, Optional, Set, Tuple

Cell = Tuple[int, int]
ExpandEvent = Tuple[str, Cell]  # layer: "bfs" | "dinamik" | "astar"


@dataclass
class SearchStats:
    expanded: int
    forward_expanded: int = 0
    backward_expanded: int = 0
    path_steps: int = 0


def neighbors4(r: int, c: int, rows: int, cols: int) -> Iterable[Cell]:
    for dr, dc in ((-1, 0), (1, 0), (0, -1), (0, 1)):
        nr, nc = r + dr, c + dc
        if 0 <= nr < rows and 0 <= nc < cols:
            yield (nr, nc)


def reconstruct(parent: Dict[Cell, Optional[Cell]], end: Cell, start: Cell) -> List[Cell]:
    path: List[Cell] = []
    cur: Optional[Cell] = end
    while cur is not None:
        path.append(cur)
        cur = parent.get(cur)
    path.reverse()
    if not path or path[0] != start:
        return []
    return path


def _meet_path(
    meet: Cell,
    forward_parent: Dict[Cell, Optional[Cell]],
    backward_parent: Dict[Cell, Optional[Cell]],
    start: Cell,
    goal: Cell,
) -> List[Cell]:
    forward_part: List[Cell] = []
    cur: Optional[Cell] = meet
    while cur is not None:
        forward_part.append(cur)
        cur = forward_parent.get(cur)
    forward_part.reverse()

    backward_part: List[Cell] = []
    cur = backward_parent.get(meet)
    while cur is not None:
        backward_part.append(cur)
        cur = backward_parent.get(cur)

    return forward_part + backward_part


def bfs(
    start: Cell,
    goal: Cell,
    walls: Set[Cell],
    rows: int,
    cols: int,
    on_expand: Optional[Callable[[ExpandEvent], None]] = None,
) -> Tuple[Optional[List[Cell]], SearchStats]:
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
        if on_expand:
            on_expand(("bfs", cell))

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


def astar(
    start: Cell,
    goal: Cell,
    walls: Set[Cell],
    rows: int,
    cols: int,
    on_expand: Optional[Callable[[ExpandEvent], None]] = None,
) -> Tuple[Optional[List[Cell]], SearchStats]:
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
        if on_expand:
            on_expand(("astar", cell))

        if cell == goal:
            path = reconstruct(parent, goal, start)
            return path, SearchStats(expanded=expanded, path_steps=max(0, len(path) - 1))

        r, c = cell
        g = -neg_g
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


def hybrid_search(
    start: Cell,
    goal: Cell,
    walls: Set[Cell],
    rows: int,
    cols: int,
    on_expand: Optional[Callable[[ExpandEvent], None]] = None,
) -> Tuple[Optional[List[Cell]], SearchStats]:
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

    def expand_forward() -> None:
        nonlocal fd, meet
        if not forward_frontier:
            return
        next_frontier: Set[Cell] = set()
        for cell in forward_frontier:
            if cell in forward_expanded_set:
                continue
            forward_expanded_set.add(cell)
            if on_expand:
                on_expand(("bfs", cell))
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
        forward_frontier.clear()
        forward_frontier.update(next_frontier)
        fd += 1

    def expand_backward() -> None:
        nonlocal bd, meet
        if not backward_frontier:
            return
        next_frontier: Set[Cell] = set()
        for cell in backward_frontier:
            if cell in backward_expanded_set:
                continue
            backward_expanded_set.add(cell)
            if on_expand:
                on_expand(("dinamik", cell))
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
        backward_frontier.clear()
        backward_frontier.update(next_frontier)
        bd += 1

    while (forward_frontier or backward_frontier) and meet is None:
        if not forward_frontier:
            expand_backward()
            continue
        if not backward_frontier:
            expand_forward()
            continue
        if fd <= bd:
            expand_forward()
        else:
            expand_backward()

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


def path_valid(path: Optional[List[Cell]], walls: Set[Cell], start: Cell, goal: Cell) -> bool:
    if path is None:
        return False
    if not path:
        return False
    if path[0] != start or path[-1] != goal:
        return False
    for i, cell in enumerate(path):
        if cell in walls:
            return False
        if i > 0:
            r0, c0 = path[i - 1]
            r1, c1 = cell
            if abs(r0 - r1) + abs(c0 - c1) != 1:
                return False
    return True


def count_obstacle_regions(walls: Set[Cell], rows: int, cols: int) -> int:
    """4-connected components of wall cells (internal obstacles only)."""
    remaining = set(walls)
    regions = 0
    while remaining:
        seed = next(iter(remaining))
        regions += 1
        stack = [seed]
        remaining.remove(seed)
        while stack:
            r, c = stack.pop()
            for nxt in neighbors4(r, c, rows, cols):
                if nxt in remaining:
                    remaining.remove(nxt)
                    stack.append(nxt)
    return regions
