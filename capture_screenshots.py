#!/usr/bin/env python3
"""Save README screenshots (pygame render)."""
from __future__ import annotations

import os
import sys

# Try headless first
if "SDL_VIDEODRIVER" not in os.environ:
    os.environ["SDL_VIDEODRIVER"] = "dummy"

import pygame

from algorithms import astar, bfs, hybrid_search
from maze_defaults import COLS, DEFAULT_GOAL, DEFAULT_START, ROWS, default_walls
from main import MazeApp


def save_app(app: MazeApp, path: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    app.draw_grid()
    app.draw_panel((0, 0))
    pygame.display.flip()
    pygame.image.save(app.screen, path)


def main() -> int:
    pygame.init()
    try:
        app = MazeApp()
    except pygame.error:
        os.environ.pop("SDL_VIDEODRIVER", None)
        pygame.quit()
        pygame.init()
        app = MazeApp()

    base = os.path.join(os.path.dirname(__file__), "screenshots")

    # 1) Default maze
    app.reset_search_viz()
    save_app(app, os.path.join(base, "01_varsayilan_labirent.png"))

    # 2) Mid-search hybrid
    app.start_animation("hybrid")
    for _ in range(120):
        app.step_animation(9999)
        if app.anim_gen is None:
            break
    save_app(app, os.path.join(base, "02_arama_animasyonu.png"))

    # 3) Compare + full path
    walls = default_walls()
    app.walls = walls
    app.run_compare_sync()
    # Mark some visits for visual interest
    gen = __import__("search_animation", fromlist=["animate_hybrid"]).animate_hybrid(
        DEFAULT_START, DEFAULT_GOAL, walls, ROWS, COLS
    )
    try:
        while True:
            layer, cell = next(gen)
            if cell not in (DEFAULT_START, DEFAULT_GOAL):
                from main import COLOR_BFS, COLOR_DINAMIK

                app.visit_colors[cell] = COLOR_BFS if layer == "bfs" else COLOR_DINAMIK
    except StopIteration:
        pass
    app.path, _ = hybrid_search(DEFAULT_START, DEFAULT_GOAL, walls, ROWS, COLS)
    _, sb = bfs(DEFAULT_START, DEFAULT_GOAL, walls, ROWS, COLS)
    _, sh = hybrid_search(DEFAULT_START, DEFAULT_GOAL, walls, ROWS, COLS)
    _, sa = astar(DEFAULT_START, DEFAULT_GOAL, walls, ROWS, COLS)
    app.compare_stats = {"BFS": sb, "Hibrit": sh, "A*": sa}
    app.last_stats = sh
    app.algo_name = "Karşılaştır"
    app.agent_index = len(app.path) - 1 if app.path else 0
    app.agent_active = False
    save_app(app, os.path.join(base, "03_en_kisa_yol_karsilastirma.png"))

    pygame.quit()
    print("Saved screenshots to", base)
    return 0


if __name__ == "__main__":
    sys.exit(main())
