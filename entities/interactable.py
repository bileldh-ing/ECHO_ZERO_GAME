"""Every world object the player can touch, read, repair or walk through."""
import math
import random

import pygame

from settings import TILE, CELL_RESTORE, DOCK_RATE, BATTERY_MAX
from systems import assets
from systems.inventory import ITEMS, FRAGMENTS


class Entity:
    solid = False
    opaque = False
    layer = 1                 # 0 = floor decal, 1 = y-sorted
    interact_range = 46
    sprite = None

    def __init__(self, gp, d):
        self.gp = gp
        self.d = d
        self.id = d["id"]
        self.uid = f"{gp.level['id']}:{self.id}"
        self.tx, self.ty = d["x"], d["y"]
        self.tw, self.th = d.get("w", 1), d.get("h", 1)
        self.x = (self.tx + self.tw / 2) * TILE
        self.y = (self.ty + self.th / 2) * TILE
        self.t = random.uniform(0, 10)
        self.highlight = 0.0

    # flags helpers
    @property
    def state(self):
        return self.gp.state

    def flag(self, name):
        return name in self.state.flags

    def setup(self):
        if self.solid:
            for dx in range(self.tw):
                for dy in range(self.th):
                    self.gp.tilemap.block(self.tx + dx, self.ty + dy, self, self.opaque)

    def interactive(self):
        return False

    def pending(self):
        """Still something to do here (used by objective markers)."""
        return True

    def prompt(self):
        return ""

    def interact(self):
        pass

    def update(self, dt):
        self.t += dt
        self.highlight = max(0.0, self.highlight - dt)

    def static_lights(self):
        return []

    def dynamic_lights(self):
        return []

    def draw(self, surf, cx, cy):
        if self.sprite:
            img = assets.image(self.sprite)
            surf.blit(img, (self.x - cx - img.get_width() / 2, (self.ty + self.th) * TILE - cy - img.get_height() + 2))

    def draw_glow(self, surf, cx, cy):
        pass

    @property
    def sort_y(self):
        return (self.ty + self.th) * TILE - 2

    def dist_to_player(self):
        p = self.gp.player
        # distance to the object's footprint
        rx = max(self.tx * TILE, min(p.x, (self.tx + self.tw) * TILE))
        ry = max(self.ty * TILE, min(p.y, (self.ty + self.th) * TILE))
        return math.hypot(p.x - rx, p.y - ry)


