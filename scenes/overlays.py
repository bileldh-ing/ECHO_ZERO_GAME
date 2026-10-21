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
    ("M", "Toggle minimap"),
    ("F11", "Fullscreen"),
    ("Gamepad", "Stick move, A interact, B sprint, X light, Y scan"),
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
        box = pygame.Rect(W // 2 - 360, H // 2 - 230, 720, 460)
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
    OPTIONS = ["Resume", "Controls", "Options", "Restart from checkpoint", "Quit to title"]

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
            elif o == "Options":
                self.game.push(Options(self.game))
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
        box = pygame.Rect(W // 2 - 200, H // 2 - 170, 400, 340)
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


class Options(Scene):
    overlay = True
    ITEMS = [("music", "Music volume", "slider"), ("sfx", "Effects volume", "slider"),
             ("shake", "Screen shake", "toggle"), ("scanlines", "CRT scanlines", "toggle"),
             ("minimap", "Minimap", "toggle"), ("back", "Back", "button")]

    def __init__(self, game):
        super().__init__(game)
        self.sel = 0

    def handle_event(self, e):
        from systems import config
        if e.type != pygame.KEYDOWN:
            return
        k, label, kind = self.ITEMS[self.sel]
        if e.key in (pygame.K_ESCAPE,):
            config.save()
            self.close()
        elif e.key in (pygame.K_UP, pygame.K_w):
            self.sel = (self.sel - 1) % len(self.ITEMS)
            assets.play("select", 0.4)
        elif e.key in (pygame.K_DOWN, pygame.K_s):
            self.sel = (self.sel + 1) % len(self.ITEMS)
            assets.play("select", 0.4)
        elif kind == "slider" and e.key in (pygame.K_LEFT, pygame.K_a, pygame.K_RIGHT, pygame.K_d):
            d = 0.1 if e.key in (pygame.K_RIGHT, pygame.K_d) else -0.1
            config.values[k] = round(max(0.0, min(1.0, config.values[k] + d)), 2)
            config.apply()
            assets.play("select", 0.7)
        elif kind == "toggle" and e.key in (pygame.K_LEFT, pygame.K_RIGHT, pygame.K_a, pygame.K_d,
                                            pygame.K_RETURN, pygame.K_SPACE, pygame.K_e):
            config.values[k] = not config.values[k]
            config.apply()
            assets.play("rotate", 0.6)
        elif kind == "button" and e.key in (pygame.K_RETURN, pygame.K_SPACE, pygame.K_e):
            config.save()
            assets.play("confirm", 0.6)
            self.close()

    def draw(self, surf):
        from systems import config
        dim(surf, 185)
        box = pygame.Rect(W // 2 - 300, H // 2 - 200, 600, 400)
        panel(surf, box)
        text(surf, "OPTIONS", (box.centerx, box.y + 20), 24, CYAN, bold=True, anchor="midtop")
        y = box.y + 80
        for i, (k, label, kind) in enumerate(self.ITEMS):
            sel = i == self.sel
            col = WHITE if sel else GREY
            text(surf, ("> " if sel else "  ") + label, (box.x + 50, y), 18, col, bold=sel)
            if kind == "slider":
                v = config.values[k]
                r = pygame.Rect(box.x + 330, y + 6, 200, 12)
                pygame.draw.rect(surf, (20, 26, 36), r, border_radius=6)
                pygame.draw.rect(surf, CYAN, (r.x, r.y, int(r.w * v), r.h), border_radius=6)
                pygame.draw.circle(surf, WHITE, (r.x + int(r.w * v), r.centery), 9)
                text(surf, f"{int(v * 100)}%", (r.right + 12, y), 15, col)
            elif kind == "toggle":
                on = config.values[k]
                text(surf, "ON" if on else "OFF", (box.x + 330, y), 18, CYAN if on else RED, bold=True)
            y += 46
        text(surf, "UP/DOWN select   LEFT/RIGHT adjust   ESC back", (box.centerx, box.bottom - 30), 13, GREY, anchor="midtop")


class Splash(Scene):
    """Short studio-style intro card before the title screen."""

    def __init__(self, game, nxt):
        super().__init__(game)
        self.t = 0.0
        self.nxt = nxt
        self.done = False

    def finish(self):
        if not self.done:
            self.done = True
            self.game.transition(lambda: self.game.replace_all(self.nxt(self.game)), speed=2.0)

    def handle_event(self, e):
        if e.type in (pygame.KEYDOWN, pygame.MOUSEBUTTONDOWN) and self.t > 0.3:
            self.finish()

    def update(self, dt):
        self.t += dt
        if self.t > 3.4:
            self.finish()

    def draw(self, surf):
        surf.fill((2, 3, 8))
        a = min(1.0, self.t / 0.8) * (1.0 if self.t < 2.6 else max(0.0, 1 - (self.t - 2.6) / 0.8))
        k = 0.6 + 0.4 * math.sin(self.t * 3)
        g = pygame.Surface((240, 240))
        g.fill((0, 0, 0))
        for i in range(10, 0, -1):
            c = int(12 * k * a * (11 - i))
            pygame.draw.circle(g, (c // 3, c, min(255, c * 2)), (120, 120), i * 12)
        surf.blit(g, (W // 2 - 120, H // 2 - 170), special_flags=pygame.BLEND_ADD)
        img = assets.scaled("echo_down_0", (96, 96))
        img = img.copy()
        img.set_alpha(int(255 * a))
        surf.blit(img, (W // 2 - 48, H // 2 - 110))
        text(surf, "A GAME BY BILEL DHAHRI", (W // 2, H // 2 + 20), 20, WHITE, bold=True, anchor="midtop", alpha=int(255 * a))
        text(surf, "made with Python + pygame", (W // 2, H // 2 + 54), 13, GREY, anchor="midtop", alpha=int(200 * a))
