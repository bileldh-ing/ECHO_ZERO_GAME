"""Light map: ambient darkness, baked static lights, flashlight cone with wall shadows."""
import math

import pygame

from settings import W, H, TILE
from systems import assets


class Lighting:
    def __init__(self):
        self.lightmap = pygame.Surface((W, H))
        self._cache = {}
        self.static = None
        self.static_offset = (0, 0)

    def light_texture(self, radius, color, intensity=1.0):
        key = (int(radius), tuple(color), round(intensity, 2))
        tex = self._cache.get(key)
        if tex is None:
            base = assets.image("light_radial", "ui")
            tex = pygame.transform.smoothscale(base, (int(radius * 2), int(radius * 2))).convert()
            c = tuple(min(255, int(v * intensity)) for v in color)
            tex.fill(c, special_flags=pygame.BLEND_MULT)
            self._cache[key] = tex
            if len(self._cache) > 200:
                self._cache.pop(next(iter(self._cache)))
        return tex

    def bake(self, world_w, world_h, lights, ambient):
        """Pre-render static lights (lamps etc.) into a world-sized surface."""
        self.static = pygame.Surface((world_w, world_h))
        self.static.fill(ambient)
        for (x, y, r, col, inten) in lights:
            tex = self.light_texture(r, col, inten)
            self.static.blit(tex, (x - r, y - r), special_flags=pygame.BLEND_ADD)

    def begin(self, cam_x, cam_y, ambient):
        if self.static is not None:
            self.lightmap.fill((170, 175, 200))
            self.lightmap.blit(self.static, (-cam_x, -cam_y))
        else:
            self.lightmap.fill(ambient)

    def add(self, sx, sy, radius, color, intensity=1.0):
        tex = self.light_texture(radius, color, intensity)
        self.lightmap.blit(tex, (sx - radius, sy - radius), special_flags=pygame.BLEND_ADD)

    def add_cone(self, tilemap, wx, wy, cam_x, cam_y, facing, length, color, intensity=1.0):
        """Flashlight: radial gradient masked by a stepped, wall-occluded cone polygon."""
        r = int(length)
        tex = self.light_texture(r, color, intensity).copy()
        mask = pygame.Surface(tex.get_size())
        mask.fill((0, 0, 0))
        for half, shade in ((math.radians(40), 70), (math.radians(31), 150), (math.radians(22), 255)):
            poly = tilemap.visibility_polygon(wx, wy, facing, half, length, 22)
            pts = [(px - wx + r, py - wy + r) for (px, py) in poly]
            if len(pts) >= 3:
                pygame.draw.polygon(mask, (shade, shade, shade), pts)
        tex.blit(mask, (0, 0), special_flags=pygame.BLEND_MULT)
        self.lightmap.blit(tex, (wx - cam_x - r, wy - cam_y - r), special_flags=pygame.BLEND_ADD)

    def add_poly(self, poly, wx, wy, cam_x, cam_y, radius, color, intensity=1.0):
        """Radial light clipped to an arbitrary polygon (used for drone vision cones)."""
        r = int(radius)
        tex = self.light_texture(r, color, intensity).copy()
        mask = pygame.Surface(tex.get_size())
        mask.fill((0, 0, 0))
        pts = [(px - wx + r, py - wy + r) for (px, py) in poly]
        if len(pts) >= 3:
            pygame.draw.polygon(mask, (255, 255, 255), pts)
        tex.blit(mask, (0, 0), special_flags=pygame.BLEND_MULT)
        self.lightmap.blit(tex, (wx - cam_x - r, wy - cam_y - r), special_flags=pygame.BLEND_ADD)

    def apply(self, target):
        target.blit(self.lightmap, (0, 0), special_flags=pygame.BLEND_MULT)