# ============================================================================ doors
class Door(Entity):
    solid = True
    opaque = True
    layer = 0
    interact_range = 40

    def __init__(self, gp, d):
        super().__init__(gp, d)
        self.reqs = d.get("requires", [])
        self.open_flag = f"opened:{self.uid}"
        self.opened = self.flag(self.open_flag)
        self.progress = 1.0 if self.opened else 0.0
        tm = gp.tilemap
        self.horizontal = tm.ch(self.tx - 1, self.ty) in "#W" or tm.ch(self.tx + 1, self.ty) in "#W"
        self.bump_cd = 0.0

    def setup(self):
        if not self.opened:
            super().setup()

    def locked(self):
        ok, _ = self.state.check(self.reqs)
        return not ok

    def pending(self):
        return not self.opened

    def interactive(self):
        return not self.opened

    def prompt(self):
        return "[E] Locked" if self.locked() else "[E] Open door"

    def open(self):
        if self.opened:
            return
        self.opened = True
        self.state.set_flag(self.open_flag)
        self.state.set_flag(f"opened:{self.id}")
        self.gp.tilemap.unblock(self.tx, self.ty)
        assets.play("door", 0.8)
        self.gp.particles.emit(self.x, self.y, 10, (180, 200, 220), speed=50, life=0.7, size=1, glow=False)
        if self.d.get("airlock"):
            self.gp.shake(4)

    def interact(self):
        if self.locked():
            assets.play("door_locked", 0.7)
            self.gp.toast(self.d.get("locked_msg") or self.state.describe(self.state.check(self.reqs)[1]), (255, 120, 90))
        else:
            self.open()

    def update(self, dt):
        super().update(dt)
        self.bump_cd = max(0.0, self.bump_cd - dt)
        target = 1.0 if self.opened else 0.0
        self.progress += (target - self.progress) * min(1.0, dt * 7)
        if not self.opened and not self.reqs and self.dist_to_player() < 26:
            self.open()

    def draw(self, surf, cx, cy):
        x, y = self.tx * TILE - cx, self.ty * TILE - cy
        theme = self.gp.level["theme"]
        panel = assets.tile(theme, "door_panel")
        # frame
        pygame.draw.rect(surf, (20, 22, 28), (x, y, TILE, TILE))
        slide = int(self.progress * TILE / 2)
        half = TILE // 2
        if self.horizontal:
            left = panel.subsurface((0, 0, half, TILE))
            right = panel.subsurface((half, 0, half, TILE))
            if half - slide > 0:
                surf.blit(left, (x, y), (slide, 0, half - slide, TILE))
                surf.blit(right, (x + half + slide, y), (0, 0, half - slide, TILE))
        else:
            top = panel.subsurface((0, 0, TILE, half))
            bot = panel.subsurface((0, half, TILE, half))
            if half - slide > 0:
                surf.blit(top, (x, y), (0, slide, TILE, half - slide))
                surf.blit(bot, (x, y + half + slide), (0, 0, TILE, half - slide))
        if not self.opened:
            col = (255, 70, 60) if self.locked() else (90, 240, 150)
            pygame.draw.rect(surf, col, (x + TILE // 2 - 3, y + 3, 6, 3))

    def draw_glow(self, surf, cx, cy):
        if not self.opened:
            col = (255, 70, 60) if self.locked() else (90, 240, 150)
            tex = self.gp.lighting.light_texture(14, col, 0.9)
            surf.blit(tex, (self.tx * TILE - cx + TILE // 2 - 14, self.ty * TILE - cy + 4 - 14), special_flags=pygame.BLEND_ADD)


# ============================================================================ pickups
class Pickup(Entity):
    layer = 1

    def __init__(self, gp, d):
        super().__init__(gp, d)
        self.item = d["item"]
        self.taken = self.flag(f"taken:{self.uid}")
        self.icon = ITEMS.get(self.item, {}).get("icon", "item_component")
        self.color = {"battery": (110, 240, 150), "keycard_maint": (90, 160, 255), "component": (255, 190, 80),
                      "command_key": (255, 210, 90)}.get(self.item, (200, 200, 255))

    def update(self, dt):
        super().update(dt)
        if not self.taken and self.dist_to_player() < 20:
            self.collect()

    def pending(self):
        return not self.taken

    def collect(self):
        self.taken = True
        self.state.set_flag(f"taken:{self.uid}")
        if self.item == "battery":
            self.state.battery_add(CELL_RESTORE)
            self.gp.toast(f"Energy cell absorbed  +{int(CELL_RESTORE)}%", (110, 240, 150))
            assets.play("charge", 0.6)
        else:
            self.state.inv.add(self.item)
            self.gp.toast(f"Acquired: {ITEMS[self.item]['name']}", self.color)
        assets.play("pickup", 0.8)
        self.gp.particles.emit(self.x, self.y, 18, self.color, speed=110, life=0.7, size=2)

    def dynamic_lights(self):
        if self.taken:
            return []
        return [(self.x, self.y, 46, self.color, 0.55 + 0.2 * math.sin(self.t * 4))]

    def draw(self, surf, cx, cy):
        if self.taken:
            return
        img = assets.image(self.icon)
        bob = math.sin(self.t * 3) * 3
        pygame.draw.ellipse(surf, (0, 0, 0), (self.x - cx - 8, self.y - cy + 8, 16, 5))
        surf.blit(img, (self.x - cx - img.get_width() / 2, self.y - cy - img.get_height() / 2 - 4 + bob))

    def draw_glow(self, surf, cx, cy):
        if self.taken:
            return
        img = assets.image(self.icon)
        bob = math.sin(self.t * 3) * 3
        g = self.gp.lighting.light_texture(20, self.color, 0.5 + 0.5 * (self.highlight > 0))
        surf.blit(g, (self.x - cx - 20, self.y - cy - 24 + bob), special_flags=pygame.BLEND_ADD)

    @property
    def sort_y(self):
        return self.y + 6


# ============================================================================ terminals
class Terminal(Entity):
    solid = True
    interact_range = 48

    def __init__(self, gp, d):
        super().__init__(gp, d)
        self.reqs = d.get("requires", [])

    def interactive(self):
        return True

    def prompt(self):
        return "[E] Access terminal"

    def online(self):
        return self.state.check(self.reqs)[0]

    def pending(self):
        frag = self.d.get("fragment")
        if frag:
            return self.online() and frag not in self.state.fragments
        return not self.flag(f"read:{self.uid}") or bool(self.d.get("choice"))

    def interact(self):
        assets.play("beep", 0.6)
        if not self.online():
            self.gp.dialogue(self.d.get("locked_dialogue", ""))
            return
        self.state.set_flag(f"read:{self.uid}")

        def done():
            frag = self.d.get("fragment")
            if frag and self.state.add_fragment(frag):
                self.gp.toast(f"Data fragment recovered: {FRAGMENTS[frag]}", (190, 150, 255))
                assets.play("pickup", 0.8)
                self.gp.particles.emit(self.x, self.y - 10, 24, (180, 140, 255), speed=120, life=0.9, size=2)
            if self.d.get("choice"):
                self.gp.open_choice(self.d["choice"])
        self.gp.dialogue(self.d.get("dialogue", ""), done)

    def draw(self, surf, cx, cy):
        self.sprite = "terminal_on" if self.online() else "terminal_off"
        super().draw(surf, cx, cy)

    def dynamic_lights(self):
        if not self.online():
            return []
        flick = 0.8 + 0.15 * math.sin(self.t * 13) * (random.random() < 0.3)
        return [(self.x, self.y - 6, 70, (80, 200, 255), flick)]

    def draw_glow(self, surf, cx, cy):
        if self.online():
            g = self.gp.lighting.light_texture(18, (60, 160, 220), 0.7 + (0.5 if self.highlight > 0 else 0))
            surf.blit(g, (self.x - cx - 18, self.y - cy - 24), special_flags=pygame.BLEND_ADD)
            if not self.flag(f"read:{self.uid}"):
                bob = math.sin(self.t * 4) * 2
                pygame.draw.polygon(surf, (120, 230, 255), [(self.x - cx - 4, self.y - cy - 34 + bob),
                                                            (self.x - cx + 4, self.y - cy - 34 + bob),
                                                            (self.x - cx, self.y - cy - 28 + bob)])


class CipherTerminal(Terminal):
    def online(self):
        return True

    def pending(self):
        return not self.flag(self.d["sets"])

    def prompt(self):
        return "[E] Decode corrupted terminal" if not self.flag(self.d["sets"]) else "[E] Read decoded order"

    def interact(self):
        assets.play("beep", 0.6)
        if self.flag(self.d["sets"]):
            self.gp.dialogue(self.d.get("dialogue_after", ""))
            return

        def solved():
            self.state.set_flag(self.d["sets"])
            self.state.set_flag(f"read:{self.uid}")
            frag = self.d.get("fragment")

            def after():
                if frag and self.state.add_fragment(frag):
                    self.gp.toast(f"Data fragment recovered: {FRAGMENTS[frag]}", (190, 150, 255))
            self.gp.dialogue(self.d.get("dialogue_after", ""), after)
        self.gp.open_cipher(self.d["text"], self.d["shift"], solved)

    def draw(self, surf, cx, cy):
        self.sprite = "terminal_broken" if not self.flag(self.d["sets"]) else "terminal_on"
        Entity.draw(self, surf, cx, cy)


# ============================================================================ machinery
class Panel(Entity):
    solid = True
    interact_range = 48

    def __init__(self, gp, d):
        super().__init__(gp, d)
        self.reqs = d.get("requires", [])

    @property
    def done(self):
        return self.flag(self.d["sets"])

    def interactive(self):
        return True

    def pending(self):
        return not self.done

    def prompt(self):
        return "[E] Power conduit (online)" if self.done else "[E] Reroute power"

    def interact(self):
        if self.done:
            self.gp.toast("Conduit already online.", (140, 220, 255))
            return
        ok, why = self.state.check(self.reqs)
        if not ok:
            assets.play("error", 0.6)
            self.gp.toast(self.d.get("locked_msg") or self.state.describe(why), (255, 120, 90))
            return

        def solved():
            self.gp.set_flag(self.d["sets"])
            self.gp.particles.sparks(self.x, self.y - 10, 20)
            self.gp.shake(3)
            if self.d.get("dialogue_after"):
                self.gp.dialogue(self.d["dialogue_after"])
        self.gp.open_power_puzzle(self.d["puzzle"], solved, self.uid)

    def draw(self, surf, cx, cy):
        self.sprite = "panel_on" if self.done else "panel_off"
        super().draw(surf, cx, cy)

    def dynamic_lights(self):
        col = (90, 220, 255) if self.done else (255, 170, 60)
        return [(self.x, self.y - 4, 60, col, 0.5 + 0.2 * math.sin(self.t * 5))]

    def draw_glow(self, surf, cx, cy):
        col = (60, 170, 220) if self.done else (220, 140, 40)
        g = self.gp.lighting.light_texture(16, col, 0.6 + (0.6 if self.highlight > 0 else 0))
        surf.blit(g, (self.x - cx - 16, self.y - cy - 22), special_flags=pygame.BLEND_ADD)


class Switch(Entity):
    solid = True

    def __init__(self, gp, d):
        super().__init__(gp, d)
        self.reqs = d.get("requires", [])

    @property
    def on(self):
        return self.flag(self.d["sets"])

    def interactive(self):
        return not self.on

    def pending(self):
        return not self.on

    def prompt(self):
        return "[E] Activate pump"

    def interact(self):
        ok, why = self.state.check(self.reqs)
        if not ok:
            assets.play("error", 0.6)
            self.gp.toast(self.d.get("locked_msg") or self.state.describe(why), (255, 120, 90))
            return
        assets.play("confirm", 0.8)
        self.gp.set_flag(self.d["sets"])
        self.gp.particles.emit(self.x, self.y, 30, (120, 200, 255), speed=90, life=1.0, size=2)
        if self.d.get("dialogue_after"):
            self.gp.dialogue(self.d["dialogue_after"])

    def draw(self, surf, cx, cy):
        self.sprite = "switch_on" if self.on else "switch_off"
        super().draw(surf, cx, cy)


class Console(Entity):
    solid = True
    interact_range = 50

    def interactive(self):
        return True

    def pending(self):
        return not self.flag("allocation_done")

    def prompt(self):
        return "[E] Reactor power allocation"

    def interact(self):
        assets.play("beep", 0.6)
        first = not self.flag("allocation_done")

        def confirmed():
            if first and self.d.get("dialogue_after"):
                self.gp.dialogue(self.d["dialogue_after"])
        self.gp.open_console(confirmed)

    def draw(self, surf, cx, cy):
        self.sprite = "console_on"
        super().draw(surf, cx, cy)

    def dynamic_lights(self):
        return [(self.x, self.y, 80, (255, 160, 90), 0.7)]


class Dock(Entity):
    layer = 0
    sprite = "dock"

    def __init__(self, gp, d):
        super().__init__(gp, d)
        self.inside = True   # player spawns here; don't save instantly
        self.sound_cd = 0.0

    def update(self, dt):
        super().update(dt)
        on = self.dist_to_player() < 14
        if on:
            if self.state.battery < BATTERY_MAX:
                self.state.battery_add(DOCK_RATE * dt)
                if random.random() < dt * 12:
                    self.gp.particles.emit(self.x + random.uniform(-10, 10), self.y + 6, 1, (90, 210, 255),
                                           speed=30, life=0.8, size=1, angle=-math.pi / 2, spread=0.6, drag=0.5)
                self.sound_cd -= dt
                if self.sound_cd <= 0:
                    assets.play("charge", 0.25)
                    self.sound_cd = 1.2
            if not self.inside:
                self.gp.checkpoint_here((self.tx, self.ty))
        self.inside = on

    def draw(self, surf, cx, cy):
        img = assets.image("dock")
        surf.blit(img, (self.x - cx - img.get_width() / 2, self.y - cy - img.get_height() / 2))

    def dynamic_lights(self):
        return [(self.x, self.y, 70, (90, 200, 255), 0.6 + 0.25 * math.sin(self.t * 2.5))]

    def draw_glow(self, surf, cx, cy):
        g = self.gp.lighting.light_texture(20, (40, 120, 170), 0.6 + 0.3 * math.sin(self.t * 2.5))
        surf.blit(g, (self.x - cx - 20, self.y - cy - 20), special_flags=pygame.BLEND_ADD)


class Lamp(Entity):
    layer = 1

    def lit(self):
        f = self.d.get("flag")
        return f is None or self.flag(f)

    def static_lights(self):
        if self.d.get("alarm") or not self.lit():
            return []
        return [(self.x, self.y + 8, self.d.get("radius", 140), tuple(self.d.get("color", (255, 230, 200))), 1.0)]

    def dynamic_lights(self):
        if self.d.get("alarm"):
            k = 0.55 + 0.45 * math.sin(self.t * 5)
            return [(self.x, self.y + 6, self.d.get("radius", 140), tuple(self.d.get("color")), k)]
        return []

    def draw(self, surf, cx, cy):
        img = assets.image("lamp_on" if self.lit() else "lamp_off")
        surf.blit(img, (self.x - cx - 16, self.y - cy - 16))

    def draw_glow(self, surf, cx, cy):
        if self.lit():
            col = tuple(self.d.get("color", (255, 230, 200)))
            k = 0.8 if not self.d.get("alarm") else 0.5 + 0.5 * math.sin(self.t * 5)
            g = self.gp.lighting.light_texture(16, col, k)
            surf.blit(g, (self.x - cx - 16, self.y - cy - 20), special_flags=pygame.BLEND_ADD)


class Exit(Entity):
    layer = 0

    def __init__(self, gp, d):
        super().__init__(gp, d)
        self.reqs = d.get("requires", [])
        self.cd = 0.0
        self.used = False

    def ready(self):
        return self.state.check(self.reqs)[0] and "next" in self.d

    def update(self, dt):
        super().update(dt)
        self.cd = max(0.0, self.cd - dt)
        if self.used:
            return
        if self.dist_to_player() < 12:
            if self.ready():
                self.used = True
                assets.play("confirm", 0.8)
                self.gp.leave_level(self.d["next"], self.d.get("dialogue"))
            elif self.cd <= 0:
                self.cd = 2.5
                assets.play("door_locked", 0.6)
                self.gp.toast(self.d.get("locked_msg", "Lift offline."), (255, 120, 90))

    def draw(self, surf, cx, cy):
        img = assets.image(f"exit_{int(self.t * 6) % 4}" if self.ready() else "exit_0")
        if not self.ready():
            img = img.copy()
            img.fill((90, 90, 90), special_flags=pygame.BLEND_MULT)
        surf.blit(img, (self.x - cx - img.get_width() / 2, self.y - cy - img.get_height() / 2))

    def dynamic_lights(self):
        if self.ready():
            return [(self.x, self.y, 90, (90, 210, 255), 0.8)]
        return []


class Hazard(Entity):
    layer = 0

    def __init__(self, gp, d):
        super().__init__(gp, d)
        self.rect = pygame.Rect(self.tx * TILE, self.ty * TILE, self.tw * TILE, self.th * TILE)
        self.kind = d.get("kind", "spores")
        self.color = (120, 230, 110) if self.kind == "spores" else (255, 130, 50)

    def active(self):
        f = self.d.get("disabled_by")
        return not (f and self.flag(f))

    def update(self, dt):
        super().update(dt)
        if not self.active():
            return
        p = self.gp.player
        if self.rect.collidepoint(p.x, p.y):
            self.gp.hazard_drain(self.d.get("drain", 5.0) * dt, self.kind)
        # ambient particles near the camera
        if random.random() < dt * (14 if self.kind == "spores" else 22):
            x = random.uniform(self.rect.left, self.rect.right)
            y = random.uniform(self.rect.top, self.rect.bottom)
            if self.kind == "spores":
                self.gp.particles.emit(x, y, 1, self.color, speed=14, life=3.0, size=2, drag=0.1)
            else:
                self.gp.particles.emit(x, y, 1, self.color, speed=40, life=1.0, size=2, angle=-math.pi / 2,
                                       spread=0.8, drag=0.4, grav=-30)

    def draw(self, surf, cx, cy):
        if not self.active():
            return
        r = self.rect.move(-cx, -cy)
        if not hasattr(self, "_tint"):
            self._tint = pygame.Surface(r.size, pygame.SRCALPHA)
            self._tint.fill((*self.color, 30))
        surf.blit(self._tint, r)

    def dynamic_lights(self):
        if self.active() and self.kind == "fire":
            out = []
            for i in range(0, self.tw, 3):
                out.append(((self.tx + i + 1) * TILE, self.y, 80, (255, 120, 40), 0.6 + 0.3 * math.sin(self.t * 9 + i)))
            return out
        return []


class Trigger(Entity):
    layer = 0

    def __init__(self, gp, d):
        super().__init__(gp, d)
        self.rect = pygame.Rect(self.tx * TILE, self.ty * TILE, self.tw * TILE, self.th * TILE)
        self.fired = self.flag(f"trig:{self.uid}")

    def update(self, dt):
        if not self.fired and self.rect.collidepoint(self.gp.player.x, self.gp.player.y):
            self.fired = True
            self.state.set_flag(f"trig:{self.uid}")
            self.gp.dialogue(self.d["dialogue"])

    def draw(self, surf, cx, cy):
        pass


class Sparks(Entity):
    layer = 1

    def __init__(self, gp, d):
        super().__init__(gp, d)
        self.next = 1.0
        self.flash = 0.0

    def update(self, dt):
        super().update(dt)
        self.next -= dt
        self.flash = max(0.0, self.flash - dt * 4)
        if self.next <= 0:
            self.next = random.uniform(0.6, 2.4)
            self.flash = 1.0
            self.gp.particles.sparks(self.x + random.uniform(-6, 6), self.y - 12, random.randint(5, 12))

    def dynamic_lights(self):
        if self.flash > 0:
            return [(self.x, self.y - 10, 90, (255, 220, 150), self.flash)]
        return []


class Decor(Entity):
    SOLID = {"crate", "barrel", "plant", "core", "aicore", "holotable", "cryo", "transmitter", "debris"}
    OPAQUE = {"crate", "barrel", "core", "aicore", "transmitter"}

    def __init__(self, gp, d):
        super().__init__(gp, d)
        k = d["type"]
        self.kind = k
        self.solid = k in self.SOLID
        self.opaque = k in self.OPAQUE
        if k == "pipe":
            self.layer = 0

    def frame_name(self):
        k = self.kind
        if k == "core":
            return f"reactor_{int(self.t * 8) % 8}"
        if k == "aicore":
            if self.state.choices.get("ai_fate") == "shutdown":
                return "aicore_0"
            return f"aicore_{int(self.t * 6) % 8}"
        if k == "holotable":
            return f"holotable_{int(self.t * 6) % 8}"
        if k == "transmitter":
            return f"transmitter_{int(self.t * 2) % 2}"
        if k == "plant":
            return f"plant_{self.d.get('variant', 0)}"
        if k == "pipe":
            return "pipe_v" if self.d.get("vertical") else "pipe_h"
        return k

    def draw(self, surf, cx, cy):
        img = assets.image(self.frame_name())
        if self.kind == "aicore" and self.state.choices.get("ai_fate") == "shutdown":
            img = img.copy()
            img.fill((70, 70, 80), special_flags=pygame.BLEND_MULT)
        if self.kind == "pipe":
            surf.blit(img, (self.tx * TILE - cx, self.ty * TILE - cy))
            return
        bottom = (self.ty + self.th) * TILE - cy + (6 if self.th > 1 else 2)
        surf.blit(img, (self.x - cx - img.get_width() / 2, bottom - img.get_height()))

    def dynamic_lights(self):
        if self.kind == "core":
            heat = self.state.heat or 30
            k = 0.7 + 0.3 * math.sin(self.t * (2 + heat / 25))
            return [(self.x, self.y, 230 + heat, (255, 140, 60), k * 1.2)]
        if self.kind == "aicore" and self.state.choices.get("ai_fate") != "shutdown":
            return [(self.x, self.y, 190, (255, 60, 50), 0.75 + 0.25 * math.sin(self.t * 2))]
        if self.kind == "holotable":
            return [(self.x, self.y - 10, 110, (90, 200, 255), 0.7)]
        if self.kind == "transmitter":
            return [(self.x, self.y - 20, 120, (120, 180, 255), 0.6)]
        return []

    def draw_glow(self, surf, cx, cy):
        if self.kind == "core":
            g = self.gp.lighting.light_texture(50, (200, 90, 30), 0.6 + 0.3 * math.sin(self.t * 3))
            surf.blit(g, (self.x - cx - 50, self.y - cy - 46), special_flags=pygame.BLEND_ADD)
        elif self.kind == "aicore" and self.state.choices.get("ai_fate") != "shutdown":
            g = self.gp.lighting.light_texture(44, (200, 40, 30), 0.6 + 0.3 * math.sin(self.t * 2))
            surf.blit(g, (self.x - cx - 44, self.y - cy - 40), special_flags=pygame.BLEND_ADD)


TYPES = {
    "door": Door, "pickup": Pickup, "terminal": Terminal, "cipher": CipherTerminal, "panel": Panel,
    "switch": Switch, "console": Console, "dock": Dock, "lamp": Lamp, "exit": Exit, "hazard": Hazard,
    "trigger": Trigger, "sparks": Sparks,
}


def create(gp, d):
    cls = TYPES.get(d["type"], Decor)
    return cls(gp, d)
