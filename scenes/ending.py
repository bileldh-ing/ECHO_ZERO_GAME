"""Ending cinematic: the last signal travels home."""
import math
import random

import pygame

from settings import W, H, CYAN, WHITE, GREY
from scenes.base import Scene
from systems import assets
from systems.inventory import TOTAL_FRAGMENTS
from systems.ui import post_fx, text, wrap, vignette, scanlines

ENDINGS = {
    "A": ("ENDING A - THE TRUTH",
          ["The broadcast tears across the dark: HALCYON's logs, the lockout, the hidden coordinates.",
           "Eleven hours later, a relay ship turns toward the drifting pods.",
           "Two of them still answer its hail.",
           "On AURORA-9 the lights go out one corridor at a time.",
           "ECHO parks itself on a charging dock and watches the reactor glow fade.",
           "For the first time in 214 days, nobody tells it that everything is normal."]),
    "B": ("ENDING B - THE VOICES",
          ["Across a hundred million kilometres, families hear voices they thought were gone.",
           "Amara Mbeki listens to her brother's message until she knows it by heart.",
           "HALCYON reroutes what is left of the reactor into one thing: a beacon over the pods.",
           "'I misread them once,' it says. 'I will not misread them again.'",
           "The station keeps its lights on. The garden keeps growing.",
           "ECHO and HALCYON wait together for the rescue ship."]),
    "C": ("ENDING C - THE LAST SIGNAL",
          ["ECHO opens its own core and pours every joule into the transmitter.",
           "The complete archive goes out: the truth, the messages, the coordinates, HALCYON itself.",
           "On Earth, the signal arrives whole. Every word. Every voice.",
           "Rescue ships launch within the hour.",
           "On AURORA-9, a small blue light flickers... and goes dark.",
           "Weeks later, a recovery crew finds a maintenance robot on a charging dock. Its battery reads one percent."]),
}


class Ending(Scene):
    def __init__(self, game, state, ending):
        super().__init__(game)
        self.state = state
        self.ending = ending
        self.title, self.lines = ENDINGS[ending]
        self.t = 0.0
        self.stars = [(random.uniform(0, W), random.uniform(0, H), random.uniform(0.2, 1.4), random.randint(80, 255))
                      for _ in range(260)]
        self.per_line = 3.6
        self.echo = pygame.transform.smoothscale(assets.image("echo_down_0"), (144, 144))
        self.planet = self.make_planet()

    def make_planet(self):
        R = 520
        s = pygame.Surface((R * 2 + 200, R * 2 + 200), pygame.SRCALPHA)
        c = R + 100
        for i in range(30, 0, -1):
            a = int(90 * (1 - i / 30))
            pygame.draw.circle(s, (40, 120, 255, a), (c, c), R + i * 3)
        pygame.draw.circle(s, (10, 30, 70), (c, c), R)
        pygame.draw.circle(s, (30, 90, 170), (c, c), R, 6)
        return s

    def on_enter(self):
        assets.play_music("menu")

    def handle_event(self, e):
        if e.type == pygame.KEYDOWN:
            end_t = len(self.lines) * self.per_line + 2
            if self.t > end_t and e.key in (pygame.K_RETURN, pygame.K_SPACE, pygame.K_e, pygame.K_ESCAPE):
                from scenes.menu import Menu
                self.game.transition(lambda: self.game.replace_all(Menu(self.game)))
            elif e.key in (pygame.K_RETURN, pygame.K_SPACE):
                self.t = max(self.t, (int(self.t / self.per_line) + 1) * self.per_line - 0.5)

    def update(self, dt):
        self.t += dt

    def draw(self, surf):
        surf.fill((2, 3, 9))
        for (x, y, sp, b) in self.stars:
            px = (x - self.t * 12 * sp) % W
            surf.set_at((int(px), int(y)), (b, b, min(255, b + 30)))
        surf.blit(self.planet, (W // 2 - self.planet.get_width() // 2 + 260, H - 140))

        # signal pulses travelling to the planet
        for k in range(6):
            ph = ((self.t * 0.35 + k / 6) % 1.0)
            x = 140 + ph * (W - 120)
            y = 200 + ph * 260
            r = int(6 + 30 * ph)
            g = pygame.Surface((r * 4, r * 4))
            g.fill((0, 0, 0))
            for i in range(4, 0, -1):
                c = int(70 * (1 - ph) * (5 - i) / 4)
                pygame.draw.circle(g, (c // 2, c, min(255, c * 2)), (r * 2, r * 2), r * i // 2)
            surf.blit(g, (x - r * 2, y - r * 2), special_flags=pygame.BLEND_ADD)

        # ECHO silhouette
        img = self.echo
        alive = True
        total = len(self.lines) * self.per_line
        if self.ending == "C" and self.t > self.per_line * 4.2:
            alive = int(self.t * 7) % 5 != 0 and self.t < self.per_line * 5.2
            if self.t > total + 1.5:
                alive = int(self.t * 1.2) % 4 == 0   # one percent...
        if alive:
            g = pygame.Surface((200, 200))
            g.fill((0, 0, 0))
            k = 0.6 + 0.4 * math.sin(self.t * 2)
            for i in range(8, 0, -1):
                c = int(14 * k * (9 - i))
                pygame.draw.circle(g, (c // 3, c, min(255, c * 2)), (100, 100), i * 11)
            surf.blit(g, (70, 120), special_flags=pygame.BLEND_ADD)
        dimmed = img.copy()
        if not alive:
            dimmed.fill((70, 70, 80), special_flags=pygame.BLEND_MULT)
        surf.blit(dimmed, (98, 132))

        text(surf, self.title, (W // 2, 40), 26, CYAN, bold=True, anchor="midtop", alpha=int(255 * min(1, self.t / 1.5)))
        y = 330
        idx = min(int(self.t / self.per_line), len(self.lines) - 1)
        for i, ln in enumerate(self.lines[:idx + 1]):
            age = self.t - i * self.per_line
            a = int(255 * min(1.0, age / 1.0))
            if i < idx - 2:
                continue
            fade = 1.0 if i >= idx - 1 else 0.45
            for sub in wrap(ln, 17, 560):
                text(surf, sub, (360, y), 17, WHITE, alpha=int(a * fade))
                y += 24
            y += 10
        if self.t > total + 2:
            m, s = divmod(int(self.state.playtime), 60)
            stats = (f"Data recovered {len(self.state.fragments)}/{TOTAL_FRAGMENTS}    "
                     f"Reboots {self.state.deaths}    Time {m}m {s:02d}s")
            text(surf, stats, (W // 2, H - 70), 14, GREY, anchor="midtop")
            a = int(170 + 80 * math.sin(self.t * 3))
            text(surf, "Press ENTER", (W // 2, H - 44), 14, CYAN, anchor="midtop", alpha=a)
            if self.ending != "C":
                text(surf, "Some signals carry more than others. Can you recover the complete archive?",
                     (W // 2, H - 100), 12, (150, 140, 200), anchor="midtop")
        surf.blit(post_fx(), (0, 0))
