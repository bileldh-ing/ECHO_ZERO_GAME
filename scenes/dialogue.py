"""Dialogue box with typewriter text and portraits, plus a choice menu."""
import json
import math
import os

import pygame

from settings import W, H, DATA_DIR, SPEAKER_COLORS, CYAN, WHITE, GREY
from scenes.base import Scene
from systems import assets
from systems.ui import panel, text, wrap

_DIALOGUE = None


def lines_for(key):
    global _DIALOGUE
    if _DIALOGUE is None:
        with open(os.path.join(DATA_DIR, "dialogue.json"), encoding="utf-8") as f:
            _DIALOGUE = json.load(f)
    return _DIALOGUE.get(key, [])


PORTRAITS = {"ECHO": "portrait_echo", "HALCYON": "portrait_halcyon", "LOG": "portrait_log",
             "SYSTEM": "portrait_log", "CREW": "portrait_crew"}


class Dialogue(Scene):
    overlay = True
    CPS = 62

    def __init__(self, game, lines, on_done=None):
        super().__init__(game)
        self.lines = lines
        self.i = 0
        self.shown = 0.0
        self.on_done = on_done
        self.t = 0.0
        self.tick = 0
        self.appear = 0.0

    @property
    def line(self):
        return self.lines[self.i]

    def advance(self):
        full = len(self.line["t"])
        if self.shown < full:
            self.shown = full
            return
        self.i += 1
        self.shown = 0
        assets.play("select", 0.5)
        if self.i >= len(self.lines):
            self.close()
            if self.on_done:
                self.on_done()

    def handle_event(self, e):
        if e.type == pygame.KEYDOWN and e.key in (pygame.K_SPACE, pygame.K_e, pygame.K_RETURN, pygame.K_KP_ENTER):
            self.advance()
        elif e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE:
            # skip the whole conversation
            self.i = len(self.lines) - 1
            self.shown = len(self.line["t"])
            self.advance()
        elif e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
            self.advance()

    def update(self, dt):
        self.t += dt
        self.appear = min(1.0, self.appear + dt * 6)
        full = len(self.line["t"])
        if self.shown < full:
            before = int(self.shown)
            self.shown = min(full, self.shown + dt * self.CPS)
            if int(self.shown) // 3 != before // 3 and self.line["t"][before:int(self.shown)].strip():
                assets.play("type", 0.4)

    def draw(self, surf):
        spk = self.line["s"]
        col = SPEAKER_COLORS.get(spk, WHITE)
        off = int((1 - self.appear) * 40)
        box = pygame.Rect(40, H - 178 + off, W - 80, 150)
        panel(surf, box, border=col)
        por = PORTRAITS.get(spk, "portrait_human")
        img = assets.image(por, "ui")
        surf.blit(img, (box.x + 18, box.y + 22))
        if spk == "HALCYON":
            g = pygame.Surface(img.get_size(), pygame.SRCALPHA)
            a = int(40 + 40 * math.sin(self.t * 6))
            g.fill((255, 60, 50, a))
            surf.blit(g, (box.x + 18, box.y + 22), special_flags=pygame.BLEND_RGBA_ADD)
        text(surf, spk, (box.x + 104, box.y + 16), 17, col, bold=True)
        msg = self.line["t"][:int(self.shown)]
        y = box.y + 46
        for ln in wrap(msg, 17, box.w - 130):
            text(surf, ln, (box.x + 104, y), 17, WHITE)
            y += 24
        if self.shown >= len(self.line["t"]):
            a = int(180 + 70 * math.sin(self.t * 5))
            text(surf, "SPACE >", (box.right - 16, box.bottom - 12), 13, CYAN, anchor="bottomright", alpha=a)
        text(surf, f"{self.i + 1}/{len(self.lines)}", (box.right - 16, box.y + 16), 12, GREY, anchor="topright")


class Choice(Scene):
    """options: list of dict(key, label, desc, enabled)."""
    overlay = True

    def __init__(self, game, title, options, on_pick):
        super().__init__(game)
        self.title = title
        self.options = options
        self.sel = next((i for i, o in enumerate(options) if o.get("enabled", True)), 0)
        self.on_pick = on_pick
        self.t = 0.0

    def move(self, d):
        for _ in range(len(self.options)):
            self.sel = (self.sel + d) % len(self.options)
            if self.options[self.sel].get("enabled", True):
                break
        assets.play("select", 0.5)

    def handle_event(self, e):
        if e.type == pygame.KEYDOWN:
            if e.key in (pygame.K_UP, pygame.K_w):
                self.move(-1)
            elif e.key in (pygame.K_DOWN, pygame.K_s):
                self.move(1)
            elif e.key in (pygame.K_RETURN, pygame.K_SPACE, pygame.K_e, pygame.K_KP_ENTER):
                o = self.options[self.sel]
                if o.get("enabled", True):
                    assets.play("confirm", 0.8)
                    self.close()
                    self.on_pick(o["key"])
                else:
                    assets.play("error", 0.5)

    def update(self, dt):
        self.t += dt

    def draw(self, surf):
        dim = pygame.Surface((W, H), pygame.SRCALPHA)
        dim.fill((0, 0, 0, 150))
        surf.blit(dim, (0, 0))
        h = 110 + len(self.options) * 74
        box = pygame.Rect(W // 2 - 340, H // 2 - h // 2, 680, h)
        panel(surf, box, border=(255, 200, 120))
        text(surf, self.title, (W // 2, box.y + 28), 22, (255, 210, 140), bold=True, anchor="midtop")
        y = box.y + 82
        for i, o in enumerate(self.options):
            r = pygame.Rect(box.x + 30, y, box.w - 60, 62)
            en = o.get("enabled", True)
            if i == self.sel:
                s = pygame.Surface(r.size, pygame.SRCALPHA)
                s.fill((255, 200, 120, 40 + int(20 * math.sin(self.t * 6))))
                surf.blit(s, r)
                pygame.draw.rect(surf, (255, 210, 140), r, 2, border_radius=4)
            col = WHITE if en else (110, 110, 120)
            text(surf, ("> " if i == self.sel else "  ") + o["label"], (r.x + 14, r.y + 8), 18, col, bold=True)
            text(surf, o.get("desc", ""), (r.x + 38, r.y + 36), 13, GREY if en else (90, 90, 100))
            y += 74
