"""Unit tests for pathfinding algorithms (no pygame)."""
from __future__ import annotations

import random
import unittest

from algorithms import astar, bfs, count_obstacle_regions, hybrid_search, path_valid
from maze_defaults import COLS, DEFAULT_GOAL, DEFAULT_START, ROWS, default_walls, random_obstacle_walls


def steps(path):
    if path is None:
        return None
    return len(path) - 1


class AlgorithmTests(unittest.TestCase):
    def assert_all_equal_paths(self, start, goal, walls, rows, cols):
        pb, sb = bfs(start, goal, walls, rows, cols)
        ph, sh = hybrid_search(start, goal, walls, rows, cols)
        pa, sa = astar(start, goal, walls, rows, cols)
        self.assertEqual(steps(pb), steps(ph))
        self.assertEqual(steps(ph), steps(pa))
        if pb is not None:
            self.assertEqual(len(pb), len(ph))
            self.assertEqual(len(ph), len(pa))
            for p in (pb, ph, pa):
                self.assertTrue(path_valid(p, walls, start, goal))

    def test_open_grid(self):
        walls: set = set()
        self.assert_all_equal_paths((0, 0), (5, 5), walls, 6, 6)

    def test_detour_wall(self):
        walls = {(2, c) for c in range(5)}
        walls.discard((2, 2))
        self.assert_all_equal_paths((0, 0), (4, 4), walls, 5, 5)

    def test_fully_blocked(self):
        walls = {(1, c) for c in range(5)}
        pb, _ = bfs((0, 0), (4, 4), walls, 5, 5)
        ph, _ = hybrid_search((0, 0), (4, 4), walls, 5, 5)
        pa, _ = astar((0, 0), (4, 4), walls, 5, 5)
        self.assertIsNone(pb)
        self.assertIsNone(ph)
        self.assertIsNone(pa)

    def test_start_equals_goal(self):
        walls: set = set()
        for fn in (bfs, hybrid_search, astar):
            p, s = fn((3, 3), (3, 3), walls, 10, 10)
            self.assertEqual(p, [(3, 3)])
            self.assertEqual(s.path_steps, 0)

    def test_default_maze(self):
        walls = default_walls()
        regions = count_obstacle_regions(walls, ROWS, COLS)
        self.assertGreaterEqual(regions, 8)
        self.assert_all_equal_paths(DEFAULT_START, DEFAULT_GOAL, walls, ROWS, COLS)

    def test_random_mazes(self):
        rng = random.Random(42)
        for i in range(40):
            walls = random_obstacle_walls(seed=rng.randint(0, 10_000_000))
            self.assert_all_equal_paths(DEFAULT_START, DEFAULT_GOAL, walls, ROWS, COLS)


if __name__ == "__main__":
    unittest.main()
