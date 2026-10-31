"""Default maze layout and random obstacle generation."""
from __future__ import annotations

import random
from typing import List, Set, Tuple

from algorithms import bfs, count_obstacle_regions

Cell = Tuple[int, int]

ROWS = 24
COLS = 50
DEFAULT_START: Cell = (1, 1)
DEFAULT_GOAL: Cell = (22, 48)

# Fixed rectangles (r0, c0, r1 inclusive, c1 inclusive) — 12 distinct regions
DEFAULT_RECTANGLES: List[Tuple[int, int, int, int]] = [
    (3, 8, 6, 14),
    (3, 22, 7, 26),
    (2, 35, 5, 42),
    (8, 4, 12, 9),
    (9, 18, 13, 24),
    (10, 30, 14, 36),
    (14, 6, 18, 11),
    (15, 20, 19, 28),
    (16, 38, 20, 45),
    (6, 44, 10, 47),
    (11, 12, 13, 15),
    (18, 14, 21, 18),
]


def cells_in_rect(r0: int, c0: int, r1: int, c1: int) -> Set[Cell]:
    out: Set[Cell] = set()
    for r in range(r0, r1 + 1):
        for c in range(c0, c1 + 1):
            out.add((r, c))
    return out


def build_walls_from_rects(rects: List[Tuple[int, int, int, int]]) -> Set[Cell]:
    walls: Set[Cell] = set()
    for r0, c0, r1, c1 in rects:
        walls |= cells_in_rect(r0, c0, r1, c1)
    return walls


def default_walls() -> Set[Cell]:
    walls = build_walls_from_rects(DEFAULT_RECTANGLES)
    walls.discard(DEFAULT_START)
    walls.discard(DEFAULT_GOAL)
    return walls


def random_obstacle_walls(
    rows: int = ROWS,
    cols: int = COLS,
    start: Cell = DEFAULT_START,
    goal: Cell = DEFAULT_GOAL,
    min_rects: int = 8,
    seed: int | None = None,
    max_attempts: int = 200,
) -> Set[Cell]:
    rng = random.Random(seed)
    for _ in range(max_attempts):
        walls: Set[Cell] = set()
        n_rects = rng.randint(min_rects, min_rects + 4)
        for _ in range(n_rects):
            h = rng.randint(2, 5)
            w = rng.randint(3, 8)
            r0 = rng.randint(1, rows - h - 2)
            c0 = rng.randint(1, cols - w - 2)
            rect_cells = cells_in_rect(r0, c0, r0 + h - 1, c0 + w - 1)
            rect_cells.discard(start)
            rect_cells.discard(goal)
            walls |= rect_cells
        if count_obstacle_regions(walls, rows, cols) < min_rects:
            continue
        path, _ = bfs(start, goal, walls, rows, cols)
        if path is not None:
            return walls
    return default_walls()


def walls_to_map_lines(walls: Set[Cell], rows: int = ROWS, cols: int = COLS) -> List[str]:
    lines: List[str] = []
    for r in range(rows):
        row_chars = []
        for c in range(cols):
            row_chars.append("@" if (r, c) in walls else ".")
        lines.append("".join(row_chars))
    return lines


def parse_map_file(text: str) -> Tuple[int, int, Set[Cell]]:
    lines = [ln.strip() for ln in text.strip().splitlines() if ln.strip()]
    height = width = 0
    map_lines: List[str] = []
    i = 0
    while i < len(lines):
        parts = lines[i].split()
        if len(parts) >= 2 and parts[0] == "height":
            height = int(parts[1])
        elif len(parts) >= 2 and parts[0] == "width":
            width = int(parts[1])
        elif parts[0] == "map":
            map_lines = lines[i + 1 : i + 1 + height]
            break
        i += 1
    walls: Set[Cell] = set()
    for r, line in enumerate(map_lines):
        for c, ch in enumerate(line[:width]):
            if ch == "@":
                walls.add((r, c))
    return height, width, walls
