"""Small overlay scenes: pause menu, inventory, controls, system failure, chapter card."""
import math

import pygame

from settings import W, H, CYAN, WHITE, GREY, RED, AMBER
from scenes.base import Scene
from systems import assets
from systems.inventory import FRAGMENTS, TOTAL_FRAGMENTS
from systems.ui import panel, text, wrap, icon

CONTROLS = [
    ("WASD / Arrows", "Move"),
    ("SHIFT", "Sprint (drains battery, makes noise)"),
    ("E / SPACE", "Interact, advance dialogue"),
    ("F", "Toggle flashlight (drones spot light from far away)"),
    ("Q", "Sensor scan (highlights objects, costs power)"),
    ("TAB", "Inventory and recovered data"),
    ("ESC", "Pause"),
    ("F11", "Fullscreen"),
]


def dim(surf, a=160):
    s = pygame.Surface((W, H), pygame.SRCALPHA)
    s.fill((0, 0, 0, a))
    surf.blit(s, (0, 0))


class Controls(Scene):
    overlay = True

    def handle_event(self, e):
        if e.type == pygame.KEYDOWN or (e.type == pygame.MOUSEBUTTONDOWN and e.button == 1):
            assets.play("select", 0.5)
            self.close()

    def draw(self, surf):
        dim(surf, 180)
        box = pygame.Rect(W // 2 - 330, H // 2 - 200, 660, 400)
        panel(surf, box)
        text(surf, "CONTROLS", (box.centerx, box.y + 20), 24, CYAN, bold=True, anchor="midtop")
        y = box.y + 76
        for k, v in CONTROLS:
            text(surf, k, (box.x + 50, y), 16, WHITE, bold=True)
            text(surf, v, (box.x + 240, y), 16, GREY)
            y += 34
        text(surf, "press any key", (box.centerx, box.bottom - 30), 13, GREY, anchor="midtop")


class Pause(Scene):
    overlay = True
    OPTIONS = ["Resume", "Controls", "Restart from checkpoint", "Quit to title"]

    def __init__(self, game, gp):
        super().__init__(game)
        self.gp = gp
        self.sel = 0
        self.t = 0.0

    def handle_event(self, e):
        if e.type != pygame.KEYDOWN:
            return
        if e.key in (pygame.K_ESCAPE, pygame.K_p):
            self.close()
        elif e.key in (pygame.K_UP, pygame.K_w):
            self.sel = (self.sel - 1) % len(self.OPTIONS)
            assets.play("select", 0.4)
        elif e.key in (pygame.K_DOWN, pygame.K_s):
            self.sel = (self.sel + 1) % len(self.OPTIONS)
            assets.play("select", 0.4)
        elif e.key in (pygame.K_RETURN, pygame.K_SPACE, pygame.K_e):
            assets.play("confirm", 0.6)
            o = self.OPTIONS[self.sel]
            if o == "Resume":
                self.close()
            elif o == "Controls":
                self.game.push(Controls(self.game))
            elif o == "Restart from checkpoint":
                self.close()
                self.gp.reload_checkpoint()
            else:
                from scenes.menu import Menu
                self.game.transition(lambda: self.game.replace_all(Menu(self.game)))

    def update(self, dt):
        self.t += dt

    def draw(self, surf):
        dim(surf, 170)
        box = pygame.Rect(W // 2 - 200, H // 2 - 150, 400, 300)
        panel(surf, box)
        text(surf, "PAUSED", (box.centerx, box.y + 22), 26, CYAN, bold=True, anchor="midtop")
        y = box.y + 88
        for i, o in enumerate(self.OPTIONS):
            sel = i == self.sel
            text(surf, ("> " if sel else "") + o, (box.centerx, y), 18, WHITE if sel else GREY, bold=sel, anchor="midtop")
            y += 44


class InventoryView(Scene):
    overlay = True

    def __init__(self, game, state):
        super().__init__(game)
        self.state = state

    def handle_event(self, e):
        if e.type == pygame.KEYDOWN and e.key in (pygame.K_TAB, pygame.K_ESCAPE, pygame.K_i):
            self.close()

    def draw(self, surf):
        dim(surf, 170)
        box = pygame.Rect(W // 2 - 400, H // 2 - 230, 800, 460)
        panel(surf, box)
        text(surf, "INVENTORY", (box.x + 30, box.y + 20), 22, CYAN, bold=True)
        y = box.y + 66
        items = self.state.inv.listing()
        if not items:
            text(surf, "Empty.", (box.x + 30, y), 15, GREY)
        for k, n, info in items:
            surf.blit(icon(info["icon"], 32), (box.x + 30, y))
            text(surf, f"{info['name']}  x{n}", (box.x + 74, y), 16, WHITE, bold=True)
            text(surf, info["desc"], (box.x + 74, y + 20), 12, GREY)
            y += 52
        x2 = box.x + 420
        text(surf, f"RECOVERED DATA  {len(self.state.fragments)}/{TOTAL_FRAGMENTS}", (x2, box.y + 20), 22, (190, 150, 255), bold=True)
        y = box.y + 66
        for fid, name in FRAGMENTS.items():
            have = fid in self.state.fragments
            surf.blit(icon("item_fragment", 22), (x2, y)) if have else pygame.draw.rect(surf, (60, 60, 70), (x2 + 4, y + 4, 14, 14), 1)
            text(surf, name if have else "??? - not recovered", (x2 + 32, y + 2), 14, WHITE if have else (100, 100, 110))
            y += 34
        b = self.state.battery
        text(surf, f"Battery {b:.0f}%    Play time {int(self.state.playtime // 60)}m {int(self.state.playtime % 60):02d}s",
             (box.x + 30, box.bottom - 36), 14, GREY)
        text(surf, "TAB close", (box.right - 30, box.bottom - 36), 13, GREY, anchor="topright")


class SystemFailure(Scene):
    overlay = True

    def __init__(self, game, gp, reason):
        super().__init__(game)
        self.gp = gp
        self.reason = reason
        self.t = 0.0

    def handle_event(self, e):
        if self.t > 1.0 and e.type == pygame.KEYDOWN and e.key in (pygame.K_RETURN, pygame.K_SPACE, pygame.K_e):
            assets.play("confirm", 0.7)
            self.close()
            self.gp.reload_checkpoint()

    def update(self, dt):
        self.t += dt

    def draw(self, surf):
        k = min(1.0, self.t * 1.5)
        dim(surf, int(200 * k))
        jitter = int(4 * max(0, 1 - self.t)) if self.t < 1 else 0
        text(surf, "SYSTEM FAILURE", (W // 2 + jitter, H // 2 - 60), 46, RED, bold=True, anchor="center", alpha=int(255 * k))
        text(surf, self.reason, (W // 2, H // 2), 18, WHITE, anchor="center", alpha=int(255 * k))
        if self.t > 1.0:
            a = int(160 + 90 * math.sin(self.t * 4))
            text(surf, "Press ENTER to reboot from last checkpoint", (W // 2, H // 2 + 60), 15, CYAN, anchor="center", alpha=a)


class ChapterCard(Scene):
    overlay = True

    def __init__(self, game, chapter, title, on_done=None):
        super().__init__(game)
        self.chapter, self.title = chapter, title
        self.t = 0.0
        self.on_done = on_done
        assets.play("heartbeat", 0.6)

    def handle_event(self, e):
        if e.type == pygame.KEYDOWN and self.t > 0.6:
            self.t = max(self.t, 3.0)

    def update(self, dt):
        self.t += dt
        if self.t > 3.6:
            self.close()
            if self.on_done:
                self.on_done()

    def draw(self, surf):
        if self.t < 0.6:
            a = 1.0
        elif self.t < 3.0:
            a = 1.0 - (self.t - 0.6) / 2.4 * 0.35
        else:
            a = max(0.0, 0.65 - (self.t - 3.0) / 0.6 * 0.65)
        dim(surf, int(255 * a))
        ta = min(1.0, self.t / 0.8) * (1.0 if self.t < 3.0 else max(0.0, 1 - (self.t - 3.0) / 0.6))
        spread = int(30 * (1 - min(1.0, self.t / 1.2)))
        text(surf, f"CHAPTER {self.chapter}", (W // 2, H // 2 - 40 - spread), 18, CYAN, bold=True, anchor="center", alpha=int(255 * ta))
        text(surf, self.title.upper(), (W // 2, H // 2 + 6), 40, WHITE, bold=True, anchor="center", alpha=int(255 * ta))
        w = int(320 * min(1.0, self.t / 1.0))
        pygame.draw.line(surf, CYAN, (W // 2 - w // 2, H // 2 + 42), (W // 2 + w // 2, H // 2 + 42), 2)
