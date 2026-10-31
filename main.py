#!/usr/bin/env python3
"""Labirentte Yol Bulan Ajan — pygame arayüzü."""
from __future__ import annotations

from typing import Dict, List, Optional, Set, Tuple

import pygame

from algorithms import SearchStats, astar, bfs, count_obstacle_regions, hybrid_search
from maze_defaults import (
    COLS,
    DEFAULT_GOAL,
    DEFAULT_START,
    ROWS,
    default_walls,
    random_obstacle_walls,
)
from search_animation import SearchResult, animate_astar, animate_bfs, animate_hybrid

Cell = Tuple[int, int]

# Renkler (koyu tema)
COLOR_BG = (18, 18, 24)
COLOR_PANEL = (28, 28, 36)
COLOR_GRID = (40, 40, 52)
COLOR_EMPTY = (22, 22, 30)
COLOR_WALL = (90, 95, 110)
COLOR_START = (46, 204, 113)
COLOR_GOAL = (236, 72, 153)
COLOR_PATH = (255, 214, 102)
COLOR_AGENT = (255, 255, 255)
COLOR_BFS = (52, 152, 219)
COLOR_DINAMIK = (155, 89, 182)
COLOR_ASTAR = (241, 196, 15)
COLOR_TEXT = (230, 230, 235)
COLOR_MUTED = (160, 160, 170)
COLOR_BTN = (55, 60, 75)
COLOR_BTN_HOVER = (70, 78, 98)
COLOR_BTN_ACTIVE = (80, 130, 200)

CELL_SIZE = 14
PANEL_W = 280
MARGIN = 8
FPS = 60

SPEED_CELLS = {"yavaş": 3, "orta": 12, "hızlı": 40}


class Button:
    def __init__(self, rect: pygame.Rect, label: str, action: str):
        self.rect = rect
        self.label = label
        self.action = action

    def draw(self, surf: pygame.Surface, font: pygame.font.Font, hover: bool) -> None:
        col = COLOR_BTN_HOVER if hover else COLOR_BTN
        pygame.draw.rect(surf, col, self.rect, border_radius=4)
        txt = font.render(self.label, True, COLOR_TEXT)
        surf.blit(txt, txt.get_rect(center=self.rect.center))


