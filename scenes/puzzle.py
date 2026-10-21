"""Puzzle overlays: power routing grid, terminal cipher and reactor power allocation."""
import math
import random

import pygame

from settings import W, H, CYAN, WHITE, GREY, AMBER, RED, GREEN
from scenes.base import Scene
from systems import assets
from systems.puzzles import PowerGrid, Cipher, DIRS, UP, RIGHT, DOWN, LEFT
from systems.ui import panel, text, wrap, icon


def dim(surf, a=160):
    s = pygame.Surface((W, H), pygame.SRCALPHA)
    s.fill((0, 0, 0, a))
    surf.blit(s, (0, 0))


# ============================================================================ power grid
class PowerPuzzle(Scene):
    overlay = True

    def __init__(self, game, spec, state, on_solved):
        super().__init__(game)
        self.grid = PowerGrid(spec)
        self.state = state
        self.on_solved = on_solved
        self.cs = min(84, 520 // max(self.grid.w, self.grid.h))
        gw, gh = self.grid.w * self.cs, self.grid.h * self.cs
        self.origin = (W // 2 - gw // 2, H // 2 - gh // 2 + 20)
        self.cursor = list(self.grid.source)
        self.vis = {p: 0.0 for p in self.grid.cells}   # rotation animation offset (degrees)
        self.t = 0.0
        self.done_t = None
        self.powered = self.grid.powered()
        self.flow = 0.0
        self.msg = ""
        self.msg_t = 0.0

    def cell_at(self, mx, my):
        x = (mx - self.origin[0]) // self.cs
        y = (my - self.origin[1]) // self.cs
        if 0 <= x < self.grid.w and 0 <= y < self.grid.h:
            return int(x), int(y)
        return None

    def act(self, pos):
        if self.done_t is not None:
            return
        pos = tuple(pos)
        c = self.grid.cells.get(pos)
        if not c:
            return
        if c.kind == "broken":
            if self.state.inv.take("component"):
                self.grid.repair(pos)
                assets.play("solve", 0.4)
                self.msg, self.msg_t = "Component installed - conduit repaired.", 2.5
            else:
                assets.play("error", 0.6)
                self.msg, self.msg_t = "Broken conduit. A circuit component is needed to repair it.", 2.5
        elif self.grid.rotate(pos):
            self.vis[pos] = -90.0
            assets.play("rotate", 0.6)
        else:
            assets.play("error", 0.3)
        self.powered = self.grid.powered()
        if self.grid.solved():
            self.done_t = 0.0
            assets.play("solve", 0.9)

    def handle_event(self, e):
        if e.type == pygame.KEYDOWN:
            if e.key == pygame.K_ESCAPE or e.key == pygame.K_TAB:
                if self.done_t is None:
                    self.close()
            elif e.key in (pygame.K_LEFT, pygame.K_a):
                self.cursor[0] = max(0, self.cursor[0] - 1)
            elif e.key in (pygame.K_RIGHT, pygame.K_d):
                self.cursor[0] = min(self.grid.w - 1, self.cursor[0] + 1)
            elif e.key in (pygame.K_UP, pygame.K_w):
                self.cursor[1] = max(0, self.cursor[1] - 1)
            elif e.key in (pygame.K_DOWN, pygame.K_s):
                self.cursor[1] = min(self.grid.h - 1, self.cursor[1] + 1)
            elif e.key in (pygame.K_SPACE, pygame.K_e, pygame.K_RETURN):
                self.act(self.cursor)
        elif e.type == pygame.MOUSEMOTION:
            c = self.cell_at(*e.pos)
            if c:
                self.cursor = list(c)
        elif e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
            c = self.cell_at(*e.pos)
            if c:
                self.cursor = list(c)
                self.act(c)

    def update(self, dt):
        self.t += dt
        self.flow += dt
        self.msg_t = max(0.0, self.msg_t - dt)
        for p in self.vis:
            self.vis[p] *= max(0.0, 1 - dt * 16)
        if self.done_t is not None:
            self.done_t += dt
            if self.done_t > 1.1:
                self.close()
                self.on_solved()

    def draw_cell(self, surf, pos, c):
        cs = self.cs
        x0 = self.origin[0] + pos[0] * cs
        y0 = self.origin[1] + pos[1] * cs
        s = pygame.Surface((cs, cs), pygame.SRCALPHA)
        on = pos in self.powered
        base = (30, 38, 52) if not on else (22, 50, 66)
        pygame.draw.rect(s, base, (3, 3, cs - 6, cs - 6), border_radius=8)
        pygame.draw.rect(s, (70, 84, 104), (3, 3, cs - 6, cs - 6), 1, border_radius=8)
        mid = cs // 2
        thick = max(8, cs // 6)
        if c.kind == "broken":
            col = (150, 60, 50)
        elif on:
            pulse = 0.75 + 0.25 * math.sin(self.flow * 8 - (pos[0] + pos[1]) * 0.9)
            col = tuple(int(v * pulse) for v in (110, 230, 255))
        else:
            col = (90, 96, 110)
        for bit, (dx, dy) in DIRS.items():
            if c.mask & bit:
                ex, ey = mid + dx * (cs // 2), mid + dy * (cs // 2)
                pygame.draw.line(s, (12, 14, 20), (mid, mid), (ex, ey), thick + 6)
                pygame.draw.line(s, col, (mid, mid), (ex, ey), thick)
                if on:
                    pygame.draw.line(s, (230, 250, 255), (mid, mid), (ex, ey), max(2, thick // 4))
        pygame.draw.circle(s, (12, 14, 20), (mid, mid), thick // 2 + 5)
        pygame.draw.circle(s, col, (mid, mid), thick // 2 + 2)
        if c.kind == "source":
            pygame.draw.circle(s, (255, 190, 70), (mid, mid), cs // 4)
            pygame.draw.circle(s, (255, 240, 200), (mid, mid), cs // 8)
        elif c.kind == "target":
            pygame.draw.circle(s, (20, 24, 30), (mid, mid), cs // 4)
            pygame.draw.circle(s, (120, 255, 170) if on else (200, 80, 70), (mid, mid), cs // 4, 4)
            if on:
                pygame.draw.circle(s, (200, 255, 220), (mid, mid), cs // 9)
        elif c.kind == "broken":
            pygame.draw.line(s, (255, 90, 70), (mid - 12, mid - 12), (mid + 12, mid + 12), 4)
            pygame.draw.line(s, (255, 90, 70), (mid + 12, mid - 12), (mid - 12, mid + 12), 4)
        ang = self.vis.get(pos, 0.0)
        if abs(ang) > 0.5:
            s = pygame.transform.rotozoom(s, -ang, 1.0)
        surf.blit(s, (x0 + cs // 2 - s.get_width() // 2, y0 + cs // 2 - s.get_height() // 2))
        if on and c.kind != "broken":
            g = pygame.Surface((cs, cs))
            g.fill((0, 0, 0))
            pygame.draw.circle(g, (10, 40, 55), (mid, mid), cs // 2)
            surf.blit(g, (x0, y0), special_flags=pygame.BLEND_ADD)

    def draw(self, surf):
        dim(surf, 170)
        gw, gh = self.grid.w * self.cs, self.grid.h * self.cs
        box = pygame.Rect(self.origin[0] - 40, self.origin[1] - 92, gw + 80, gh + 150)
        panel(surf, box)
        text(surf, "POWER ROUTING", (box.centerx, box.y + 18), 22, CYAN, bold=True, anchor="midtop")
        text(surf, "Rotate conduits to connect the SOURCE to every TARGET node", (box.centerx, box.y + 50), 13, GREY, anchor="midtop")
        for y in range(self.grid.h):
            for x in range(self.grid.w):
                pygame.draw.rect(surf, (16, 20, 28), (self.origin[0] + x * self.cs + 3, self.origin[1] + y * self.cs + 3,
                                                      self.cs - 6, self.cs - 6), border_radius=8)
        for pos, c in self.grid.cells.items():
            self.draw_cell(surf, pos, c)
        cx = self.origin[0] + self.cursor[0] * self.cs
        cy = self.origin[1] + self.cursor[1] * self.cs
        a = int(160 + 90 * math.sin(self.t * 7))
        pygame.draw.rect(surf, (255, 255, 255), (cx + 1, cy + 1, self.cs - 2, self.cs - 2), 2, border_radius=9)
        lit = sum(1 for t in self.grid.targets if t in self.powered)
        text(surf, f"TARGETS {lit}/{len(self.grid.targets)}", (box.x + 20, box.bottom - 32), 14,
             GREEN if lit == len(self.grid.targets) else AMBER, bold=True)
        comp = self.state.inv.items.get("component", 0)
        if any(c.kind == "broken" for c in self.grid.cells.values()) or comp:
            text(surf, f"COMPONENTS: {comp}", (box.centerx, box.bottom - 32), 14, AMBER, anchor="midtop")
        text(surf, "Click / SPACE rotate   ESC exit", (box.right - 20, box.bottom - 32), 13, GREY, anchor="topright")
        if self.msg_t > 0:
            text(surf, self.msg, (box.centerx, box.bottom + 14), 15, AMBER, anchor="midtop")
        if self.done_t is not None:
            k = min(1.0, self.done_t * 3)
            text(surf, "CIRCUIT COMPLETE", (W // 2, box.y - 40), 30, GREEN, bold=True, anchor="midtop", alpha=int(255 * k))


# ============================================================================ cipher
class CipherPuzzle(Scene):
    overlay = True

    def __init__(self, game, plain, shift, on_solved):
        super().__init__(game)
        self.c = Cipher(plain, shift)
        self.on_solved = on_solved
        self.t = 0.0
        self.done_t = None
        self.glitch = 0.0

    def handle_event(self, e):
        if self.done_t is not None:
            return
        if e.type == pygame.KEYDOWN:
            if e.key == pygame.K_ESCAPE:
                self.close()
            elif e.key in (pygame.K_LEFT, pygame.K_a, pygame.K_DOWN, pygame.K_s):
                self.c.nudge(-1)
                assets.play("rotate", 0.5)
                self.glitch = 0.2
            elif e.key in (pygame.K_RIGHT, pygame.K_d, pygame.K_UP, pygame.K_w):
                self.c.nudge(1)
                assets.play("rotate", 0.5)
                self.glitch = 0.2
            elif e.key in (pygame.K_RETURN, pygame.K_SPACE, pygame.K_e):
                if self.c.solved():
                    self.done_t = 0.0
                    assets.play("solve", 0.9)
                else:
                    assets.play("error", 0.6)
                    self.glitch = 0.5
        elif e.type == pygame.MOUSEWHEEL:
            self.c.nudge(1 if e.y > 0 else -1)
            assets.play("rotate", 0.5)

    def update(self, dt):
        self.t += dt
        self.glitch = max(0.0, self.glitch - dt)
        if self.done_t is not None:
            self.done_t += dt
            if self.done_t > 1.2:
                self.close()
                self.on_solved()

    def draw(self, surf):
        dim(surf, 175)
        box = pygame.Rect(W // 2 - 380, H // 2 - 190, 760, 360)
        panel(surf, box, border=(200, 200, 140))
        text(surf, "CORRUPTED TERMINAL - SIGNAL DECODER", (box.centerx, box.y + 18), 20, (220, 220, 150), bold=True, anchor="midtop")
        text(surf, "Tune the decode offset until the message reads clearly.", (box.centerx, box.y + 50), 13, GREY, anchor="midtop")
        text(surf, "RAW:", (box.x + 30, box.y + 92), 13, GREY)
        y = box.y + 112
        for ln in wrap(self.c.cipher, 18, box.w - 60):
            text(surf, ln, (box.x + 30, y), 18, (150, 110, 110))
            y += 24
        text(surf, "DECODED:", (box.x + 30, box.y + 176), 13, GREY)
        dec = self.c.decoded()
        solved = self.c.solved()
        col = GREEN if solved else (160, 220, 255)
        y = box.y + 196
        for ln in wrap(dec, 20, box.w - 60):
            if self.glitch > 0 and not solved:
                ln = "".join(ch if random.random() > 0.3 else random.choice("#%@&?") for ch in ln)
            text(surf, ln, (box.x + 30, y), 20, col, bold=True)
            y += 28
        # dial
        dial = pygame.Rect(box.centerx - 110, box.bottom - 70, 220, 44)
        pygame.draw.rect(surf, (20, 26, 36), dial, border_radius=6)
        pygame.draw.rect(surf, col, dial, 2, border_radius=6)
        text(surf, f"<   OFFSET {self.c.guess:02d}   >", dial.center, 18, WHITE, bold=True, anchor="center")
        text(surf, "LEFT/RIGHT tune   ENTER confirm   ESC exit", (box.centerx, box.bottom + 12), 13, GREY, anchor="midtop")
        if self.done_t is not None:
            text(surf, "MESSAGE RECOVERED", (W // 2, box.y - 44), 28, GREEN, bold=True, anchor="midtop")


# ============================================================================ reactor console
SYSTEMS = [
    ("life", "LIFE SUPPORT", "Off: no cooling for ECHO - battery drains 50% faster for the rest of the mission."),
    ("comms", "COMMUNICATIONS", "Off: the comms array stays dark - some crew messages can never be recovered."),
    ("security", "SECURITY", "Off: every security drone powers down - but security doors stay sealed."),
]


class ConsolePuzzle(Scene):
    overlay = True

    def __init__(self, game, gp, on_confirm):
        super().__init__(game)
        self.gp = gp
        f = gp.state.flags
        if "allocation_done" in f:
            self.on = {k: (f"{k}_on" in f) for k, _, _ in SYSTEMS}
        else:
            self.on = {"life": True, "comms": True, "security": False}
        self.sel = 0
        self.on_confirm = on_confirm
        self.t = 0.0
        self.msg = ""
        self.msg_t = 0.0

    def toggle(self, i):
        k = SYSTEMS[i][0]
        if self.on[k]:
            self.on[k] = False
        else:
            if sum(self.on.values()) >= 2:
                assets.play("error", 0.6)
                self.msg, self.msg_t = "Reactor can only feed two systems. Switch one off first.", 2.5
                return
            self.on[k] = True
        assets.play("rotate", 0.6)

    def handle_event(self, e):
        if e.type == pygame.KEYDOWN:
            if e.key == pygame.K_ESCAPE:
                self.close()
            elif e.key in (pygame.K_UP, pygame.K_w):
                self.sel = (self.sel - 1) % 3
                assets.play("select", 0.4)
            elif e.key in (pygame.K_DOWN, pygame.K_s):
                self.sel = (self.sel + 1) % 3
                assets.play("select", 0.4)
            elif e.key in (pygame.K_SPACE, pygame.K_e):
                self.toggle(self.sel)
            elif e.key in (pygame.K_1, pygame.K_2, pygame.K_3):
                self.sel = e.key - pygame.K_1
                self.toggle(self.sel)
            elif e.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                if sum(self.on.values()) != 2:
                    assets.play("error", 0.6)
                    self.msg, self.msg_t = "Route power to exactly two systems.", 2.5
                    return
                self.apply()

    def apply(self):
        st = self.gp.state
        for k, _, _ in SYSTEMS:
            st.flags.discard(f"{k}_on")
            st.flags.discard(f"{k}_off")
            st.flags.add(f"{k}_on" if self.on[k] else f"{k}_off")
        self.gp.set_flag("allocation_done")
        st.choices["allocation"] = [k for k in self.on if self.on[k]]
        assets.play("confirm", 0.9)
        self.gp.shake(3)
        self.close()
        self.on_confirm()

    def update(self, dt):
        self.t += dt
        self.msg_t = max(0.0, self.msg_t - dt)

    def draw(self, surf):
        dim(surf, 170)
        box = pygame.Rect(W // 2 - 360, H // 2 - 220, 720, 430)
        panel(surf, box, border=(255, 160, 90))
        text(surf, "REACTOR POWER ALLOCATION", (box.centerx, box.y + 18), 22, (255, 180, 110), bold=True, anchor="midtop")
        text(surf, "The damaged reactor can feed only TWO systems. This choice follows you.", (box.centerx, box.y + 52), 13, GREY, anchor="midtop")
        y = box.y + 90
        for i, (k, name, desc) in enumerate(SYSTEMS):
            r = pygame.Rect(box.x + 30, y, box.w - 60, 82)
            on = self.on[k]
            pygame.draw.rect(surf, (24, 30, 40) if i != self.sel else (40, 44, 56), r, border_radius=6)
            pygame.draw.rect(surf, (255, 180, 110) if i == self.sel else (70, 80, 96), r, 2, border_radius=6)
            sw = pygame.Rect(r.right - 92, r.y + 22, 70, 34)
            pygame.draw.rect(surf, (30, 160, 110) if on else (110, 40, 40), sw, border_radius=17)
            kx = sw.right - 19 if on else sw.x + 19
            pygame.draw.circle(surf, WHITE, (kx, sw.centery), 13)
            text(surf, f"{i + 1}  {name}", (r.x + 16, r.y + 12), 18, WHITE, bold=True)
            text(surf, "ONLINE" if on else "OFFLINE", (r.x + 16, r.y + 38), 13, GREEN if on else RED, bold=True)
            for j, ln in enumerate(wrap(desc, 12, r.w - 220)):
                text(surf, ln, (r.x + 110, r.y + 40 + j * 16), 12, GREY)
            y += 94
        text(surf, "UP/DOWN select   SPACE toggle   ENTER confirm   ESC back", (box.centerx, box.bottom - 30), 13, GREY, anchor="midtop")
        if self.msg_t > 0:
            text(surf, self.msg, (box.centerx, box.bottom + 12), 15, AMBER, anchor="midtop")
