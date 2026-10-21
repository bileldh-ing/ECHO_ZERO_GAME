"""Procedural asset generator for ECHO//ZERO.

Creates every sprite, tile, UI image, sound effect and music loop the game uses,
using only pygame and the Python standard library. Run it directly:

    python tools/generate_assets.py

The game also calls generate_all() automatically if the assets folder is empty.
"""
import math
import os
import random
import struct
import sys
import wave

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

if __name__ == "__main__":
    os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
    os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame  # noqa: E402

ASSETS = os.path.join(ROOT, "assets")
SPR = os.path.join(ASSETS, "sprites")
TIL = os.path.join(ASSETS, "tiles")
UI = os.path.join(ASSETS, "ui")
SND = os.path.join(ASSETS, "sounds")
MUS = os.path.join(ASSETS, "music")

T = 32


# --------------------------------------------------------------------------- helpers
def surf(w, h):
    return pygame.Surface((w, h), pygame.SRCALPHA)


def save(s, folder, name):
    os.makedirs(folder, exist_ok=True)
    pygame.image.save(s, os.path.join(folder, name + ".png"))


def down(s, factor=2):
    return pygame.transform.smoothscale(s, (s.get_width() // factor, s.get_height() // factor))


def shade(c, k):
    return tuple(max(0, min(255, int(v * k))) for v in c[:3])


def mix(a, b, t):
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


def glow(s, center, radius, color, strength=1.0):
    """Soft alpha glow made of stacked circles."""
    g = surf(radius * 2, radius * 2)
    steps = max(4, radius // 2)
    for i in range(steps, 0, -1):
        r = int(radius * i / steps)
        a = int(255 * strength * (1 - i / steps) ** 1.6 * 0.55)
        pygame.draw.circle(g, (*color[:3], min(255, a)), (radius, radius), r)
    s.blit(g, (center[0] - radius, center[1] - radius))


def noise_fill(s, rect, base, amount, rng, density=0.35):
    x0, y0, w, h = rect
    for _ in range(int(w * h * density)):
        x = rng.randrange(x0, x0 + w)
        y = rng.randrange(y0, y0 + h)
        k = 1 + rng.uniform(-amount, amount)
        s.set_at((x, y), shade(base, k))


# --------------------------------------------------------------------------- ECHO
def draw_echo(direction, frame):
    S = 96  # drawn at 2x for a 48px sprite
    s = surf(S, S)
    cx = S // 2
    bob = [0, -2, 0, -2][frame]
    step = [0, 3, 0, -3][frame]
    steel = (66, 78, 96)
    steel_hi = (120, 136, 158)
    steel_lo = (34, 40, 52)
    fin = (150, 160, 175)

    # shadow
    pygame.draw.ellipse(s, (0, 0, 0, 110), (cx - 24, 78, 48, 12))

    # legs
    if direction in ("down", "up"):
        for side, off in ((-1, step), (1, -step)):
            lx = cx + side * 14
            pygame.draw.line(s, steel_lo, (lx, 60 + bob), (lx + side * 4, 80 + off // 2), 6)
            pygame.draw.circle(s, steel_hi, (lx + side * 4, 81 + off // 2), 4)
    else:
        d = 1 if direction == "right" else -1
        for off, col in ((step, steel_lo), (-step, shade(steel_lo, 0.8))):
            pygame.draw.line(s, col, (cx, 60 + bob), (cx + off * d, 81), 6)
            pygame.draw.circle(s, steel_hi, (cx + off * d, 82), 4)

    # fins (the angled side arms from the key art)
    if direction in ("down", "up"):
        for side in (-1, 1):
            pts = [(cx + side * 22, 58 + bob), (cx + side * 34, 18 + bob),
                   (cx + side * 38, 22 + bob), (cx + side * 28, 62 + bob)]
            pygame.draw.polygon(s, fin, pts)
            pygame.draw.polygon(s, steel_lo, pts, 2)
    else:
        d = 1 if direction == "right" else -1
        pts = [(cx - d * 10, 58 + bob), (cx - d * 22, 16 + bob),
               (cx - d * 16, 14 + bob), (cx - d * 2, 56 + bob)]
        pygame.draw.polygon(s, fin, pts)
        pygame.draw.polygon(s, steel_lo, pts, 2)

    # body
    bw = 44 if direction in ("down", "up") else 36
    body = pygame.Rect(cx - bw // 2, 26 + bob, bw, 40)
    pygame.draw.rect(s, steel_lo, body.inflate(4, 4), border_radius=12)
    pygame.draw.rect(s, steel, body, border_radius=11)
    top = pygame.Rect(body.x + 3, body.y + 3, body.w - 6, 10)
    pygame.draw.rect(s, steel_hi, top, border_radius=6)
    # bolts
    for bx in (body.x + 6, body.right - 7):
        pygame.draw.circle(s, steel_lo, (bx, body.bottom - 7), 2)

    # antenna
    pygame.draw.line(s, steel_lo, (cx + 8, body.y), (cx + 12, body.y - 12), 3)
    pygame.draw.circle(s, (120, 230, 255), (cx + 12, body.y - 13), 3)

    ey = body.y + 22
    if direction == "down":
        pygame.draw.circle(s, (14, 22, 34), (cx, ey), 15)
        glow(s, (cx, ey), 22, (70, 200, 255), 1.0)
        pygame.draw.circle(s, (40, 150, 230), (cx, ey), 12)
        pygame.draw.circle(s, (120, 225, 255), (cx, ey), 9)
        pygame.draw.circle(s, (14, 40, 70), (cx, ey), 6)
        pygame.draw.circle(s, (210, 250, 255), (cx, ey), 4)
        pygame.draw.circle(s, (255, 255, 255), (cx - 4, ey - 4), 2)
    elif direction == "up":
        for i in range(4):
            pygame.draw.line(s, steel_lo, (body.x + 8, body.y + 18 + i * 5), (body.right - 8, body.y + 18 + i * 5), 2)
        pygame.draw.circle(s, (90, 220, 255), (cx, body.bottom - 8), 3)
    else:
        d = 1 if direction == "right" else -1
        ex = cx + d * 9
        pygame.draw.ellipse(s, (14, 22, 34), (ex - 9, ey - 14, 18, 28))
        glow(s, (ex + d * 2, ey), 18, (70, 200, 255), 1.0)
        pygame.draw.ellipse(s, (60, 180, 245), (ex - 6 + d * 2, ey - 11, 12, 22))
        pygame.draw.ellipse(s, (200, 245, 255), (ex - 2 + d * 3, ey - 5, 6, 10))
    return down(s)


# --------------------------------------------------------------------------- drone
def draw_drone(frame, mode):
    S = 88
    s = surf(S, S)
    c = S // 2
    eye = {"normal": (255, 70, 55), "alert": (255, 40, 30), "off": (70, 70, 80), "sus": (255, 190, 60)}[mode]
    body = (46, 48, 58)
    rim = (92, 96, 110)
    ang0 = frame * 45
    for k in range(4):
        a = math.radians(45 + 90 * k)
        rx, ry = c + math.cos(a) * 28, c + math.sin(a) * 28
        pygame.draw.line(s, rim, (c, c), (rx, ry), 5)
        pygame.draw.circle(s, (30, 32, 40), (int(rx), int(ry)), 11)
        pygame.draw.circle(s, (130, 140, 160, 70), (int(rx), int(ry)), 11)
        for b in range(2):
            ba = math.radians(ang0 + b * 90 + k * 20)
            pygame.draw.line(s, (180, 190, 205, 160), (rx - math.cos(ba) * 10, ry - math.sin(ba) * 10),
                             (rx + math.cos(ba) * 10, ry + math.sin(ba) * 10), 2)
    pygame.draw.circle(s, (20, 20, 26), (c, c), 21)
    pygame.draw.circle(s, body, (c, c), 19)
    pygame.draw.circle(s, rim, (c, c), 19, 3)
    pygame.draw.arc(s, (170, 176, 190), (c - 16, c - 16, 32, 32), math.radians(100), math.radians(170), 2)
    pygame.draw.circle(s, (24, 24, 30), (c + 9, c), 9)
    if mode != "off":
        glow(s, (c + 10, c), 18, eye, 1.0)
    pygame.draw.circle(s, eye, (c + 10, c), 6)
    pygame.draw.circle(s, (255, 230, 220) if mode != "off" else (110, 110, 120), (c + 11, c - 1), 2)
    return down(s)


# --------------------------------------------------------------------------- tiles
PALETTES = {
    "maint":   dict(floor=(58, 66, 80), wall_top=(26, 30, 38), wall_face=(52, 60, 74), accent=(70, 170, 230)),
    "garden":  dict(floor=(54, 66, 60), wall_top=(24, 32, 28), wall_face=(48, 62, 54), accent=(90, 220, 140)),
    "reactor": dict(floor=(72, 60, 54), wall_top=(34, 26, 24), wall_face=(70, 52, 44), accent=(255, 140, 60)),
    "command": dict(floor=(48, 58, 82), wall_top=(22, 26, 42), wall_face=(44, 52, 78), accent=(90, 190, 255)),
    "signal":  dict(floor=(62, 50, 56), wall_top=(28, 20, 24), wall_face=(62, 42, 48), accent=(255, 70, 70)),
}


def tile_floor(p, variant, rng):
    s = surf(T, T)
    base = p["floor"]
    s.fill(shade(base, 0.92))
    noise_fill(s, (0, 0, T, T), base, 0.08, rng)
    pygame.draw.rect(s, shade(base, 1.18), (0, 0, T, T), 1)
    pygame.draw.line(s, shade(base, 0.6), (0, T - 1), (T - 1, T - 1))
    pygame.draw.line(s, shade(base, 0.6), (T - 1, 0), (T - 1, T - 1))
    for (x, y) in ((3, 3), (T - 4, 3), (3, T - 4), (T - 4, T - 4)):
        s.set_at((x, y), shade(base, 0.55))
        s.set_at((x - 1, y - 1), shade(base, 1.3))
    if variant == 1:
        for _ in range(3):
            x, y = rng.randrange(4, 28), rng.randrange(4, 28)
            pygame.draw.line(s, shade(base, 0.75), (x, y), (x + rng.randrange(-6, 7), y + rng.randrange(-3, 4)))
    elif variant == 2:
        pygame.draw.rect(s, shade(base, 0.8), (8, 8, 16, 16), 1)
    elif variant == 3:
        pygame.draw.circle(s, shade(base, 0.7, ), (16, 16), 4, 1)
    return s


def tile_grate(p, rng):
    s = surf(T, T)
    base = p["floor"]
    s.fill(shade(base, 0.45))
    for y in range(3, T - 2, 4):
        pygame.draw.line(s, shade(base, 0.9), (3, y), (T - 4, y), 2)
    pygame.draw.rect(s, shade(base, 1.1), (0, 0, T, T), 2)
    return s


def tile_line(p, rng):
    s = tile_floor(p, 0, rng)
    pygame.draw.rect(s, shade(p["accent"], 0.5), (0, 13, T, 6))
    pygame.draw.rect(s, p["accent"], (0, 15, T, 2))
    return s


def tile_hazard(p, rng):
    s = tile_floor(p, 0, rng)
    stripe = surf(T, T)
    for i in range(-T, T * 2, 10):
        pygame.draw.polygon(stripe, (220, 170, 40, 200), [(i, 0), (i + 5, 0), (i + 5 - T, T), (i - T, T)])
    s.blit(stripe, (0, 0))
    pygame.draw.rect(s, (30, 30, 30), (0, 0, T, T), 2)
    return s


def tile_wall_top(p, rng):
    s = surf(T, T)
    s.fill(p["wall_top"])
    noise_fill(s, (0, 0, T, T), p["wall_top"], 0.12, rng, 0.2)
    pygame.draw.rect(s, shade(p["wall_top"], 1.35), (0, 0, T, T), 1)
    return s


def tile_wall_front(p, rng, window=False):
    s = surf(T, T)
    s.fill(p["wall_top"])
    pygame.draw.rect(s, shade(p["wall_top"], 1.35), (0, 0, T, 10), 1)
    face = pygame.Rect(0, 10, T, T - 10)
    pygame.draw.rect(s, p["wall_face"], face)
    noise_fill(s, (0, 10, T, T - 10), p["wall_face"], 0.07, rng, 0.3)
    pygame.draw.line(s, shade(p["wall_face"], 1.4), (0, 10), (T, 10), 2)
    pygame.draw.line(s, shade(p["wall_face"], 0.55), (0, T - 1), (T, T - 1), 2)
    if window:
        win = pygame.Rect(4, 13, T - 8, T - 18)
        pygame.draw.rect(s, (4, 6, 14), win)
        for _ in range(7):
            x = rng.randrange(win.x + 1, win.right - 1)
            y = rng.randrange(win.y + 1, win.bottom - 1)
            v = rng.randrange(120, 255)
            s.set_at((x, y), (v, v, min(255, v + 30)))
        pygame.draw.line(s, (90, 120, 170, 120), (win.x + 2, win.bottom - 2), (win.x + 8, win.y + 1))
        pygame.draw.rect(s, shade(p["wall_face"], 1.5), win, 1)
    else:
        pygame.draw.line(s, shade(p["wall_face"], 0.7), (T // 2, 12), (T // 2, T - 3))
        if rng.random() < 0.4:
            pygame.draw.rect(s, shade(p["accent"], 0.8), (6, 18, 4, 2))
    return s


def tile_water(p, frame):
    s = surf(T, T)
    s.fill((18, 52, 70))
    for i in range(5):
        y = (i * 7 + frame * 2) % T
        for x in range(0, T, 2):
            yy = int(y + math.sin((x + frame * 4) * 0.35) * 1.5)
            if 0 <= yy < T:
                s.set_at((x, yy), (60, 150, 190))
    pygame.draw.rect(s, (40, 80, 90), (0, 0, T, T), 1)
    return s


def tile_soil(p, rng):
    s = surf(T, T)
    s.fill((52, 40, 30))
    noise_fill(s, (0, 0, T, T), (60, 46, 34), 0.25, rng, 0.6)
    return s


def tile_bed(p, rng):
    s = surf(T, T)
    s.fill((40, 46, 44))
    pygame.draw.rect(s, (38, 30, 24), (2, 2, T - 4, T - 4))
    noise_fill(s, (2, 2, T - 4, T - 4), (54, 42, 32), 0.3, rng, 0.5)
    for _ in range(6):
        x, y = rng.randrange(5, 27), rng.randrange(5, 27)
        col = rng.choice([(70, 160, 80), (90, 190, 90), (50, 130, 70), (120, 200, 110)])
        for k in range(4):
            a = rng.uniform(0, math.tau)
            pygame.draw.line(s, col, (x, y), (x + math.cos(a) * 5, y + math.sin(a) * 5), 2)
    pygame.draw.rect(s, (90, 100, 96), (0, 0, T, T), 2)
    return s


def tile_space(rng):
    s = surf(T, T)
    s.fill((3, 4, 10))
    for _ in range(rng.randrange(1, 4)):
        v = rng.randrange(90, 230)
        s.set_at((rng.randrange(T), rng.randrange(T)), (v, v, min(255, v + 25)))
    return s


# --------------------------------------------------------------------------- objects
def obj_terminal(on):
    s = surf(64, 64)
    pygame.draw.ellipse(s, (0, 0, 0, 90), (8, 52, 48, 10))
    pygame.draw.rect(s, (40, 46, 58), (10, 14, 44, 42), border_radius=6)
    pygame.draw.rect(s, (80, 90, 108), (10, 14, 44, 42), 2, border_radius=6)
    scr = pygame.Rect(16, 20, 32, 20)
    pygame.draw.rect(s, (8, 30, 40) if on else (12, 14, 18), scr)
    if on:
        for i in range(4):
            pygame.draw.line(s, (90, 220, 255), (19, 24 + i * 4), (19 + [24, 16, 20, 10][i], 24 + i * 4), 1)
    pygame.draw.rect(s, (110, 120, 140), scr, 1)
    for i in range(5):
        pygame.draw.rect(s, (24, 28, 36), (16 + i * 7, 45, 5, 4))
    return down(s)


def obj_broken_terminal():
    s = obj_terminal(True)
    pygame.draw.line(s, (255, 255, 255), (9, 10), (17, 18), 1)
    pygame.draw.line(s, (255, 80, 80), (12, 11), (20, 15), 1)
    pygame.draw.line(s, (40, 40, 40), (14, 9), (12, 17), 1)
    return s


def obj_panel(on):
    s = surf(64, 64)
    pygame.draw.ellipse(s, (0, 0, 0, 90), (10, 54, 44, 8))
    pygame.draw.rect(s, (54, 50, 40), (12, 8, 40, 48), border_radius=4)
    pygame.draw.rect(s, (200, 160, 50), (12, 8, 40, 48), 2, border_radius=4)
    for i in range(3):
        y = 16 + i * 12
        pygame.draw.rect(s, (24, 22, 18), (18, y, 28, 7))
        pygame.draw.rect(s, (90, 230, 255) if on else (90, 40, 30), (20 + i * 6, y + 2, 10, 3))
    pygame.draw.polygon(s, (230, 190, 60), [(32, 48), (28, 54), (31, 54), (29, 60), (36, 52), (33, 52), (35, 48)])
    return down(s)


def obj_switch(on):
    s = surf(64, 64)
    pygame.draw.rect(s, (46, 50, 60), (18, 14, 28, 38), border_radius=5)
    pygame.draw.rect(s, (100, 110, 125), (18, 14, 28, 38), 2, border_radius=5)
    pygame.draw.rect(s, (20, 22, 28), (28, 20, 8, 26))
    ky = 22 if on else 36
    pygame.draw.rect(s, (220, 225, 235), (24, ky, 16, 8), border_radius=3)
    pygame.draw.circle(s, (80, 240, 140) if on else (240, 70, 60), (32, 50), 3)
    return down(s)


def obj_dock():
    s = surf(64, 64)
    pygame.draw.ellipse(s, (30, 36, 46), (4, 8, 56, 48))
    pygame.draw.ellipse(s, (90, 210, 255), (4, 8, 56, 48), 2)
    pygame.draw.ellipse(s, (60, 140, 190), (14, 16, 36, 32), 2)
    pygame.draw.ellipse(s, (40, 90, 130), (24, 24, 16, 16))
    for k in range(8):
        a = math.radians(k * 45)
        pygame.draw.circle(s, (120, 230, 255), (int(32 + math.cos(a) * 24), int(32 + math.sin(a) * 20)), 2)
    return down(s)


def obj_lamp(on):
    s = surf(32, 32)
    pygame.draw.rect(s, (60, 64, 74), (10, 4, 12, 8), border_radius=2)
    pygame.draw.rect(s, (250, 240, 200) if on else (60, 60, 60), (12, 10, 8, 4))
    return s


def obj_crate(rng):
    s = surf(64, 64)
    pygame.draw.ellipse(s, (0, 0, 0, 100), (4, 52, 56, 10))
    pygame.draw.rect(s, (78, 74, 62), (6, 10, 52, 46), border_radius=3)
    pygame.draw.rect(s, (120, 112, 90), (6, 10, 52, 12), border_radius=3)
    pygame.draw.rect(s, (40, 38, 32), (6, 10, 52, 46), 2, border_radius=3)
    pygame.draw.line(s, (50, 48, 40), (8, 26), (56, 54), 3)
    pygame.draw.rect(s, (220, 170, 40), (10, 44, 14, 4))
    return down(s)


def obj_barrel():
    s = surf(64, 64)
    pygame.draw.ellipse(s, (0, 0, 0, 100), (10, 52, 44, 10))
    pygame.draw.rect(s, (70, 90, 110), (14, 14, 36, 42))
    pygame.draw.ellipse(s, (110, 130, 150), (14, 6, 36, 16))
    pygame.draw.ellipse(s, (60, 76, 94), (20, 9, 24, 9))
    pygame.draw.ellipse(s, (50, 66, 84), (14, 48, 36, 14))
    pygame.draw.rect(s, (220, 170, 40), (14, 30, 36, 5))
    return down(s)


def obj_plant(rng):
    s = surf(64, 64)
    pygame.draw.ellipse(s, (0, 0, 0, 90), (14, 52, 36, 9))
    pygame.draw.rect(s, (70, 76, 84), (20, 40, 24, 16), border_radius=4)
    for _ in range(14):
        a = rng.uniform(math.pi * 1.0, math.pi * 2.0)
        L = rng.uniform(12, 26)
        col = rng.choice([(60, 150, 70), (90, 190, 90), (40, 120, 60), (130, 210, 110)])
        ex, ey = 32 + math.cos(a) * L, 40 + math.sin(a) * L
        pygame.draw.line(s, col, (32, 42), (ex, ey), 4)
        pygame.draw.circle(s, col, (int(ex), int(ey)), 4)
    return down(s)


def obj_vines(rng):
    s = surf(32, 32)
    for _ in range(9):
        x = rng.randrange(0, 32)
        pts = [(x + math.sin(i * 0.9 + x) * 3, i * 4) for i in range(9)]
        pygame.draw.lines(s, rng.choice([(50, 120, 60), (70, 150, 70)]), False, pts, 2)
    return s


def obj_reactor(frame):
    S = 192
    s = surf(S, S)
    c = S // 2
    pulse = 0.5 + 0.5 * math.sin(frame / 8 * math.tau)
    pygame.draw.circle(s, (30, 24, 22), (c, c), 92)
    pygame.draw.circle(s, (90, 70, 60), (c, c), 92, 6)
    for k in range(12):
        a = math.radians(k * 30 + frame * 4)
        pygame.draw.line(s, (60, 46, 40), (c + math.cos(a) * 60, c + math.sin(a) * 60),
                         (c + math.cos(a) * 88, c + math.sin(a) * 88), 6)
    glow(s, (c, c), 80, (255, 140, 50), 0.7 + 0.3 * pulse)
    pygame.draw.circle(s, (255, 120, 40), (c, c), 44)
    pygame.draw.circle(s, (255, 190, 90), (c, c), 32)
    pygame.draw.circle(s, (255, 240, 200), (c, c), int(16 + 6 * pulse))
    pygame.draw.circle(s, (120, 80, 60), (c, c), 52, 4)
    return down(s)


def obj_ai_core(frame):
    S = 192
    s = surf(S, S)
    c = S // 2
    pulse = 0.5 + 0.5 * math.sin(frame / 8 * math.tau)
    pts = [(c + math.cos(math.radians(60 * k + 30)) * 86, c + math.sin(math.radians(60 * k + 30)) * 86) for k in range(6)]
    pygame.draw.polygon(s, (24, 26, 40), pts)
    pygame.draw.polygon(s, (110, 120, 160), pts, 5)
    for r in (64, 50):
        pygame.draw.circle(s, (60, 64, 90), (c, c), r, 3)
    glow(s, (c, c), 70, (255, 60, 50), 0.6 + 0.4 * pulse)
    pygame.draw.circle(s, (120, 20, 20), (c, c), 30)
    pygame.draw.circle(s, (255, 70, 60), (c, c), 22)
    pygame.draw.circle(s, (255, 210, 200), (c, c), int(7 + 4 * pulse))
    return down(s)


def obj_console(on):
    s = surf(64, 64)
    pygame.draw.ellipse(s, (0, 0, 0, 90), (2, 52, 60, 10))
    pygame.draw.polygon(s, (44, 48, 62), [(4, 30), (60, 30), (56, 56), (8, 56)])
    pygame.draw.rect(s, (36, 40, 52), (6, 6, 52, 26), border_radius=4)
    pygame.draw.rect(s, (120, 130, 150), (6, 6, 52, 26), 2, border_radius=4)
    cols = [(255, 140, 60), (90, 210, 255), (255, 80, 70)]
    for i in range(3):
        pygame.draw.rect(s, cols[i] if on else (50, 50, 50), (12 + i * 16, 12, 10, 14))
    for i in range(6):
        pygame.draw.circle(s, (200, 200, 210), (12 + i * 8, 44), 2)
    return down(s)


def obj_transmitter(frame):
    S = 128
    s = surf(S, S)
    c = S // 2
    pygame.draw.ellipse(s, (0, 0, 0, 100), (20, 100, 88, 20))
    pygame.draw.rect(s, (60, 64, 76), (54, 60, 20, 50))
    pygame.draw.ellipse(s, (150, 160, 175), (16, 10, 96, 64))
    pygame.draw.ellipse(s, (90, 98, 112), (26, 18, 76, 48))
    pygame.draw.line(s, (200, 205, 215), (c, 42), (c, 4), 4)
    glow(s, (c, 4), 18, (255, 90, 80) if frame % 2 else (90, 210, 255), 1)
    return down(s)


def obj_holotable(frame):
    S = 128
    s = surf(S, S)
    pygame.draw.ellipse(s, (0, 0, 0, 100), (10, 92, 108, 22))
    pygame.draw.ellipse(s, (40, 46, 66), (10, 50, 108, 56))
    pygame.draw.ellipse(s, (110, 130, 180), (10, 50, 108, 56), 3)
    holo = surf(S, S)
    pygame.draw.circle(holo, (90, 200, 255, 70), (64, 46), 30)
    pygame.draw.circle(holo, (150, 230, 255, 160), (64, 46), 30, 2)
    a = frame * 0.4
    pygame.draw.ellipse(holo, (150, 230, 255, 140), (34, 40 + int(math.sin(a) * 4), 60, 12), 2)
    pygame.draw.circle(holo, (255, 255, 255, 200), (64 + int(math.cos(a) * 26), 46), 4)
    s.blit(holo, (0, 0))
    return down(s)


def obj_exit(frame):
    s = surf(64, 64)
    pygame.draw.rect(s, (30, 36, 46), (2, 2, 60, 60), border_radius=6)
    pygame.draw.rect(s, (90, 210, 255), (2, 2, 60, 60), 2, border_radius=6)
    for i in range(3):
        y = 50 - ((frame * 4 + i * 16) % 48)
        pygame.draw.polygon(s, (90, 210, 255, 200 - i * 50), [(32, y - 8), (20, y + 4), (44, y + 4)])
    return down(s)


def obj_door_panel(p):
    s = surf(T, T)
    s.fill(shade(p["wall_face"], 1.1))
    pygame.draw.rect(s, shade(p["wall_face"], 0.6), (0, 0, T, T), 2)
    for i in range(4):
        pygame.draw.line(s, shade(p["wall_face"], 0.75), (4, 6 + i * 6), (T - 5, 6 + i * 6), 1)
    pygame.draw.polygon(s, (220, 170, 40), [(0, T - 6), (6, T), (0, T)])
    return s


def obj_pipe(vertical):
    s = surf(T, T)
    if vertical:
        pygame.draw.rect(s, (70, 76, 86), (10, 0, 12, T))
        pygame.draw.rect(s, (120, 128, 140), (12, 0, 3, T))
        pygame.draw.rect(s, (50, 54, 62), (8, 12, 16, 6))
    else:
        pygame.draw.rect(s, (70, 76, 86), (0, 10, T, 12))
        pygame.draw.rect(s, (120, 128, 140), (0, 12, T, 3))
        pygame.draw.rect(s, (50, 54, 62), (12, 8, 6, 16))
    return s


def obj_debris(rng):
    s = surf(64, 64)
    for _ in range(9):
        x, y = rng.randrange(8, 56), rng.randrange(16, 56)
        r = rng.randrange(3, 9)
        c = rng.choice([(60, 60, 66), (90, 86, 80), (40, 40, 46)])
        pts = [(x + math.cos(a) * r * rng.uniform(0.6, 1.2), y + math.sin(a) * r * rng.uniform(0.6, 1.2))
               for a in [k * math.tau / 6 for k in range(6)]]
        pygame.draw.polygon(s, c, pts)
    return down(s)


def obj_bed_cryo():
    s = surf(64, 64)
    pygame.draw.rect(s, (40, 46, 58), (6, 4, 52, 56), border_radius=14)
    pygame.draw.rect(s, (110, 170, 200, 120), (12, 10, 40, 44), border_radius=12)
    pygame.draw.rect(s, (160, 220, 255), (12, 10, 40, 44), 2, border_radius=12)
    return down(s)


# --------------------------------------------------------------------------- items
def item_battery():
    s = surf(48, 48)
    glow(s, (24, 24), 22, (110, 240, 150), 0.6)
    pygame.draw.rect(s, (40, 46, 50), (14, 10, 20, 30), border_radius=4)
    pygame.draw.rect(s, (200, 210, 220), (19, 6, 10, 5), border_radius=2)
    for i in range(3):
        pygame.draw.rect(s, (110, 240, 150), (17, 30 - i * 8, 14, 6))
    pygame.draw.rect(s, (220, 230, 240), (14, 10, 20, 30), 2, border_radius=4)
    return down(s)


def item_keycard(color):
    s = surf(48, 48)
    glow(s, (24, 24), 22, color, 0.5)
    pygame.draw.rect(s, color, (8, 14, 32, 22), border_radius=4)
    pygame.draw.rect(s, (255, 255, 255), (8, 14, 32, 22), 2, border_radius=4)
    pygame.draw.rect(s, (230, 200, 90), (12, 20, 8, 7))
    pygame.draw.line(s, (20, 20, 20), (24, 22), (36, 22), 2)
    pygame.draw.line(s, (20, 20, 20), (24, 28), (32, 28), 2)
    return down(s)


def item_component():
    s = surf(48, 48)
    glow(s, (24, 24), 22, (255, 190, 80), 0.5)
    pygame.draw.rect(s, (30, 70, 50), (12, 12, 24, 24), border_radius=2)
    pygame.draw.rect(s, (20, 20, 24), (18, 18, 12, 12))
    for i in range(4):
        for (x0, y0, x1, y1) in ((14 + i * 6, 12, 14 + i * 6, 6), (14 + i * 6, 36, 14 + i * 6, 42),
                                 (12, 14 + i * 6, 6, 14 + i * 6), (36, 14 + i * 6, 42, 14 + i * 6)):
            pygame.draw.line(s, (220, 190, 90), (x0, y0), (x1, y1), 2)
    return down(s)


def item_fragment():
    s = surf(48, 48)
    glow(s, (24, 24), 24, (180, 140, 255), 0.8)
    pts = [(24, 6), (36, 22), (24, 42), (12, 22)]
    pygame.draw.polygon(s, (150, 110, 255), pts)
    pygame.draw.polygon(s, (230, 210, 255), [(24, 6), (30, 22), (24, 30), (18, 22)])
    pygame.draw.polygon(s, (255, 255, 255), pts, 2)
    return down(s)


def item_command_key():
    s = surf(48, 48)
    glow(s, (24, 24), 24, (255, 210, 90), 0.8)
    pygame.draw.circle(s, (240, 200, 80), (16, 24), 9, 4)
    pygame.draw.rect(s, (240, 200, 80), (22, 22, 20, 5))
    pygame.draw.rect(s, (240, 200, 80), (34, 26, 4, 7))
    pygame.draw.rect(s, (240, 200, 80), (39, 26, 3, 5))
    return down(s)


# --------------------------------------------------------------------------- UI
def portrait(kind):
    s = surf(128, 128)
    pygame.draw.rect(s, (12, 18, 28), (0, 0, 128, 128), border_radius=12)
    if kind == "ECHO":
        big = pygame.transform.smoothscale(draw_echo("down", 0), (128, 128))
        s.blit(big, (0, 8))
    elif kind == "HALCYON":
        pts = [(64 + math.cos(math.radians(60 * k)) * 50, 64 + math.sin(math.radians(60 * k)) * 50) for k in range(6)]
        pygame.draw.polygon(s, (40, 20, 24), pts)
        pygame.draw.polygon(s, (255, 90, 80), pts, 3)
        glow(s, (64, 64), 48, (255, 60, 50), 1)
        pygame.draw.circle(s, (255, 90, 80), (64, 64), 20)
        pygame.draw.circle(s, (255, 230, 220), (64, 64), 8)
    elif kind == "LOG":
        for cx in (40, 88):
            pygame.draw.circle(s, (200, 200, 140), (cx, 58), 20, 4)
            pygame.draw.circle(s, (200, 200, 140), (cx, 58), 5)
        pygame.draw.rect(s, (200, 200, 140), (18, 32, 92, 60), 3, border_radius=6)
        pygame.draw.line(s, (200, 200, 140), (40, 84), (88, 84), 3)
    else:  # crew / generic human silhouette
        col = (170, 220, 170) if kind == "CREW" else (180, 200, 255)
        pygame.draw.circle(s, col, (64, 48), 22)
        pygame.draw.ellipse(s, col, (24, 74, 80, 70))
        for y in range(0, 128, 4):
            pygame.draw.line(s, (12, 18, 28, 140), (0, y), (128, y))
    pygame.draw.rect(s, (90, 110, 140), (0, 0, 128, 128), 3, border_radius=12)
    return down(s)


def radial_light(size=256):
    s = pygame.Surface((size, size))
    s.fill((0, 0, 0))
    c = size / 2
    for y in range(size):
        for x in range(size):
            d = math.hypot(x - c + 0.5, y - c + 0.5) / c
            if d < 1:
                v = int(255 * (1 - d) ** 1.8)
                s.set_at((x, y), (v, v, v))
    return s


def make_title():
    src = os.path.join(ROOT, "assets", "ui", "keyart_source.png")
    out = os.path.join(UI, "title.png")
    if os.path.exists(src):
        img = pygame.image.load(src)
        w, h = img.get_size()
        scale = max(1100 / w, 720 / h)
        img = pygame.transform.smoothscale(img, (int(w * scale), int(h * scale)))
        save(img, UI, "title")
        return
    if os.path.exists(out):
        return
    # fallback procedural title art
    s = pygame.Surface((1100, 720))
    s.fill((4, 6, 12))
    rng = random.Random(3)
    for _ in range(400):
        v = rng.randrange(60, 255)
        s.set_at((rng.randrange(1100), rng.randrange(720)), (v, v, v))
    glow(s, (550, 330), 220, (60, 170, 255), 0.9)
    big = pygame.transform.smoothscale(draw_echo("down", 0), (300, 300))
    s.blit(big, (400, 200))
    save(s, UI, "title")


# --------------------------------------------------------------------------- audio
SR = 22050


def write_wav(name, samples, folder=SND):
    os.makedirs(folder, exist_ok=True)
    path = os.path.join(folder, name + ".wav")
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        frames = bytearray()
        for v in samples:
            v = max(-1.0, min(1.0, v))
            frames += struct.pack("<h", int(v * 32000))
        w.writeframes(bytes(frames))


def env(i, n, a=0.01, r=0.2):
    t = i / SR
    total = n / SR
    if t < a:
        return t / a
    if t > total - r:
        return max(0.0, (total - t) / r)
    return 1.0


def osc(kind, phase):
    if kind == "sine":
        return math.sin(phase)
    if kind == "square":
        return 1.0 if math.sin(phase) >= 0 else -1.0
    if kind == "saw":
        return 2 * ((phase / math.tau) % 1) - 1
    if kind == "tri":
        return 2 * abs(2 * ((phase / math.tau) % 1) - 1) - 1
    return 0.0


def tone(f0, dur, vol=0.5, kind="sine", f1=None, a=0.005, r=0.1):
    n = int(SR * dur)
    out = []
    ph = 0.0
    for i in range(n):
        f = f0 if f1 is None else f0 + (f1 - f0) * i / n
        ph += math.tau * f / SR
        out.append(osc(kind, ph) * vol * env(i, n, a, r))
    return out


def noise(dur, vol=0.5, lp=0.2, a=0.005, r=0.1, rng=random.Random(1)):
    n = int(SR * dur)
    out = []
    y = 0.0
    for i in range(n):
        y += lp * (rng.uniform(-1, 1) - y)
        out.append(y * vol * env(i, n, a, r) * (1 / max(lp, 0.05)) ** 0.5)
    return out


def add(a, b, offset=0):
    n = max(len(a), len(b) + offset)
    out = a + [0.0] * (n - len(a))
    for i, v in enumerate(b):
        out[i + offset] += v
    return out


def echo_fx(s, delay=0.18, fb=0.35, taps=3):
    out = list(s) + [0.0] * int(SR * delay * taps)
    d = int(SR * delay)
    for t in range(1, taps + 1):
        g = fb ** t
        for i, v in enumerate(s):
            out[i + d * t] += v * g
    return out


def gen_sounds():
    write_wav("step", noise(0.05, 0.25, 0.5, r=0.04))
    write_wav("door", add(noise(0.45, 0.35, 0.08, a=0.05, r=0.2), tone(160, 0.45, 0.15, "saw", 90, r=0.2)))
    write_wav("door_locked", add(tone(140, 0.12, 0.3, "square"), tone(110, 0.16, 0.3, "square"), int(SR * 0.13)))
    p = []
    for k, f in enumerate((660, 880, 1320)):
        p = add(p, tone(f, 0.12, 0.25, "tri", r=0.08), int(SR * 0.06 * k))
    write_wav("pickup", p)
    write_wav("beep", tone(1200, 0.07, 0.2, "square", r=0.03))
    write_wav("type", tone(1800, 0.018, 0.08, "square", r=0.01))
    al = []
    for k in range(2):
        al = add(al, tone(700, 0.25, 0.25, "saw", 1000), int(SR * 0.25 * k))
    write_wav("alarm", al)
    write_wav("zap", add(noise(0.3, 0.5, 0.9, r=0.2), tone(90, 0.3, 0.3, "square", 40)))
    write_wav("rotate", add(tone(500, 0.04, 0.2, "square", r=0.02), noise(0.04, 0.2, 0.6)))
    sv = []
    for k, f in enumerate((523, 659, 784, 1046)):
        sv = add(sv, tone(f, 0.5 - k * 0.05, 0.18, "sine", r=0.3), int(SR * 0.07 * k))
    write_wav("solve", echo_fx(sv, 0.12, 0.3, 2))
    write_wav("scan", echo_fx(tone(300, 0.5, 0.25, "sine", 1600, r=0.3), 0.1, 0.3, 2))
    write_wav("low", add(tone(880, 0.1, 0.2, "sine"), tone(660, 0.12, 0.2, "sine"), int(SR * 0.12)))
    write_wav("error", tone(90, 0.25, 0.35, "square", r=0.1))
    write_wav("select", tone(900, 0.05, 0.15, "tri", 1200, r=0.03))
    write_wav("confirm", add(tone(700, 0.08, 0.18, "tri"), tone(1050, 0.12, 0.18, "tri"), int(SR * 0.07)))
    write_wav("detect", add(tone(600, 0.1, 0.25, "square", 900), tone(900, 0.15, 0.25, "square", 1300), int(SR * 0.1)))
    write_wav("charge", tone(200, 0.6, 0.15, "sine", 800, a=0.1, r=0.2))
    write_wav("boom", add(noise(1.4, 0.7, 0.05, a=0.01, r=1.2), tone(55, 1.2, 0.4, "sine", 30, r=1.0)))
    write_wav("heartbeat", add(tone(60, 0.12, 0.6, "sine", 40), tone(55, 0.14, 0.5, "sine", 35), int(SR * 0.22)))
    write_wav("transmit", echo_fx(add(tone(220, 1.5, 0.2, "sine", 880, a=0.3, r=0.6),
                                      tone(330, 1.5, 0.12, "tri", 1320, a=0.3, r=0.6)), 0.2, 0.4, 3))


def gen_music():
    rng = random.Random(7)
    # ambient: low drones with slow breathing and distant pings
    dur = 24.0
    n = int(SR * dur)
    out = [0.0] * n
    freqs = [(55.0, 0.16), (55.4, 0.12), (82.41, 0.10), (110.0, 0.05), (164.8, 0.03)]
    phs = [0.0] * len(freqs)
    for i in range(n):
        t = i / SR
        lfo = 0.6 + 0.4 * math.sin(math.tau * t / dur * 2)
        v = 0.0
        for k, (f, a) in enumerate(freqs):
            phs[k] += math.tau * f / SR
            v += math.sin(phs[k]) * a
        out[i] = v * lfo
    for start in (2.0, 7.5, 13.0, 18.5):
        f = rng.choice([659.3, 587.3, 783.99, 880.0])
        ping = echo_fx(tone(f, 1.6, 0.06, "sine", a=0.01, r=1.5), 0.35, 0.45, 4)
        o = int(start * SR)
        for j, v in enumerate(ping):
            out[(o + j) % n] += v
    # fade loop edges very slightly to avoid clicks
    write_wav("ambient", out, MUS)

    # tension: pulsing bass at 120 bpm with hats
    dur = 16.0
    n = int(SR * dur)
    out = [0.0] * n
    beat = SR // 2
    notes = [55.0, 55.0, 65.41, 49.0]
    for b in range(int(dur * 2)):
        f = notes[(b // 4) % 4]
        s = tone(f, 0.45, 0.32, "saw", a=0.005, r=0.35)
        s2 = tone(f * 2, 0.2, 0.08, "square", r=0.15)
        for j, v in enumerate(s):
            if b * beat + j < n:
                out[b * beat + j] += v
        for j, v in enumerate(s2):
            if b * beat + j < n:
                out[b * beat + j] += v
        h = noise(0.05, 0.08, 0.9, r=0.04)
        off = b * beat + beat // 2
        for j, v in enumerate(h):
            if off + j < n:
                out[off + j] += v
    ph = 0.0
    for i in range(n):
        ph += math.tau * 220 / SR
        out[i] += math.sin(ph) * 0.03 * (0.5 + 0.5 * math.sin(math.tau * i / SR / 4))
    write_wav("tension", out, MUS)

    # menu: ambient pad + slow arpeggio bells
    dur = 20.0
    n = int(SR * dur)
    out = [0.0] * n
    phs = [0.0, 0.0, 0.0]
    for i in range(n):
        t = i / SR
        lfo = 0.7 + 0.3 * math.sin(math.tau * t / 10)
        v = 0.0
        for k, f in enumerate((73.42, 110.0, 146.83)):
            phs[k] += math.tau * f / SR
            v += math.sin(phs[k]) * (0.12 / (k + 1))
        out[i] = v * lfo
    arp = [293.66, 440.0, 587.33, 659.25, 587.33, 440.0, 349.23, 523.25]
    for k in range(20):
        f = arp[k % len(arp)]
        bell = add(tone(f, 1.0, 0.07, "sine", r=0.9), tone(f * 2.01, 0.6, 0.02, "sine", r=0.5))
        o = int(k * SR * 1.0)
        for j, v in enumerate(echo_fx(bell, 0.3, 0.35, 2)):
            out[(o + j) % n] += v
    write_wav("menu", out, MUS)


# --------------------------------------------------------------------------- main
def gen_images():
    rng = random.Random(42)
    for d in ("down", "up", "left", "right"):
        for f in range(4):
            save(draw_echo(d, f), SPR, f"echo_{d}_{f}")
    for mode in ("normal", "alert", "off", "sus"):
        for f in range(2):
            save(draw_drone(f, mode), SPR, f"drone_{mode}_{f}")

    for theme, p in PALETTES.items():
        folder = os.path.join(TIL, theme)
        trng = random.Random(hash(theme) & 0xffff)
        for v in range(4):
            save(tile_floor(p, v, trng), folder, f"floor_{v}")
        save(tile_grate(p, trng), folder, "grate")
        save(tile_line(p, trng), folder, "line")
        save(tile_hazard(p, trng), folder, "hazard")
        save(tile_wall_top(p, trng), folder, "wall_top")
        for v in range(3):
            save(tile_wall_front(p, trng), folder, f"wall_front_{v}")
        save(tile_wall_front(p, trng, window=True), folder, "window")
        save(obj_door_panel(p), folder, "door_panel")
        for f in range(4):
            save(tile_water(p, f), folder, f"water_{f}")
        save(tile_soil(p, trng), folder, "soil")
        save(tile_bed(p, trng), folder, "bed")
    for v in range(4):
        save(tile_space(rng), TIL, f"space_{v}")

    save(obj_terminal(False), SPR, "terminal_off")
    save(obj_terminal(True), SPR, "terminal_on")
    save(obj_broken_terminal(), SPR, "terminal_broken")
    save(obj_panel(False), SPR, "panel_off")
    save(obj_panel(True), SPR, "panel_on")
    save(obj_switch(False), SPR, "switch_off")
    save(obj_switch(True), SPR, "switch_on")
    save(obj_dock(), SPR, "dock")
    save(obj_lamp(True), SPR, "lamp_on")
    save(obj_lamp(False), SPR, "lamp_off")
    save(obj_crate(rng), SPR, "crate")
    save(obj_barrel(), SPR, "barrel")
    for k in range(3):
        save(obj_plant(random.Random(10 + k)), SPR, f"plant_{k}")
    save(obj_vines(rng), SPR, "vines")
    for f in range(8):
        save(obj_reactor(f), SPR, f"reactor_{f}")
        save(obj_ai_core(f), SPR, f"aicore_{f}")
    save(obj_console(False), SPR, "console_off")
    save(obj_console(True), SPR, "console_on")
    for f in range(2):
        save(obj_transmitter(f), SPR, f"transmitter_{f}")
    for f in range(8):
        save(obj_holotable(f), SPR, f"holotable_{f}")
    for f in range(4):
        save(obj_exit(f), SPR, f"exit_{f}")
    save(obj_pipe(True), SPR, "pipe_v")
    save(obj_pipe(False), SPR, "pipe_h")
    save(obj_debris(rng), SPR, "debris")
    save(obj_bed_cryo(), SPR, "cryo")

    save(item_battery(), SPR, "item_battery")
    save(item_keycard((70, 150, 255)), SPR, "item_keycard_maint")
    save(item_keycard((255, 90, 90)), SPR, "item_keycard_red")
    save(item_component(), SPR, "item_component")
    save(item_fragment(), SPR, "item_fragment")
    save(item_command_key(), SPR, "item_command_key")

    for k in ("ECHO", "HALCYON", "LOG", "CREW", "HUMAN"):
        save(portrait(k), UI, f"portrait_{k.lower()}")
    save(radial_light(256), UI, "light_radial")
    make_title()


def generate_all(verbose=True):
    if not pygame.get_init():
        pygame.init()
    if verbose:
        print("[assets] drawing sprites and tiles...")
    gen_images()
    if verbose:
        print("[assets] synthesizing sound effects...")
    gen_sounds()
    if verbose:
        print("[assets] composing music loops (this takes a few seconds)...")
    gen_music()
    if verbose:
        print("[assets] done.")


if __name__ == "__main__":
    pygame.init()
    generate_all()