class MazeApp:
    def __init__(self) -> None:
        pygame.init()
        self.font = pygame.font.SysFont("Arial", 16)
        self.font_sm = pygame.font.SysFont("Arial", 14)
        self.font_lg = pygame.font.SysFont("Arial", 20, bold=True)

        grid_w = COLS * CELL_SIZE
        grid_h = ROWS * CELL_SIZE
        self.width = MARGIN + grid_w + MARGIN + PANEL_W
        self.height = max(grid_h + 2 * MARGIN, 620)
        self.screen = pygame.display.set_mode((self.width, self.height))
        pygame.display.set_caption("Labirentte Yol Bulan Ajan")

        self.grid_rect = pygame.Rect(MARGIN, MARGIN, grid_w, grid_h)

        self.walls: Set[Cell] = default_walls()
        self.start: Cell = DEFAULT_START
        self.goal: Cell = DEFAULT_GOAL

        self.mode: Optional[str] = None  # "start" | "goal"
        self.drag_wall = False
        self.drag_erase = False

        self.visit_colors: Dict[Cell, Tuple[int, int, int]] = {}
        self.path: Optional[List[Cell]] = None
        self.agent_index = 0
        self.agent_active = False

        self.algo_name = "—"
        self.last_stats: Optional[SearchStats] = None
        self.compare_stats: Dict[str, SearchStats] = {}
        self.no_path = False

        self.auto_replan = True
        self.speed_name = "orta"
        self.anim_gen = None
        self.anim_result: Optional[SearchResult] = None
        self.pending_compare = False

        self.buttons = self._build_buttons()
        self.clock = pygame.time.Clock()

    def _build_buttons(self) -> List[Button]:
        x = self.grid_rect.right + MARGIN
        y = MARGIN
        w, h, gap = PANEL_W - 2 * MARGIN, 32, 6
        labels = [
            ("Hibrit Ara", "hybrid"),
            ("BFS", "bfs"),
            ("A*", "astar"),
            ("Karşılaştır", "compare"),
            ("Rastgele engel", "random"),
            ("Temizle", "clear"),
            ("Başlangıç koy", "set_start"),
            ("Hedef koy", "set_goal"),
        ]
        buttons: List[Button] = []
        for label, action in labels:
            buttons.append(Button(pygame.Rect(x, y, w, h), label, action))
            y += h + gap
        return buttons

    def cell_at_pixel(self, pos: Tuple[int, int]) -> Optional[Cell]:
        if not self.grid_rect.collidepoint(pos):
            return None
        lx = pos[0] - self.grid_rect.x
        ly = pos[1] - self.grid_rect.y
        c = lx // CELL_SIZE
        r = ly // CELL_SIZE
        if 0 <= r < ROWS and 0 <= c < COLS:
            return (int(r), int(c))
        return None

    def paint_cell(self, cell: Cell, wall: bool) -> None:
        if cell == self.start or cell == self.goal:
            return
        if wall:
            self.walls.add(cell)
        else:
            self.walls.discard(cell)

    def reset_search_viz(self) -> None:
        self.visit_colors.clear()
        self.path = None
        self.agent_active = False
        self.agent_index = 0
        self.anim_gen = None
        self.anim_result = None
        self.no_path = False
        self.last_stats = None
        self.algo_name = "—"

    def start_animation(self, kind: str) -> None:
        self.reset_search_viz()
        self.algo_name = {"hybrid": "Hibrit", "bfs": "BFS", "astar": "A*"}[kind]
        factories = {
            "hybrid": animate_hybrid,
            "bfs": animate_bfs,
            "astar": animate_astar,
        }
        self.anim_gen = factories[kind](self.start, self.goal, self.walls, ROWS, COLS)

    def finish_search(self, path: Optional[List[Cell]], stats: SearchStats) -> None:
        self.last_stats = stats
        if path is None:
            self.no_path = True
            self.path = None
            self.agent_active = False
            return
        self.path = path
        self.no_path = False
        self.agent_index = 0
        self.agent_active = True

    def run_compare_sync(self) -> None:
        self.reset_search_viz()
        self.algo_name = "Karşılaştır"
        pb, sb = bfs(self.start, self.goal, self.walls, ROWS, COLS)
        ph, sh = hybrid_search(self.start, self.goal, self.walls, ROWS, COLS)
        pa, sa = astar(self.start, self.goal, self.walls, ROWS, COLS)
        self.compare_stats = {"BFS": sb, "Hibrit": sh, "A*": sa}
        self.finish_search(pb, sh)
        # Show hybrid visit replay quickly — just path for compare view
        if pb and ph and pa:
            assert len(pb) == len(ph) == len(pa)

    def replan_hybrid_if_needed(self) -> None:
        if self.auto_replan:
            self.start_animation("hybrid")

    def step_animation(self, budget: int) -> None:
        if self.anim_gen is None:
            return
        for _ in range(budget):
            try:
                layer, cell = next(self.anim_gen)
                col = {
                    "bfs": COLOR_BFS,
                    "dinamik": COLOR_DINAMIK,
                    "astar": COLOR_ASTAR,
                }[layer]
                if cell != self.start and cell != self.goal:
                    self.visit_colors[cell] = col
            except StopIteration as ex:
                path, stats = ex.value
                self.anim_gen = None
                self.finish_search(path, stats)
                break

    def tick_agent(self) -> None:
        if not self.agent_active or not self.path:
            return
        if self.agent_index < len(self.path) - 1:
            self.agent_index += 1
        else:
            self.agent_active = False

    def handle_action(self, action: str) -> None:
        if action == "hybrid":
            self.start_animation("hybrid")
        elif action == "bfs":
            self.start_animation("bfs")
        elif action == "astar":
            self.start_animation("astar")
        elif action == "compare":
            self.run_compare_sync()
        elif action == "random":
            self.walls = random_obstacle_walls()
            self.reset_search_viz()
            self.replan_hybrid_if_needed()
        elif action == "clear":
            self.walls.clear()
            self.reset_search_viz()
        elif action == "set_start":
            self.mode = "start"
        elif action == "set_goal":
            self.mode = "goal"

    def draw_grid(self) -> None:
        for r in range(ROWS):
            for c in range(COLS):
                rect = pygame.Rect(
                    self.grid_rect.x + c * CELL_SIZE,
                    self.grid_rect.y + r * CELL_SIZE,
                    CELL_SIZE - 1,
                    CELL_SIZE - 1,
                )
                cell = (r, c)
                if cell in self.walls:
                    col = COLOR_WALL
                elif cell in self.visit_colors:
                    col = self.visit_colors[cell]
                else:
                    col = COLOR_EMPTY
                pygame.draw.rect(self.screen, col, rect)
                if cell == self.start:
                    pygame.draw.rect(self.screen, COLOR_START, rect.inflate(-2, -2))
                elif cell == self.goal:
                    pygame.draw.rect(self.screen, COLOR_GOAL, rect.inflate(-2, -2))

        if self.path:
            for cell in self.path:
                if cell == self.start or cell == self.goal:
                    continue
                rect = pygame.Rect(
                    self.grid_rect.x + cell[1] * CELL_SIZE + 3,
                    self.grid_rect.y + cell[0] * CELL_SIZE + 3,
                    CELL_SIZE - 7,
                    CELL_SIZE - 7,
                )
                pygame.draw.rect(self.screen, COLOR_PATH, rect)

        if self.path and self.agent_active:
            ac = self.path[self.agent_index]
            cx = self.grid_rect.x + ac[1] * CELL_SIZE + CELL_SIZE // 2
            cy = self.grid_rect.y + ac[0] * CELL_SIZE + CELL_SIZE // 2
            pygame.draw.circle(self.screen, COLOR_AGENT, (cx, cy), max(3, CELL_SIZE // 4))

        pygame.draw.rect(self.screen, COLOR_GRID, self.grid_rect, 1)

    def draw_panel(self, mouse_pos: Tuple[int, int]) -> None:
        px = self.grid_rect.right + MARGIN
        panel = pygame.Rect(px - MARGIN // 2, 0, PANEL_W + MARGIN, self.height)
        pygame.draw.rect(self.screen, COLOR_PANEL, panel)

        y = MARGIN
        title = self.font_lg.render("Labirent Ajanı", True, COLOR_TEXT)
        self.screen.blit(title, (px, y))
        y += 32

        regions = count_obstacle_regions(self.walls, ROWS, COLS)
        infos = [
            f"Izgara: {ROWS}×{COLS}",
            f"Engel bölgesi: {regions}",
            f"Algoritma: {self.algo_name}",
        ]
        if self.no_path:
            infos.append("Yol yok")
        elif self.last_stats:
            infos.append(f"Genişletilen: {self.last_stats.expanded}")
            if self.last_stats.forward_expanded or self.last_stats.backward_expanded:
                infos.append(
                    f"  İleri: {self.last_stats.forward_expanded}  Geri: {self.last_stats.backward_expanded}"
                )
            infos.append(f"Yol adımı: {self.last_stats.path_steps}")

        for line in infos:
            self.screen.blit(self.font_sm.render(line, True, COLOR_MUTED if line == "Yol yok" else COLOR_TEXT), (px, y))
            y += 20

        y += 8
        self.screen.blit(self.font.render("Hız: 1/2/3", True, COLOR_MUTED), (px, y))
        y += 18
        self.screen.blit(self.font.render(f"Seçili: {self.speed_name}", True, COLOR_TEXT), (px, y))
        y += 22

        toggle = "[X]" if self.auto_replan else "[ ]"
        self.screen.blit(
            self.font_sm.render(f"{toggle} Duvar sonrası hibrit yenile", True, COLOR_TEXT),
            (px, y),
        )
        y += 28

        if self.compare_stats:
            y += 4
            self.screen.blit(self.font.render("Karşılaştırma", True, COLOR_TEXT), (px, y))
            y += 22
            max_exp = max(s.expanded for s in self.compare_stats.values()) or 1
            for name, st in self.compare_stats.items():
                bar_w = int((PANEL_W - 40) * st.expanded / max_exp)
                pygame.draw.rect(self.screen, COLOR_BTN, pygame.Rect(px, y + 14, PANEL_W - 40, 10))
                col = COLOR_BFS if name == "BFS" else COLOR_DINAMIK if name == "Hibrit" else COLOR_ASTAR
                pygame.draw.rect(self.screen, col, pygame.Rect(px, y + 14, bar_w, 10))
                self.screen.blit(
                    self.font_sm.render(f"{name}: {st.expanded} hücre", True, COLOR_TEXT),
                    (px, y),
                )
                y += 32

        for btn in self.buttons:
            btn.draw(self.screen, self.font_sm, btn.rect.collidepoint(mouse_pos))

        if self.mode:
            hint = "Başlangıç için hücre tıkla" if self.mode == "start" else "Hedef için hücre tıkla"
            self.screen.blit(self.font_sm.render(hint, True, COLOR_ASTAR), (px, self.height - 28))

    def run(self) -> None:
        running = True
        agent_timer = 0
        while running:
            dt = self.clock.tick(FPS)
            mouse = pygame.mouse.get_pos()

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        running = False
                    elif event.key == pygame.K_SPACE:
                        self.start_animation("hybrid")
                    elif event.key == pygame.K_b:
                        self.start_animation("bfs")
                    elif event.key == pygame.K_a:
                        self.start_animation("astar")
                    elif event.key == pygame.K_c:
                        self.run_compare_sync()
                    elif event.key == pygame.K_r:
                        self.walls.clear()
                        self.reset_search_viz()
                    elif event.key == pygame.K_m:
                        self.walls = random_obstacle_walls()
                        self.reset_search_viz()
                        self.replan_hybrid_if_needed()
                    elif event.key in (pygame.K_1, pygame.K_2, pygame.K_3):
                        self.speed_name = {pygame.K_1: "yavaş", pygame.K_2: "orta", pygame.K_3: "hızlı"}[event.key]
                    elif event.key == pygame.K_t:
                        self.auto_replan = not self.auto_replan
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    if event.button == 1:
                        for btn in self.buttons:
                            if btn.rect.collidepoint(event.pos):
                                self.handle_action(btn.action)
                                break
                        else:
                            cell = self.cell_at_pixel(event.pos)
                            if cell and self.mode == "start" and cell not in self.walls:
                                self.start = cell
                                self.mode = None
                                self.reset_search_viz()
                                self.replan_hybrid_if_needed()
                            elif cell and self.mode == "goal" and cell not in self.walls:
                                self.goal = cell
                                self.mode = None
                                self.reset_search_viz()
                                self.replan_hybrid_if_needed()
                            elif cell and self.mode is None and self.grid_rect.collidepoint(event.pos):
                                self.drag_wall = True
                                self.paint_cell(cell, True)
                    elif event.button == 3:
                        cell = self.cell_at_pixel(event.pos)
                        if cell:
                            self.drag_erase = True
                            self.paint_cell(cell, False)
                elif event.type == pygame.MOUSEBUTTONUP:
                    if event.button == 1 and self.drag_wall:
                        self.drag_wall = False
                        self.replan_hybrid_if_needed()
                    if event.button == 3 and self.drag_erase:
                        self.drag_erase = False
                        self.replan_hybrid_if_needed()
                elif event.type == pygame.MOUSEMOTION:
                    if self.drag_wall:
                        cell = self.cell_at_pixel(event.pos)
                        if cell:
                            self.paint_cell(cell, True)
                    elif self.drag_erase:
                        cell = self.cell_at_pixel(event.pos)
                        if cell:
                            self.paint_cell(cell, False)

            budget = SPEED_CELLS[self.speed_name]
            self.step_animation(budget)

            agent_timer += dt
            if agent_timer >= 80:
                agent_timer = 0
                self.tick_agent()

            self.screen.fill(COLOR_BG)
            self.draw_grid()
            self.draw_panel(mouse)
            pygame.display.flip()

        pygame.quit()


def main() -> None:
    MazeApp().run()


if __name__ == "__main__":
    main()
