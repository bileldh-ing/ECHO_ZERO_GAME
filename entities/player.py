"""ECHO, the maintenance robot the player controls."""
import math

import pygame

from settings import TILE, WALK_SPEED, SPRINT_SPEED, ACCEL, FRICTION
from systems import assets


def angle_lerp(a, b, t):
    d = (b - a + math.pi) % math.tau - math.pi
    return a + d * t


class Player:
    HB_W, HB_H = 18, 14

    def __init__(self, x, y):
        self.x, self.y = float(x), float(y)
        self.vx = self.vy = 0.0
        self.facing = math.pi / 2
        self.dir = "down"
        self.anim = 0.0
        self.frame = 0
        self.flashlight = True
        self.sprinting = False
        self.moving = False
        self.noise = 0.0
        self.step_timer = 0.0
        self.kb = [0.0, 0.0]
        self.hurt = 0.0
        self.dead = False
        self.sprites = {d: [assets.image(f"echo_{d}_{i}") for i in range(4)] for d in ("down", "up", "left", "right")}

    @property
    def rect(self):
        r = pygame.Rect(0, 0, self.HB_W, self.HB_H)
        r.center = (round(self.x), round(self.y))
        return r

    @property
    def eye(self):
        return self.x, self.y - 14

    def knockback(self, vx, vy):
        self.kb = [vx, vy]
        self.hurt = 0.6

    def update(self, dt, keys, tilemap, can_sprint):
        ix = (keys[pygame.K_d] or keys[pygame.K_RIGHT]) - (keys[pygame.K_a] or keys[pygame.K_LEFT])
        iy = (keys[pygame.K_s] or keys[pygame.K_DOWN]) - (keys[pygame.K_w] or keys[pygame.K_UP])
        if self.dead:
            ix = iy = 0
        mag = math.hypot(ix, iy)
        want_sprint = keys[pygame.K_LSHIFT] or keys[pygame.K_RSHIFT]
        self.sprinting = bool(want_sprint and mag > 0 and can_sprint)
        speed = SPRINT_SPEED if self.sprinting else WALK_SPEED
        if mag > 0:
            tx, ty = ix / mag * speed, iy / mag * speed
            self.facing = angle_lerp(self.facing, math.atan2(iy, ix), min(1.0, dt * 14))
        else:
            tx = ty = 0.0

        def approach(v, t, rate):
            if v < t:
                return min(t, v + rate)
            return max(t, v - rate)

        rate = (ACCEL if mag > 0 else FRICTION) * dt
        self.vx = approach(self.vx, tx, rate)
        self.vy = approach(self.vy, ty, rate)

        dx = (self.vx + self.kb[0]) * dt
        dy = (self.vy + self.kb[1]) * dt
        self.kb[0] *= max(0, 1 - 6 * dt)
        self.kb[1] *= max(0, 1 - 6 * dt)
        self.x, self.y, hx, hy = tilemap.move(self.x, self.y, self.HB_W, self.HB_H, dx, dy)
        if hx:
            self.vx = 0
        if hy:
            self.vy = 0
        self.hurt = max(0.0, self.hurt - dt)

        spd = math.hypot(self.vx, self.vy)
        self.moving = spd > 15
        if self.moving:
            self.anim += dt * (spd / 22)
            self.frame = int(self.anim) % 4
        else:
            self.frame = 0
        self.noise = 175 if (self.sprinting and self.moving) else (55 if self.moving else 0)

        a = math.degrees(self.facing) % 360
        if 45 <= a < 135:
            self.dir = "down"
        elif 135 <= a < 225:
            self.dir = "left"
        elif 225 <= a < 315:
            self.dir = "up"
        else:
            self.dir = "right"

        stepped = False
        if self.moving:
            self.step_timer -= dt
            if self.step_timer <= 0:
                self.step_timer = 0.22 if self.sprinting else 0.34
                assets.play("step", 0.35 if self.sprinting else 0.2)
                stepped = True
        return stepped

    def draw(self, surf, cam_x, cam_y):
        img = self.sprites[self.dir][self.frame]
        if self.hurt > 0 and int(self.hurt * 20) % 2 == 0:
            img = img.copy()
            img.fill((255, 120, 120, 0), special_flags=pygame.BLEND_RGBA_ADD)
        sx = self.x - cam_x - img.get_width() / 2
        sy = self.y - cam_y - img.get_height() + 10
        surf.blit(img, (sx, sy))

    @property
    def sort_y(self):
        return self.y + 6
