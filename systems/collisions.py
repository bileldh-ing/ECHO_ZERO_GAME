"""Tile map collision, line of sight raycasting and grid pathfinding."""
import math
from collections import deque

import pygame

from settings import TILE

SOLID_TILES = set("#W ~\"")
OPAQUE_TILES = set("#W ")


class TileMap:
    def __init__(self, rows):
        self.rows = rows
        self.h = len(rows)
        self.w = max(len(r) for r in rows)
        self.rows = [r.ljust(self.w) for r in rows]
        self.blockers = {}      # (x, y) -> owner, solid entity tiles (doors, furniture)
        self.opaque = set()     # tiles blocking light / sight besides walls

    def ch(self, x, y):
        if 0 <= x < self.w and 0 <= y < self.h:
            return self.rows[y][x]
        return " "

    def solid(self, x, y):
        return self.ch(x, y) in SOLID_TILES or (x, y) in self.blockers

    def is_opaque(self, x, y):
        return self.ch(x, y) in OPAQUE_TILES or (x, y) in self.opaque

    def block(self, x, y, owner, opaque=False):
        self.blockers[(x, y)] = owner
        if opaque:
            self.opaque.add((x, y))

    def unblock(self, x, y):
        self.blockers.pop((x, y), None)
        self.opaque.discard((x, y))

    # ------------------------------------------------------------------ movement
    def solid_rects_near(self, rect):
        x0 = rect.left // TILE - 1
        x1 = rect.right // TILE + 1
        y0 = rect.top // TILE - 1
        y1 = rect.bottom // TILE + 1
        out = []
        for ty in range(y0, y1 + 1):
            for tx in range(x0, x1 + 1):
                if self.solid(tx, ty):
                    out.append(pygame.Rect(tx * TILE, ty * TILE, TILE, TILE))
        return out

    def move(self, fx, fy, w, h, dx, dy):
        """Move a float-positioned box (centre fx,fy) and resolve against solids per axis.
        Returns new (fx, fy, hit_x, hit_y)."""
        hit_x = hit_y = False
        # X axis
        fx += dx
        r = pygame.Rect(0, 0, w, h)
        r.center = (round(fx), round(fy))
        for s in self.solid_rects_near(r):
            if r.colliderect(s):
                if dx > 0:
                    r.right = s.left
                elif dx < 0:
                    r.left = s.right
                fx = r.centerx
                hit_x = True
        # Y axis
        fy += dy
        r.center = (round(fx), round(fy))
        for s in self.solid_rects_near(r):
            if r.colliderect(s):
                if dy > 0:
                    r.bottom = s.top
                elif dy < 0:
                    r.top = s.bottom
                fy = r.centery
                hit_y = True
        return fx, fy, hit_x, hit_y

    # ------------------------------------------------------------------ sight
    def raycast(self, x, y, angle, max_dist):
        """DDA raycast in pixel space. Returns distance to the first opaque tile."""
        dx, dy = math.cos(angle), math.sin(angle)
        tx, ty = int(x // TILE), int(y // TILE)
        step_x = 1 if dx > 0 else -1
        step_y = 1 if dy > 0 else -1
        inv_dx = abs(1 / dx) if dx else 1e9
        inv_dy = abs(1 / dy) if dy else 1e9
        if dx > 0:
            side_x = ((tx + 1) * TILE - x) * inv_dx
        else:
            side_x = (x - tx * TILE) * inv_dx
        if dy > 0:
            side_y = ((ty + 1) * TILE - y) * inv_dy
        else:
            side_y = (y - ty * TILE) * inv_dy
        dist = 0.0
        while dist < max_dist:
            if side_x < side_y:
                dist = side_x
                side_x += TILE * inv_dx
                tx += step_x
            else:
                dist = side_y
                side_y += TILE * inv_dy
                ty += step_y
            if self.is_opaque(tx, ty):
                return min(dist, max_dist)
        return max_dist

    def line_of_sight(self, x0, y0, x1, y1):
        d = math.hypot(x1 - x0, y1 - y0)
        if d < 1:
            return True
        a = math.atan2(y1 - y0, x1 - x0)
        return self.raycast(x0, y0, a, d) >= d - 2

    def visibility_polygon(self, x, y, facing, half_angle, length, rays):
        pts = [(x, y)]
        for i in range(rays + 1):
            a = facing - half_angle + 2 * half_angle * i / rays
            d = self.raycast(x, y, a, length)
            pts.append((x + math.cos(a) * d, y + math.sin(a) * d))
        return pts

    # ------------------------------------------------------------------ pathfinding
    def bfs(self, start, goal, limit=1400):
        if start == goal:
            return [goal]
        if self.solid(*goal):
            return None
        prev = {start: None}
        q = deque([start])
        n = 0
        while q and n < limit:
            cur = q.popleft()
            n += 1
            if cur == goal:
                break
            cx, cy = cur
            for nx, ny in ((cx + 1, cy), (cx - 1, cy), (cx, cy + 1), (cx, cy - 1)):
                if (nx, ny) not in prev and not self.solid(nx, ny):
                    prev[(nx, ny)] = cur
                    q.append((nx, ny))
        if goal not in prev:
            return None
        path = []
        cur = goal
        while cur is not None:
            path.append(cur)
            cur = prev[cur]
        path.reverse()
        return path[1:]
