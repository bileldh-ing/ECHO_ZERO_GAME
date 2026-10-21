"""ECHO//ZERO - The Last Signal.

A 2D sci-fi action-adventure about a maintenance robot on a dying orbital station.
Run:  python main.py        (requires pygame or pygame-ce 2.x)
"""
import os
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import pygame  # noqa: E402

from settings import W, H, FPS, TITLE  # noqa: E402
from systems import assets  # noqa: E402


class Game:
    def __init__(self, headless=False):
        assets.init_audio()
        pygame.init()
        pygame.display.set_caption(TITLE)
        flags = pygame.SCALED | pygame.RESIZABLE
        try:
            self.screen = pygame.display.set_mode((W, H), flags, vsync=1)
        except Exception:
            self.screen = pygame.display.set_mode((W, H), flags)
        assets.ensure_generated()
        try:
            icon = assets.image("echo_down_0")
            pygame.display.set_icon(icon)
        except Exception:
            pass
        self.clock = pygame.time.Clock()
        self.scenes = []
        self.running = True
        self.fade = 0.0          # 0 = clear, 1 = black
        self.fade_target = 0.0
        self.fade_speed = 2.5
        self.fade_cb = None
        self._black = pygame.Surface((W, H))
        self.time = 0.0
        self.show_fps = False

    # ------------------------------------------------------------------ scene stack
    @property
    def top(self):
        return self.scenes[-1] if self.scenes else None

    def push(self, scene):
        self.scenes.append(scene)
        scene.on_enter()

    def pop(self):
        if self.scenes:
            return self.scenes.pop()

    def remove(self, scene):
        if scene in self.scenes:
            self.scenes.remove(scene)

    def replace_all(self, scene):
        self.scenes = []
        self.push(scene)

    def transition(self, callback, speed=2.5):
        """Fade to black, run callback, fade back in."""
        if self.fade_cb is not None:
            return
        self.fade_speed = speed
        self.fade_target = 1.0
        self.fade_cb = callback

    # ------------------------------------------------------------------ loop
    def step(self, dt, events):
        self.time += dt
        for e in events:
            if e.type == pygame.QUIT:
                self.running = False
            elif e.type == pygame.KEYDOWN and e.key == pygame.K_F11:
                pygame.display.toggle_fullscreen()
            elif e.type == pygame.KEYDOWN and e.key == pygame.K_F3:
                self.show_fps = not self.show_fps
            elif self.top and self.fade_cb is None:
                self.top.handle_event(e)
        if self.top:
            self.top.update(dt)
        # fade
        if self.fade < self.fade_target:
            self.fade = min(self.fade_target, self.fade + dt * self.fade_speed)
            if self.fade >= 1.0 and self.fade_cb:
                cb, self.fade_cb = self.fade_cb, None
                cb()
                self.fade_target = 0.0
        elif self.fade > self.fade_target:
            self.fade = max(self.fade_target, self.fade - dt * self.fade_speed)

    def render(self):
        start = len(self.scenes) - 1
        while start > 0 and self.scenes[start].overlay:
            start -= 1
        for s in self.scenes[max(0, start):]:
            s.draw(self.screen)
        if self.fade > 0:
            self._black.set_alpha(int(255 * self.fade))
            self.screen.blit(self._black, (0, 0))
        if self.show_fps:
            from systems.ui import text
            text(self.screen, f"{self.clock.get_fps():.0f} fps", (W - 8, H - 8), 12, anchor="bottomright")

    def run(self):
        from scenes.menu import Menu
        self.push(Menu(self))
        while self.running and self.scenes:
            dt = min(self.clock.tick(FPS) / 1000.0, 1 / 20)
            self.step(dt, pygame.event.get())
            self.render()
            pygame.display.flip()
        pygame.quit()


if __name__ == "__main__":
    Game().run()
