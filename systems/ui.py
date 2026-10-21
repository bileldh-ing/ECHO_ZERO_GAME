"""Shared UI drawing helpers: text, wrapping, panels, vignette and scanlines."""
import math

import pygame

from settings import W, H, CYAN, WHITE, PANEL_BG
from systems import assets

_cache = {}


def text(surf, msg, pos, size=16, color=WHITE, bold=False, anchor="topleft", shadow=True, alpha=255):
    f = assets.font(size, bold)
    img = f.render(str(msg), True, color)
    r = img.get_rect(**{anchor: pos})
    if shadow:
        sh = f.render(str(msg), True, (0, 0, 0))
        if alpha < 255:
            sh.set_alpha(alpha)
        surf.blit(sh, (r.x + 1, r.y + 2))
    if alpha < 255:
        img.set_alpha(alpha)
    surf.blit(img, r)
    return r


def wrap(msg, size, width, bold=False):
    f = assets.font(size, bold)
    words = msg.split(" ")
    lines, cur = [], ""
    for w in words:
        t = (cur + " " + w).strip()
        if f.size(t)[0] <= width:
            cur = t
        else:
            if cur:
                lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def panel(surf, rect, alpha=215, border=CYAN, radius=8, glow=True):
    r = pygame.Rect(rect)
    key = ("panel", r.size, alpha, tuple(border), radius)
    cached = _cache.get(key)
    if cached is not None:
        surf.blit(cached, r)
        return
    s = pygame.Surface(r.size, pygame.SRCALPHA)
    pygame.draw.rect(s, (*PANEL_BG, alpha), s.get_rect(), border_radius=radius)
    for y in range(0, r.h, 3):
        pygame.draw.line(s, (255, 255, 255, 6), (0, y), (r.w, y))
    pygame.draw.rect(s, (*border, 200), s.get_rect(), 2, border_radius=radius)
    # corner brackets
    L = 14
    for (cx, cy, dx, dy) in ((0, 0, 1, 1), (r.w - 1, 0, -1, 1), (0, r.h - 1, 1, -1), (r.w - 1, r.h - 1, -1, -1)):
        pygame.draw.line(s, (*border, 255), (cx, cy), (cx + dx * L, cy), 3)
        pygame.draw.line(s, (*border, 255), (cx, cy), (cx, cy + dy * L), 3)
    if len(_cache) > 300:
        for k in [k for k in _cache if isinstance(k, tuple) and k[0] == "panel"][:100]:
            _cache.pop(k, None)
    _cache[key] = s
    surf.blit(s, r)


def bar(surf, rect, frac, color, back=(20, 26, 36), segments=0):
    r = pygame.Rect(rect)
    pygame.draw.rect(surf, back, r, border_radius=3)
    fr = r.inflate(-4, -4)
    fr.w = int(fr.w * max(0.0, min(1.0, frac)))
    if fr.w > 0:
        pygame.draw.rect(surf, color, fr, border_radius=2)
        hi = fr.copy()
        hi.h = max(1, fr.h // 3)
        pygame.draw.rect(surf, tuple(min(255, c + 60) for c in color), hi, border_radius=2)
    if segments:
        for i in range(1, segments):
            x = r.x + r.w * i // segments
            pygame.draw.line(surf, back, (x, r.y + 2), (x, r.bottom - 3), 2)
    pygame.draw.rect(surf, (120, 140, 160), r, 1, border_radius=3)


def vignette():
    if "vig" not in _cache:
        cx, cy = W / 2, H / 2
        out = pygame.Surface((W, H), pygame.SRCALPHA)
        out.fill((0, 0, 0, 175))
        hole = pygame.Surface((W, H), pygame.SRCALPHA)
        n = 36
        for i in range(n):
            t = 1 - i / n
            a = int(175 * min(1.0, (i / (n - 1)) ** 0.7))
            rw, rh = int(W * (0.5 + 0.85 * t)), int(H * (0.5 + 0.85 * t))
            pygame.draw.ellipse(hole, (0, 0, 0, a), (cx - rw / 2, cy - rh / 2, rw, rh))
        out.blit(hole, (0, 0), special_flags=pygame.BLEND_RGBA_SUB)
        _cache["vig"] = out
    return _cache["vig"]


def scanlines():
    if "scan" not in _cache:
        s = pygame.Surface((W, H), pygame.SRCALPHA)
        for y in range(0, H, 3):
            pygame.draw.line(s, (0, 0, 0, 28), (0, y), (W, y))
        _cache["scan"] = s
    return _cache["scan"]


def post_fx(scan=True):
    """Vignette (and optional scanlines) merged into one overlay."""
    key = ("post", bool(scan))
    if key not in _cache:
        s = vignette().copy()
        if scan:
            s.blit(scanlines(), (0, 0))
        _cache[key] = s.convert_alpha() if pygame.display.get_surface() else s
    return _cache[key]


def icon(name, size=28):
    return assets.scaled(name, (size, size))
