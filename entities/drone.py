"""Security drones: patrol paths, see with a light cone, hear sprinting, chase and shock."""
import math
import random

from settings import (TILE, DRONE_PATROL_SPEED, DRONE_CHASE_SPEED, DRONE_VIEW, DRONE_VIEW_LIT,
                      DRONE_FOV, DRONE_ZAP)
from systems import assets
from entities.player import angle_lerp


def tc(t):
    return (t[0] + 0.5) * TILE, (t[1] + 0.5) * TILE


class Drone:
    def __init__(self, d):
        self.d = d
        self.id = d["id"]
        self.path = [tc(p) for p in d["path"]]
        self.pingpong = d.get("pingpong", False)
        self.idx = 1 % len(self.path)
        self.step = 1
        self.x, self.y = self.path[0]
        self.angle = 0.0
        if len(self.path) > 1:
            self.angle = math.atan2(self.path[1][1] - self.y, self.path[1][0] - self.x)
        self.state = "patrol"
        self.meter = 0.0
        self.timer = 0.0
        self.route = []
        self.repath = 0.0
        self.target = None
        self.lost = 0.0
        self.stun = 0.0
        self.bob = random.uniform(0, 6)
        self.anim = 0.0
        self.poly = []
        self.disabled = False
        self.off_flag = d.get("requires_off")
        self.alarm_cd = 0.0

    # ------------------------------------------------------------------ helpers
    def view_range(self, player):
        return DRONE_VIEW_LIT if player.flashlight else DRONE_VIEW

    def sees(self, player, tilemap):
        dx, dy = player.x - self.x, player.y - self.y
        dist = math.hypot(dx, dy)
        if dist < 30:
            return True
        rng = self.view_range(player)
        if self.state == "alert":
            rng *= 1.3
        if dist > rng:
            return False
        a = math.atan2(dy, dx)
        diff = abs((a - self.angle + math.pi) % math.tau - math.pi)
        fov = math.radians(DRONE_FOV * (1.5 if self.state == "alert" else 1.0))
        if diff > fov:
            return False
        return tilemap.line_of_sight(self.x, self.y, player.x, player.y - 6)

    def move_towards(self, tx, ty, speed, dt, turn=6.0):
        dx, dy = tx - self.x, ty - self.y
        d = math.hypot(dx, dy)
        if d < 1:
            return True
        self.angle = angle_lerp(self.angle, math.atan2(dy, dx), min(1.0, dt * turn))
        s = min(d, speed * dt)
        self.x += dx / d * s
        self.y += dy / d * s
        return d <= speed * dt + 0.5

    def follow_route(self, speed, dt):
        if not self.route:
            return True
        tx, ty = tc(self.route[0])
        if self.move_towards(tx, ty, speed, dt):
            self.route.pop(0)
        return not self.route

    def tile(self):
        return int(self.x // TILE), int(self.y // TILE)

    # ------------------------------------------------------------------ update
    def update(self, dt, gp):
        player, tilemap = gp.player, gp.tilemap
        self.anim += dt
        self.disabled = bool(self.off_flag and self.off_flag in gp.state.flags)
        if self.disabled:
            self.state = "patrol"
            self.meter = 0
            self.poly = []
            return
        self.alarm_cd = max(0.0, self.alarm_cd - dt)

        if self.stun > 0:
            self.stun -= dt
            self.angle += dt * 9
            self.poly = []
            if self.stun <= 0:
                self.state = "return"
                self.route = []
            return

        seen = self.sees(player, tilemap) and not player.dead
        dist = math.hypot(player.x - self.x, player.y - self.y)
        heard = player.noise > 0 and dist < player.noise and not player.dead

        rate = 1.25 * (1.6 if player.flashlight else 1.0) * (1.5 if player.sprinting else 1.0)
        if dist < 70:
            rate *= 2.0

        if self.state in ("patrol", "return", "suspicious", "investigate"):
            if seen:
                self.meter += rate * dt
                self.target = (player.x, player.y)
                if self.state != "suspicious":
                    self.state = "suspicious"
                    self.timer = 2.2
                    assets.play("beep", 0.5)
            elif heard and self.state in ("patrol", "return"):
                self.state = "investigate"
                self.target = (player.x, player.y)
                self.route = tilemap.bfs(self.tile(), (int(player.x // TILE), int(player.y // TILE))) or []
                self.timer = 4.0
                self.meter = max(self.meter, 0.25)
            else:
                self.meter = max(0.0, self.meter - 0.35 * dt)
            if self.meter >= 1.0:
                self.state = "alert"
                self.lost = 0.0
                self.repath = 0.0
                assets.play("detect", 0.8)
                gp.on_alert(self)

        if self.state == "patrol":
            tx, ty = self.path[self.idx]
            if self.move_towards(tx, ty, DRONE_PATROL_SPEED, dt):
                if self.pingpong:
                    if self.idx + self.step >= len(self.path) or self.idx + self.step < 0:
                        self.step *= -1
                    self.idx += self.step
                else:
                    self.idx = (self.idx + 1) % len(self.path)

        elif self.state == "suspicious":
            if self.target:
                a = math.atan2(self.target[1] - self.y, self.target[0] - self.x)
                self.angle = angle_lerp(self.angle, a, min(1.0, dt * 5))
            if not seen:
                self.timer -= dt
                if self.timer <= 0:
                    self.state = "return"
                    self.route = []

        elif self.state == "investigate":
            done = self.follow_route(DRONE_PATROL_SPEED * 1.3, dt)
            self.timer -= dt
            if done:
                self.angle += dt * 2.5
            if self.timer <= 0:
                self.state = "return"
                self.route = []

        elif self.state == "alert":
            if seen:
                self.lost = 0.0
            else:
                self.lost += dt
            self.repath -= dt
            if self.repath <= 0:
                self.repath = 0.35
                ptile = (int(player.x // TILE), int(player.y // TILE))
                self.route = tilemap.bfs(self.tile(), ptile) or []
                if self.alarm_cd <= 0:
                    assets.play("alarm", 0.35)
                    self.alarm_cd = 1.6
            if seen and dist < 90:
                self.move_towards(player.x, player.y, DRONE_CHASE_SPEED, dt, turn=10)
            else:
                self.follow_route(DRONE_CHASE_SPEED, dt)
            if dist < 24 and not player.dead:
                gp.on_zap(self)
                self.stun = 1.6
                self.meter = 0.4
            if self.lost > 3.2:
                self.state = "return"
                self.route = []
                self.meter = 0.5

        elif self.state == "return":
            if not self.route:
                # nearest waypoint
                best = min(range(len(self.path)), key=lambda i: math.dist(self.path[i], (self.x, self.y)))
                self.idx = best
                wt = (int(self.path[best][0] // TILE), int(self.path[best][1] // TILE))
                self.route = tilemap.bfs(self.tile(), wt) or []
                if not self.route:
                    self.state = "patrol"
            if self.route and self.follow_route(DRONE_PATROL_SPEED * 1.2, dt):
                self.state = "patrol"

        # vision polygon (used for light + overlay)
        rng = self.view_range(player) * (1.3 if self.state == "alert" else 1.0)
        fov = math.radians(DRONE_FOV * (1.5 if self.state == "alert" else 1.0))
        self.poly = tilemap.visibility_polygon(self.x, self.y, self.angle, fov, rng, 16)

    # ------------------------------------------------------------------ drawing
    @property
    def mode(self):
        if self.disabled or self.stun > 0:
            return "off"
        if self.state == "alert":
            return "alert"
        if self.state in ("suspicious", "investigate"):
            return "sus"
        return "normal"

    @property
    def color(self):
        return {"alert": (255, 60, 50), "sus": (255, 190, 70), "off": (60, 60, 60), "normal": (255, 90, 70)}[self.mode]

    def draw(self, surf, cam_x, cam_y, rot_cache):
        frame = int(self.anim * 18) % 2
        hover = 0 if self.disabled else math.sin(self.anim * 3 + self.bob) * 3
        key = (self.mode, frame, int(math.degrees(self.angle) // 6) % 60)
        img = rot_cache.get(key)
        if img is None:
            import pygame
            base = assets.image(f"drone_{self.mode}_{frame}")
            img = pygame.transform.rotate(base, -key[2] * 6)
            rot_cache[key] = img
        sx = self.x - cam_x - img.get_width() / 2
        sy = self.y - cam_y - img.get_height() / 2 - 10 + hover + (8 if self.disabled else 0)
        surf.blit(img, (sx, sy))

    @property
    def sort_y(self):
        return self.y + 10
