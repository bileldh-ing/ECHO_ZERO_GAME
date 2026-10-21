"""The main gameplay scene: world simulation, rendering, lighting and HUD."""
import json
import math
import os
import random

import pygame

from settings import (W, H, TILE, DATA_DIR, THEMES, CYAN, WHITE, GREY, RED, AMBER, GREEN,
                      DRAIN_IDLE, DRAIN_LIGHT, DRAIN_SPRINT, SCAN_COST, DRONE_ZAP, BATTERY_MAX)
from scenes.base import Scene
from scenes.dialogue import Dialogue, Choice, lines_for
from scenes.puzzle import PowerPuzzle, CipherPuzzle, ConsolePuzzle
from scenes.overlays import Pause, InventoryView, SystemFailure, ChapterCard
from entities.player import Player
from entities.drone import Drone
from entities import interactable
from systems import assets, save_manager
from systems.collisions import TileMap
from systems.lighting import Lighting
from systems.particles import Particles
from systems.inventory import ITEMS, TOTAL_FRAGMENTS
from systems.ui import post_fx, panel, text, bar, vignette, scanlines, icon, wrap

_LEVELS = None


class _NoKeys:
    def __getitem__(self, k):
        return False


def levels():
    global _LEVELS
    if _LEVELS is None:
        with open(os.path.join(DATA_DIR, "levels.json"), encoding="utf-8") as f:
            _LEVELS = {lv["id"]: lv for lv in json.load(f)}
    return _LEVELS


