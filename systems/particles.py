"""Lightweight particle system (sparks, dust, spores, scan pulses)."""
import math
import random

import pygame


class Particle:
    __slots__ = ("x", "y", "vx", "vy", "life", "max_life", "color", "size", "glow", "drag", "grav")

    def __init__(self, x, y, vx, vy, life, color, size, glow=False, drag=0.0, grav=0.0):
        self.x, self.y, self.vx, self.vy = x, y, vx, vy
        self.life = self.max_life = life
        self.color, self.size, self.glow, self.drag, self.grav = color, size, glow, drag, grav


class Particles:
    def __init__(self):
        self.items = []
        self._dots = {}

    def dot(self, size, color, level=8):
        """Additive glow dot on black (RGB), pre-faded to one of 8 brightness levels."""
        key = (size, color, level)
        s = self._dots.get(key)
        if s is None:
            dim = size * 6
            s = pygame.Surface((dim, dim))
            s.fill((0, 0, 0))
            c = dim // 2
            k = level / 8
            for i in range(6, 0, -1):
                f = (1 - i / 6) ** 1.5 * k if i > 1 else k
                col = tuple(min(255, int(v * f)) for v in color)
                pygame.draw.circle(s, col, (c, c), max(1, int(size * i / 2)))
            self._dots[key] = s
        return s

    def emit(self, x, y, n, color, speed=60, life=0.6, size=2, glow=True, spread=math.tau, angle=0, drag=2.0, grav=0.0):
        for _ in range(n):
            a = angle + random.uniform(-spread / 2, spread / 2)
            v = random.uniform(speed * 0.3, speed)
            self.items.append(Particle(x, y, math.cos(a) * v, math.sin(a) * v,
                                       random.uniform(life * 0.5, life), color, size, glow, drag, grav))

    def sparks(self, x, y, n=8):
        self.emit(x, y, n, (255, 210, 120), speed=140, life=0.5, size=1, drag=3.0, grav=160)

    def update(self, dt):
        alive = []
        for p in self.items:
            p.life -= dt
            if p.life <= 0:
                continue
            k = max(0.0, 1 - p.drag * dt)
            p.vx *= k
            p.vy = p.vy * k + p.grav * dt
            p.x += p.vx * dt
            p.y += p.vy * dt
            alive.append(p)
        self.items = alive[-900:]

    def draw(self, surf, cam_x, cam_y, glow_pass):
        for p in self.items:
            if p.glow != glow_pass:
                continue
            t = p.life / p.max_life
            sx, sy = p.x - cam_x, p.y - cam_y
            if glow_pass:
                d = self.dot(p.size, p.color, max(1, min(8, int(t * 8 + 0.999))))
                surf.blit(d, (sx - d.get_width() / 2, sy - d.get_height() / 2), special_flags=pygame.BLEND_ADD)
            else:
                c = tuple(int(v * (0.4 + 0.6 * t)) for v in p.color)
                pygame.draw.circle(surf, c, (int(sx), int(sy)), p.size)
