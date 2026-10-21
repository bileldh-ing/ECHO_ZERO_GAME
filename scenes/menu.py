"""Title screen."""
import math
import random

import pygame

from settings import W, H, CYAN, WHITE, GREY, RED
from scenes.base import Scene
from scenes.overlays import Controls, Options
from systems import assets, save_manager
from systems.state import GameState
from systems.ui import post_fx, text, vignette, scanlines


class Menu(Scene):
    def __init__(self, game):
        super().__init__(game)
        self.bg = assets.image("title", "ui")
        self.t = 0.0
        self.sel = 0
        self.dust = [[random.uniform(0, W), random.uniform(0, H), random.uniform(4, 16), random.uniform(0.5, 2)]
                     for _ in range(70)]
        self.glitch = 0.0
        self.shade = pygame.Surface((W, H), pygame.SRCALPHA)
        for i in range(H):
            a = int(200 * (i / H) ** 2.2)
            pygame.draw.line(self.shade, (2, 4, 10, a), (0, i), (W, i))
        for i in range(W // 2):
            a = int(150 * (1 - i / (W / 2)) ** 2)
            pygame.draw.line(self.shade, (2, 4, 10, a), (i, 0), (i, H))
        self.refresh_options()

    def refresh_options(self):
        self.options = []
        if save_manager.exists():
            self.options.append("Continue")
        self.options += ["New Game", "Controls", "Options", "Quit"]
        self.sel = min(self.sel, len(self.options) - 1)

    def on_enter(self):
        assets.play_music("menu")

    def start(self, state):
        from scenes.gameplay import Gameplay
        assets.play("confirm", 0.8)
        self.game.transition(lambda: self.game.replace_all(Gameplay(self.game, state)), speed=1.4)

    def handle_event(self, e):
        if e.type != pygame.KEYDOWN:
            return
        if e.key in (pygame.K_UP, pygame.K_w):
            self.sel = (self.sel - 1) % len(self.options)
            assets.play("select", 0.5)
        elif e.key in (pygame.K_DOWN, pygame.K_s):
            self.sel = (self.sel + 1) % len(self.options)
            assets.play("select", 0.5)
        elif e.key in (pygame.K_RETURN, pygame.K_SPACE, pygame.K_e, pygame.K_KP_ENTER):
            o = self.options[self.sel]
            if o == "Continue":
                d = save_manager.load()
                self.start(GameState.from_dict(d) if d else GameState())
            elif o == "New Game":
                save_manager.delete()
                self.start(GameState())
            elif o == "Controls":
                assets.play("select", 0.5)
                self.game.push(Controls(self.game))
            elif o == "Options":
                assets.play("select", 0.5)
                self.game.push(Options(self.game))
            else:
                self.game.running = False
        elif e.key == pygame.K_ESCAPE:
            self.game.running = False

    def update(self, dt):
        self.t += dt
        for d in self.dust:
            d[0] += math.sin(self.t * 0.3 + d[2]) * dt * 6
            d[1] -= d[3] * dt * 6
            if d[1] < -5:
                d[1] = H + 5
                d[0] = random.uniform(0, W)
        self.glitch -= dt
        if self.glitch < -random.uniform(2.5, 5.0):
            self.glitch = 0.18

    def draw(self, surf):
        bw, bh = self.bg.get_size()
        ox = (bw - W) / 2 + math.sin(self.t * 0.07) * (bw - W) / 2 * 0.8
        oy = (bh - H) / 2 + math.cos(self.t * 0.05) * (bh - H) / 2 * 0.6
        surf.blit(self.bg, (-ox, -oy))
        # pulse on the robot's core
        cx, cy = bw * 0.495 - ox, bh * 0.4 - oy
        g = pygame.Surface((300, 300))
        g.fill((0, 0, 0))
        k = 0.5 + 0.5 * math.sin(self.t * 1.8)
        for i in range(12, 0, -1):
            c = int(9 * k * (13 - i))
            pygame.draw.circle(g, (c // 3, c, min(255, c * 2)), (150, 150), i * 12)
        surf.blit(g, (cx - 150, cy - 150), special_flags=pygame.BLEND_ADD)
        for (x, y, s, sp) in self.dust:
            a = int(80 + 60 * math.sin(self.t + s))
            pygame.draw.circle(surf, (a, a, min(255, a + 30)), (int(x), int(y)), 1)

        surf.blit(self.shade, (0, 0))

        # logo with chromatic glitch
        gx = random.randint(-6, 6) if self.glitch > 0 else 0
        y = 70
        text(surf, "ECHO//ZERO", (60 + gx + 3, y), 64, (255, 50, 60), bold=True, shadow=False, alpha=110)
        text(surf, "ECHO//ZERO", (60 - gx - 3, y), 64, (40, 200, 255), bold=True, shadow=False, alpha=110)
        text(surf, "ECHO//ZERO", (60, y), 64, WHITE, bold=True)
        text(surf, "T H E   L A S T   S I G N A L", (64, y + 82), 17, CYAN, bold=True)
        pygame.draw.line(surf, CYAN, (64, y + 112), (64 + int(330 * min(1, self.t / 1.5)), y + 112), 2)

        y = H - 70 - len(self.options) * 44
        for i, o in enumerate(self.options):
            sel = i == self.sel
            col = WHITE if sel else GREY
            if sel:
                w = assets.font(22, True).size(o)[0]
                s = pygame.Surface((w + 60, 38), pygame.SRCALPHA)
                s.fill((90, 210, 255, 40 + int(20 * math.sin(self.t * 5))))
                surf.blit(s, (52, y - 6))
                pygame.draw.rect(surf, CYAN, (52, y - 6, 4, 38))
            text(surf, o, (72, y), 22, col, bold=sel)
            y += 44
        text(surf, "A maintenance robot. A failing reactor. An AI that insists everything is fine.",
             (W - 20, H - 18), 12, GREY, anchor="bottomright")
        surf.blit(post_fx(), (0, 0))