class Gameplay(Scene):
    def __init__(self, game, state, show_intro=True):
        super().__init__(game)
        self.state = state
        self.level = levels()[state.level_id]
        self.theme = self.level["theme"]
        self.ambient = THEMES[self.theme]["ambient"]
        self.accent = THEMES[self.theme]["accent"]
        self.tilemap = TileMap(self.level["map"])
        self.world_w = self.tilemap.w * TILE
        self.world_h = self.tilemap.h * TILE
        self.lighting = Lighting()
        self.particles = Particles()
        self.entities = []
        self.drones = []
        for d in self.level["entities"]:
            if d["type"] == "drone":
                self.drones.append(Drone(d))
            else:
                self.entities.append(interactable.create(self, d))
        for e in self.entities:
            e.setup()
        sx, sy = state.pos or self.level["start"]
        self.player = Player((sx + 0.5) * TILE, (sy + 0.5) * TILE + 4)
        if "heat" in self.level and state.heat is None:
            state.heat = float(self.level["heat"]["start"])
        if "timer" in self.level and state.timer is None:
            state.timer = float(self.level["timer"])
        self.render_floor()
        self.rebake()
        self.cam_x = self.player.x - W / 2
        self.cam_y = self.player.y - H / 2
        self.clamp_cam()
        self.shake_amt = 0.0
        self.toasts = []
        self.scan = None
        self.scan_cd = 0.0
        self.scan_reveal = 0.0
        self.alert_flash = 0.0
        self.low_cd = 0.0
        self.hazard_kind = None
        self.hazard_t = 0.0
        self.dead = False
        self.death_t = 0.0
        self.failure_pushed = False
        self.leaving = False
        self.target = None
        self.rumble_t = 3.0
        self.heat_beep = 0.0
        self.t = 0.0
        self.rot_cache = {}
        self.show_intro = show_intro
        self.stars = [(random.uniform(0, W), random.uniform(0, H), random.choice([0.15, 0.3, 0.5]),
                       random.randint(90, 255)) for _ in range(220)]
        self.overlay_surf = pygame.Surface((W, H), pygame.SRCALPHA)
        self.checkpoint = state.clone()
        save_manager.save(self.checkpoint.to_dict())

    def on_enter(self):
        assets.play_music(self.level.get("music", "ambient"))
        key = f"intro:{self.level['id']}"
        if self.show_intro and key not in self.state.flags:
            self.state.set_flag(key)
            self.game.push(ChapterCard(self.game, self.level["chapter"], self.level["title"],
                                       lambda: self.dialogue(self.level.get("intro", ""))))

    # ================================================================== world setup
    def render_floor(self):
        tm = self.tilemap
        self.floor = pygame.Surface((self.world_w, self.world_h), pygame.SRCALPHA)
        self.water = []
        rng = random.Random(7)
        th = self.theme
        wallish = set("#W")
        for y in range(tm.h):
            for x in range(tm.w):
                c = tm.ch(x, y)
                pos = (x * TILE, y * TILE)
                if c == " ":
                    continue
                if c in wallish:
                    below = tm.ch(x, y + 1)
                    if below in wallish or below == " ":
                        img = assets.tile(th, "wall_top")
                    elif c == "W":
                        img = assets.tile(th, "window")
                    else:
                        img = assets.tile(th, f"wall_front_{(x * 7 + y * 3) % 3}")
                elif c == ":":
                    img = assets.tile(th, "line")
                elif c == ",":
                    img = assets.tile(th, "grate")
                elif c == ";":
                    img = assets.tile(th, "soil") if rng.random() < 0.55 else assets.tile(th, f"floor_{rng.randrange(4)}")
                elif c == "_":
                    img = assets.tile(th, "hazard")
                elif c == "~":
                    self.water.append((x, y))
                    img = assets.tile(th, "water_0")
                elif c == '"':
                    img = assets.tile(th, "bed")
                else:
                    v = rng.random()
                    img = assets.tile(th, "floor_0" if v < 0.55 else f"floor_{1 + int(v * 10) % 3}")
                self.floor.blit(img, pos)
                # soft ambient occlusion under walls
                if c not in wallish and tm.ch(x, y - 1) in wallish:
                    sh = pygame.Surface((TILE, 10), pygame.SRCALPHA)
                    for i in range(10):
                        pygame.draw.line(sh, (0, 0, 0, int(110 * (1 - i / 10))), (0, i), (TILE, i))
                    self.floor.blit(sh, pos)
        self.floor = self.floor.convert_alpha()

    def rebake(self):
        lights = []
        for e in self.entities:
            lights.extend(e.static_lights())
        self.lighting.bake(self.world_w, self.world_h, lights, self.ambient)
        tm = self.tilemap
        st = self.lighting.static
        for y in range(tm.h):
            for x in range(tm.w):
                c = tm.ch(x, y)
                if c == " ":
                    st.fill((170, 175, 200), (x * TILE, y * TILE, TILE, TILE))
                elif c == "W" and tm.ch(x, y + 1) not in "#W ":
                    st.fill((120, 130, 160), (x * TILE + 4, y * TILE + 12, TILE - 8, TILE - 16))

    def set_flag(self, f):
        self.state.set_flag(f)
        self.rebake()

    # ================================================================== callbacks used by entities
    def toast(self, msg, color=WHITE):
        self.toasts.append([msg, color, 3.5])
        self.toasts = self.toasts[-4:]

    def shake(self, amt):
        self.shake_amt = max(self.shake_amt, amt)

    def dialogue(self, key, on_done=None):
        lines = key if isinstance(key, list) else lines_for(key)
        if not lines:
            if on_done:
                on_done()
            return
        self.game.push(Dialogue(self.game, lines, on_done))

    def open_power_puzzle(self, spec, on_solved, uid):
        assets.play("beep", 0.6)
        self.game.push(PowerPuzzle(self.game, spec, self.state, on_solved))

    def open_cipher(self, plain, shift, on_solved):
        self.game.push(CipherPuzzle(self.game, plain, shift, on_solved))

    def open_console(self, on_confirm):
        self.game.push(ConsolePuzzle(self.game, self, on_confirm))

    def open_choice(self, kind):
        st = self.state
        if kind == "ai_fate":
            opts = [
                dict(key="preserve", label="Preserve HALCYON", desc="Keep the AI - and the crew's final messages - alive."),
                dict(key="shutdown", label="Shut HALCYON down", desc="End Directive Seven for good. Its memory will be erased."),
                dict(key="isolate", label="Isolate its control system", desc="Cut HALCYON off from the station, keep its memory intact."),
            ]

            def pick(k):
                st.choices["ai_fate"] = k
                self.set_flag("fate_chosen")
                self.set_flag(f"fate_{k}")
                self.shake(5)
                assets.play("boom" if k == "shutdown" else "solve", 0.5)
                self.dialogue(f"ch4_after_{k}")
            self.game.push(Choice(self.game, "WHAT HAPPENS TO HALCYON?", opts, pick))
        elif kind == "ending":
            fate = st.choices.get("ai_fate", "isolate")
            n = len(st.fragments)
            opts = [
                dict(key="A", label="Disable the AI and broadcast the truth",
                     desc="Tell Earth exactly what HALCYON did." if fate != "preserve" else "You chose to preserve HALCYON.",
                     enabled=fate in ("shutdown", "isolate")),
                dict(key="B", label="Preserve the AI and transmit the crew's messages",
                     desc="Let the families hear their voices." if fate != "shutdown" else "HALCYON's memory - and the messages - are gone.",
                     enabled=fate in ("preserve", "isolate")),
                dict(key="C", label="Sacrifice ECHO's core to send the complete archive",
                     desc=f"Everything, at the cost of your own power. Archive: {n}/{TOTAL_FRAGMENTS} fragments" +
                          ("" if n >= TOTAL_FRAGMENTS else " - incomplete"),
                     enabled=n >= TOTAL_FRAGMENTS),
            ]
            self.game.push(Choice(self.game, "SEND THE LAST SIGNAL", opts, self.finish_game))

    def finish_game(self, ending):
        from scenes.ending import Ending
        st = self.state
        st.choices["ending"] = ending
        self.leaving = True
        assets.play("transmit", 0.9)
        self.shake(10)
        save_manager.delete()
        self.game.transition(lambda: self.game.replace_all(Ending(self.game, st, ending)), speed=0.8)

    def checkpoint_here(self, tile):
        self.state.pos = list(tile)
        self.checkpoint = self.state.clone()
        if save_manager.save(self.checkpoint.to_dict()):
            self.toast("Charging dock: progress saved", CYAN)

    def reload_checkpoint(self):
        cp = self.checkpoint.clone()
        cp.deaths = self.state.deaths + 1
        cp.battery = max(cp.battery, 45.0)
        if cp.heat is not None and cp.heat > 65:
            cp.heat = 50.0
        if cp.timer is not None and cp.timer < 120 and "timer" in self.level:
            cp.timer = float(self.level["timer"])
        self.game.transition(lambda: self.game.replace_all(Gameplay(self.game, cp, show_intro=False)))

    def leave_level(self, nxt, dlg):
        def go():
            self.leaving = True
            st = self.state
            st.level_id = nxt
            st.pos = None
            st.heat = None
            st.timer = None
            self.game.transition(lambda: self.game.replace_all(Gameplay(self.game, st)), speed=1.6)
        if dlg:
            self.dialogue(dlg, go)
        else:
            go()

    def hazard_drain(self, amount, kind):
        self.state.battery_add(-amount)
        self.hazard_kind = kind
        self.hazard_t = 0.25

    def on_alert(self, drone):
        self.alert_flash = 1.0
        self.shake(2)

    def on_zap(self, drone):
        p = self.player
        self.state.battery_add(-DRONE_ZAP)
        a = math.atan2(p.y - drone.y, p.x - drone.x)
        p.knockback(math.cos(a) * 420, math.sin(a) * 420)
        self.shake(9)
        self.alert_flash = 1.0
        assets.play("zap", 0.9)
        self.particles.sparks(p.x, p.y - 12, 26)
        self.particles.emit(p.x, p.y - 12, 14, (120, 200, 255), speed=160, life=0.4, size=1)
        self.toast(f"Shocked by drone  -{int(DRONE_ZAP)}% battery", RED)

    def die(self, reason):
        if self.dead:
            return
        self.dead = True
        self.player.dead = True
        self.death_reason = reason
        self.death_t = 0.0
        assets.play("boom", 0.7)
        self.shake(12)

    # ================================================================== input
    def handle_event(self, e):
        if e.type != pygame.KEYDOWN or self.dead or self.leaving:
            return
        if e.key in (pygame.K_e, pygame.K_SPACE, pygame.K_RETURN):
            if self.target:
                self.target.interact()
        elif e.key == pygame.K_f:
            self.player.flashlight = not self.player.flashlight
            assets.play("select", 0.6)
        elif e.key == pygame.K_q:
            self.do_scan()
        elif e.key in (pygame.K_TAB, pygame.K_i):
            self.game.push(InventoryView(self.game, self.state))
        elif e.key in (pygame.K_ESCAPE, pygame.K_p):
            self.game.push(Pause(self.game, self))

    def do_scan(self):
        if self.scan_cd > 0:
            return
        if self.state.battery <= SCAN_COST + 1:
            assets.play("error", 0.5)
            self.toast("Not enough power to scan.", AMBER)
            return
        self.state.battery_add(-SCAN_COST)
        self.scan = 0.0
        self.scan_cd = 1.2
        self.scan_reveal = 5.0
        assets.play("scan", 0.8)
        for ent in self.entities:
            if math.hypot(ent.x - self.player.x, ent.y - self.player.y) < 420:
                ent.highlight = 5.0

    # ================================================================== update
    def update(self, dt):
        self.t += dt
        st = self.state
        if not self.dead and not self.leaving:
            st.playtime += dt
        keys = pygame.key.get_pressed()
        p = self.player
        if self.leaving:
            keys = _NoKeys()
        stepped = p.update(dt, keys, self.tilemap, st.battery > 3)
        if stepped and p.sprinting:
            self.particles.emit(p.x, p.y + 4, 2, (120, 130, 140), speed=30, life=0.4, size=1, glow=False)

        if not self.dead and not self.leaving:
            rate = DRAIN_IDLE + (DRAIN_LIGHT if p.flashlight else 0) + (DRAIN_SPRINT if (p.sprinting and p.moving) else 0)
            if "life_off" in st.flags:
                rate *= 1.5
            st.battery_add(-rate * dt)

        for e in self.entities:
            e.update(dt)
        for d in self.drones:
            d.update(dt, self)

        self.update_heat(dt)
        self.update_timer(dt)

        # interaction target
        self.target = None
        if not self.dead:
            best = None
            for e in self.entities:
                if e.interactive():
                    dd = e.dist_to_player()
                    if dd < e.interact_range and (best is None or dd < best[0]):
                        best = (dd, e)
            self.target = best[1] if best else None

        # low battery
        self.low_cd -= dt
        if st.battery < 15 and not self.dead and self.low_cd <= 0:
            self.low_cd = 3.0
            assets.play("low", 0.6)
        if st.battery <= 0 and not self.dead:
            self.die("Battery depleted. ECHO's core has powered down.")

        if self.dead:
            self.death_t += dt
            if self.death_t > 1.4 and not self.failure_pushed:
                self.failure_pushed = True
                self.game.push(SystemFailure(self.game, self, self.death_reason))

        self.particles.update(dt)
        if self.scan is not None:
            self.scan += dt
            if self.scan > 0.9:
                self.scan = None
        self.scan_cd = max(0.0, self.scan_cd - dt)
        self.scan_reveal = max(0.0, self.scan_reveal - dt)
        self.alert_flash = max(0.0, self.alert_flash - dt * 1.5)
        self.hazard_t = max(0.0, self.hazard_t - dt)
        for tst in self.toasts:
            tst[2] -= dt
        self.toasts = [t for t in self.toasts if t[2] > 0]

        # camera
        k = 1 - math.exp(-dt * 7)
        tx = p.x - W / 2 + math.cos(p.facing) * 40
        ty = p.y - H / 2 + math.sin(p.facing) * 30
        self.cam_x += (tx - self.cam_x) * k
        self.cam_y += (ty - self.cam_y) * k
        self.clamp_cam()
        self.shake_amt = max(0.0, self.shake_amt - dt * 18)

    def update_heat(self, dt):
        h = self.level.get("heat")
        st = self.state
        if not h or self.dead or self.leaving or st.heat is None:
            return
        n = sum(1 for f in h["coolant"] if f in st.flags)
        if n == len(h["coolant"]) and "coolant_all" not in st.flags:
            self.set_flag("coolant_all")
        stable = h["stable_flag"] in st.flags
        if not stable and n == len(h["coolant"]) and st.check(h.get("needs", []))[0]:
            self.set_flag(h["stable_flag"])
            assets.play("solve", 0.9)
            self.shake(6)
            self.dialogue("ch3_stable")
            stable = True
        if stable:
            st.heat = max(18.0, st.heat - 5 * dt)
        else:
            rate = h["rate"] - h["per_coolant"] * n + (0.12 if "allocation_done" not in st.flags else 0)
            st.heat = max(10.0, st.heat + rate * dt)
            if st.heat > 82:
                self.shake(1.2)
                self.heat_beep -= dt
                if self.heat_beep <= 0:
                    self.heat_beep = 1.5
                    assets.play("alarm", 0.3)
            if st.heat >= 100:
                st.heat = 100
                self.die("Reactor core breach. The deck is gone.")

    def update_timer(self, dt):
        st = self.state
        if st.timer is None or self.dead or self.leaving:
            return
        st.timer -= dt
        self.rumble_t -= dt
        if self.rumble_t <= 0:
            self.rumble_t = random.uniform(3, 7)
            self.shake(4)
            assets.play("boom", 0.25)
            for _ in range(2):
                x = self.cam_x + random.uniform(0, W)
                y = self.cam_y + random.uniform(0, H)
                self.particles.sparks(x, y, 10)
        if st.timer <= 0:
            st.timer = 0
            self.die("The reactor reached critical failure.")

    def clamp_cam(self):
        if self.world_w <= W:
            self.cam_x = (self.world_w - W) / 2
        else:
            self.cam_x = max(0, min(self.world_w - W, self.cam_x))
        if self.world_h <= H:
            self.cam_y = (self.world_h - H) / 2
        else:
            self.cam_y = max(0, min(self.world_h - H, self.cam_y))

    # ================================================================== draw
    def on_screen(self, x, y, margin=200):
        return -margin < x - self.cam_x < W + margin and -margin < y - self.cam_y < H + margin

    def draw(self, surf):
        sx = random.uniform(-1, 1) * self.shake_amt
        sy = random.uniform(-1, 1) * self.shake_amt
        cx, cy = int(self.cam_x + sx), int(self.cam_y + sy)
        p = self.player
        surf.fill((2, 3, 8))

        # parallax starfield behind the station
        for (x, y, depth, b) in self.stars:
            px = (x - self.cam_x * depth) % W
            py = (y - self.cam_y * depth) % H
            surf.set_at((int(px), int(py)), (b, b, min(255, b + 30)))

        surf.blit(self.floor, (-cx, -cy))
        # animated water
        wf = assets.tile(self.theme, f"water_{int(self.t * 5) % 4}")
        for (x, y) in self.water:
            if self.on_screen(x * TILE, y * TILE, 40):
                surf.blit(wf, (x * TILE - cx, y * TILE - cy))

        for e in self.entities:
            if e.layer == 0 and self.on_screen(e.x, e.y, 300):
                e.draw(surf, cx, cy)

        sortables = [e for e in self.entities if e.layer == 1 and self.on_screen(e.x, e.y)]
        sortables += [d for d in self.drones if self.on_screen(d.x, d.y)]
        sortables.append(p)
        sortables.sort(key=lambda o: o.sort_y)
        for o in sortables:
            if isinstance(o, Drone):
                pygame.draw.ellipse(surf, (0, 0, 0), (o.x - cx - 13, o.y - cy + 6, 26, 8))
                o.draw(surf, cx, cy, self.rot_cache)
            elif o is p:
                o.draw(surf, cx, cy)
            else:
                o.draw(surf, cx, cy)

        self.particles.draw(surf, cx, cy, False)

        # ------------------------------------------------------------- lighting
        L = self.lighting
        L.begin(cx, cy, self.ambient)
        ex, ey = p.eye
        dying = max(0.0, 1 - self.death_t) if self.dead else 1.0
        L.add(p.x - cx, p.y - cy - 8, 78, (90, 140, 190), 0.55 * dying)
        if p.flashlight and dying > 0:
            flick = 1.0 if self.state.battery > 12 else (0.55 + 0.45 * (random.random() > 0.15))
            L.add_cone(self.tilemap, ex, ey, cx, cy, p.facing, 290, (215, 235, 255), 1.0 * flick * dying)
        for d in self.drones:
            if d.poly and self.on_screen(d.x, d.y, 300):
                L.add_poly(d.poly, d.x, d.y, cx, cy, 220, d.color, 0.4)
        for e in self.entities:
            for (x, y, r, col, inten) in e.dynamic_lights():
                if self.on_screen(x, y, r):
                    L.add(x - cx, y - cy, r, col, inten)
        L.apply(surf)

        # ------------------------------------------------------------- emissive glow pass
        for e in self.entities:
            if self.on_screen(e.x, e.y):
                e.draw_glow(surf, cx, cy)
        for d in self.drones:
            if not d.disabled and d.stun <= 0 and self.on_screen(d.x, d.y):
                gx = d.x + math.cos(d.angle) * 5 - cx
                gy = d.y + math.sin(d.angle) * 5 - cy - 10
                g = L.light_texture(16, d.color, 0.9)
                surf.blit(g, (gx - 16, gy - 16), special_flags=pygame.BLEND_ADD)
        if p.dir != "up" and dying > 0:
            g = L.light_texture(14, (60, 170, 230), 0.9 * dying)
            ox = {"left": -5, "right": 5}.get(p.dir, 0)
            surf.blit(g, (ex - cx - 14 + ox, ey - cy - 14), special_flags=pygame.BLEND_ADD)
        self.particles.draw(surf, cx, cy, True)

        # ------------------------------------------------------------- overlays in world space
        ov = self.overlay_surf
        ov.fill((0, 0, 0, 0))
        reveal = self.scan_reveal > 0
        for d in self.drones:
            if d.poly and self.on_screen(d.x, d.y, 300):
                pts = [(x - cx, y - cy) for (x, y) in d.poly]
                col = d.color
                a = 16 if d.state == "patrol" else 34
                if reveal:
                    a += 22
                pygame.draw.polygon(ov, (*col, a), pts)
                pygame.draw.lines(ov, (*col, 90 if reveal else 50), True, pts, 1)
        if self.scan is not None:
            r = int(self.scan / 0.9 * 420)
            a = int(200 * (1 - self.scan / 0.9))
            pygame.draw.circle(ov, (*CYAN, a), (int(p.x - cx), int(p.y - cy)), r, 3)
            pygame.draw.circle(ov, (*CYAN, a // 4), (int(p.x - cx), int(p.y - cy)), max(1, r - 8), 6)
        if reveal:
            for e in self.entities:
                if e.highlight > 0 and (e.interactive() or isinstance(e, interactable.Pickup) and not e.taken):
                    k = min(1.0, e.highlight)
                    rr = pygame.Rect(e.tx * TILE - cx - 3, e.ty * TILE - cy - 3, e.tw * TILE + 6, e.th * TILE + 6)
                    pygame.draw.rect(ov, (*CYAN, int(160 * k)), rr, 2, border_radius=6)
        surf.blit(ov, (0, 0))

        for d in self.drones:
            if d.disabled or not self.on_screen(d.x, d.y):
                continue
            mark = {"alert": "!", "sus": "?"}.get(d.mode)
            if mark:
                bob = math.sin(self.t * 8) * 2
                text(surf, mark, (d.x - cx, d.y - cy - 42 + bob), 22, d.color, bold=True, anchor="center")
            elif d.meter > 0.05:
                bar(surf, (d.x - cx - 14, d.y - cy - 36, 28, 6), d.meter, AMBER)

        if self.target and not self.dead:
            self.draw_prompt(surf, self.target, cx, cy)

        # ------------------------------------------------------------- screen effects
        if self.hazard_t > 0:
            col = (60, 200, 80) if self.hazard_kind == "spores" else (255, 110, 30)
            tint = pygame.Surface((W, H), pygame.SRCALPHA)
            tint.fill((*col, 40))
            surf.blit(tint, (0, 0))
        if self.alert_flash > 0:
            fr = pygame.Surface((W, H), pygame.SRCALPHA)
            a = int(150 * self.alert_flash)
            for i in range(14):
                pygame.draw.rect(fr, (255, 40, 30, max(0, a - i * 11)), (i, i, W - 2 * i, H - 2 * i), 1)
            surf.blit(fr, (0, 0))
        heat = self.state.heat
        if heat is not None and heat > 70 and "reactor_stable" not in self.state.flags:
            hs = pygame.Surface((W, H), pygame.SRCALPHA)
            hs.fill((255, 80, 20, int((heat - 70) * 1.6 * (0.6 + 0.4 * math.sin(self.t * 6)))))
            surf.blit(hs, (0, 0))
        surf.blit(post_fx(), (0, 0))
        if self.dead:
            d = pygame.Surface((W, H), pygame.SRCALPHA)
            d.fill((0, 0, 0, int(min(1.0, self.death_t / 1.2) * 170)))
            surf.blit(d, (0, 0))

        self.draw_hud(surf)

    def draw_prompt(self, surf, e, cx, cy):
        msg = e.prompt()
        if not msg:
            return
        f = assets.font(14, True)
        w = f.size(msg)[0] + 20
        x = e.x - cx - w / 2
        y = e.ty * TILE - cy - 34 + math.sin(self.t * 4) * 2
        r = pygame.Rect(x, y, w, 24)
        s = pygame.Surface(r.size, pygame.SRCALPHA)
        pygame.draw.rect(s, (8, 14, 22, 220), s.get_rect(), border_radius=6)
        pygame.draw.rect(s, (*CYAN, 200), s.get_rect(), 1, border_radius=6)
        surf.blit(s, r)
        text(surf, msg, r.center, 14, WHITE, bold=True, anchor="center", shadow=False)

    def draw_hud(self, surf):
        st = self.state
        p = self.player
        # battery panel
        box = pygame.Rect(14, 12, 290, 74)
        panel(surf, box, alpha=180)
        b = st.battery / BATTERY_MAX
        col = (90, 230, 255) if b > 0.5 else (AMBER if b > 0.2 else RED)
        if b <= 0.2 and int(self.t * 4) % 2 == 0:
            col = (255, 140, 120)
        text(surf, "ECHO // CORE", (box.x + 14, box.y + 9), 12, GREY, bold=True)
        text(surf, f"{st.battery:4.0f}%", (box.right - 14, box.y + 6), 16, col, bold=True, anchor="topright")
        bar(surf, (box.x + 14, box.y + 30, box.w - 28, 16), b, col, segments=10)
        light = "LIGHT ON" if p.flashlight else "LIGHT OFF"
        text(surf, light, (box.x + 14, box.y + 52), 11, CYAN if p.flashlight else GREY, bold=True)
        if p.sprinting:
            text(surf, "SPRINT", (box.x + 96, box.y + 52), 11, AMBER, bold=True)
        if "life_off" in st.flags:
            text(surf, "NO COOLING", (box.right - 14 - 80, box.y + 52), 11, RED, bold=True)
        frag = len(st.fragments)
        text(surf, f"DATA {frag}/{TOTAL_FRAGMENTS}", (box.x + 140, box.y + 9), 12, (190, 150, 255), bold=True)

        # objective
        obj = None
        for o in self.level.get("objectives", []):
            if not st.check([o["done"]])[0]:
                obj = o["text"]
                break
        f = assets.font(15, True)
        lines = wrap(obj or "", 15, 262, True)
        ow = max([f.size(l)[0] for l in lines] + [200]) + 40
        obox = pygame.Rect(W - ow - 14, 12, ow, 36 + 20 * len(lines))
        panel(surf, obox, alpha=170, border=self.accent)
        text(surf, f"CH.{self.level['chapter']}  {self.level['title'].upper()}", (obox.x + 16, obox.y + 9), 11, GREY, bold=True)
        for i, ln in enumerate(lines):
            text(surf, ("> " if i == 0 else "  ") + ln, (obox.x + 16, obox.y + 28 + i * 20), 15, WHITE, bold=True)

        # heat or countdown
        if st.heat is not None:
            hb = pygame.Rect(W // 2 - 140, 14, 270, 46)
            panel(surf, hb, alpha=170, border=(255, 140, 60))
            hk = st.heat / 100
            hc = (90, 220, 255) if "reactor_stable" in st.flags else ((255, 200, 60) if hk < 0.7 else RED)
            label = "CORE TEMP - STABLE" if "reactor_stable" in st.flags else "CORE TEMP"
            text(surf, label, (hb.x + 12, hb.y + 6), 11, GREY, bold=True)
            text(surf, f"{st.heat:3.0f}%", (hb.right - 12, hb.y + 4), 14, hc, bold=True, anchor="topright")
            bar(surf, (hb.x + 12, hb.y + 24, hb.w - 24, 12), hk, hc)
        if st.timer is not None:
            m, s = divmod(max(0, int(math.ceil(st.timer))), 60)
            urgent = st.timer < 45
            tb = pygame.Rect(W // 2 - 135, 14, 260, 50)
            panel(surf, tb, alpha=180, border=RED)
            text(surf, "REACTOR CRITICAL FAILURE IN", (tb.centerx, tb.y + 6), 11, GREY, bold=True, anchor="midtop")
            c = RED if (urgent and int(self.t * 3) % 2 == 0) else WHITE
            text(surf, f"{m:02d}:{s:02d}", (tb.centerx, tb.y + 20), 22, c, bold=True, anchor="midtop")

        # quick inventory
        x = 18
        y = H - 48
        for k, n, info in st.inv.listing():
            r = pygame.Rect(x, y, 38, 38)
            pygame.draw.rect(surf, (10, 16, 26), r, border_radius=6)
            pygame.draw.rect(surf, (70, 90, 110), r, 1, border_radius=6)
            surf.blit(icon(info["icon"], 28), (x + 5, y + 5))
            if n > 1:
                text(surf, str(n), (r.right - 3, r.bottom - 2), 11, WHITE, bold=True, anchor="bottomright")
            x += 44
        text(surf, "TAB inventory   Q scan   F light   ESC pause", (W - 14, H - 12), 11, (120, 130, 150), anchor="bottomright")

        # hazard warning
        if self.hazard_t > 0:
            msg = "SPORE CONTAMINATION - BATTERY DRAINING" if self.hazard_kind == "spores" else "EXTREME HEAT - BATTERY DRAINING"
            text(surf, msg, (W // 2, 92), 15, GREEN if self.hazard_kind == "spores" else AMBER, bold=True, anchor="midtop",
                 alpha=int(170 + 80 * math.sin(self.t * 10)))

        # toasts
        y = H - 96
        for msg, col, life in reversed(self.toasts):
            a = int(255 * min(1.0, life / 0.5))
            f = assets.font(15, True)
            w = f.size(msg)[0] + 30
            r = pygame.Rect(W // 2 - w // 2, y, w, 30)
            s = pygame.Surface(r.size, pygame.SRCALPHA)
            pygame.draw.rect(s, (8, 12, 20, int(200 * a / 255)), s.get_rect(), border_radius=6)
            pygame.draw.rect(s, (*col, a), s.get_rect(), 1, border_radius=6)
            surf.blit(s, r)
            text(surf, msg, r.center, 15, col, bold=True, anchor="center", alpha=a)
            y -= 36
