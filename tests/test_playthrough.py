"""Headless end-to-end playthrough: all five chapters, every puzzle, ending C and a death/reboot.

Run: python tests/test_playthrough.py   (screenshots land in docs/screenshots/)
"""
import os, sys, math
os.environ["SDL_VIDEODRIVER"] = "dummy"; os.environ["SDL_AUDIODRIVER"] = "dummy"
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import pygame
from main import Game
from systems.state import GameState
from systems import save_manager
from scenes.gameplay import Gameplay
from scenes.dialogue import Dialogue, Choice
from scenes.puzzle import PowerPuzzle, CipherPuzzle, ConsolePuzzle
from scenes.overlays import ChapterCard, SystemFailure
from scenes.ending import Ending
from systems.puzzles import DIRS, OPP, rot
from settings import TILE

SHOTS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "docs", "screenshots")
os.makedirs(SHOTS, exist_ok=True)
g = Game()
shots = 0


def key(k):
    return pygame.event.Event(pygame.KEYDOWN, key=k, mod=0, unicode="")


def step(n=1, events=None):
    for i in range(n):
        g.step(1 / 60, events if (events and i == 0) else [])
        g.render()


def settle(choice=None, max_frames=3000):
    """Skip dialogue / cards, finish transitions; pick choice key if a Choice appears."""
    for _ in range(max_frames):
        top = g.top
        if g.fade_cb is not None or g.fade > 0:
            step(1); continue
        if isinstance(top, Dialogue):
            top.handle_event(key(pygame.K_ESCAPE)); step(1); continue
        if isinstance(top, ChapterCard):
            top.handle_event(key(pygame.K_SPACE)); step(30); continue
        if isinstance(top, Choice) and choice:
            for i, o in enumerate(top.options):
                if o["key"] == choice:
                    top.sel = i
            top.handle_event(key(pygame.K_RETURN)); step(1); continue
        break
    return g.top


def gp():
    for s in reversed(g.scenes):
        if isinstance(s, Gameplay):
            return s


def tp(x, y):
    p = gp().player
    p.x, p.y = (x + 0.5) * TILE, (y + 0.5) * TILE + 4
    p.vx = p.vy = 0


def ent(eid):
    for e in gp().entities:
        if e.id == eid:
            return e
    raise KeyError(eid)


def near(eid, dx=0, dy=1):
    e = ent(eid)
    tp(e.tx + dx, e.ty + dy)
    step(2)


def interact(eid, dx=0, dy=1):
    near(eid, dx, dy)
    s = gp()
    assert s.target is not None, f"no target near {eid}"
    s.target.interact()
    step(1)


def solve_power():
    top = g.top
    assert isinstance(top, PowerPuzzle), top
    grid = top.grid
    spec_masks = {}
    # rebuild solution masks
    from systems.puzzles import PowerGrid
        # replicate path mask building
    masks = {}
    # find spec via scene attr
    for path in top._spec["paths"]:
        cells = [tuple(c) for c in path]
        for a, b in zip(cells, cells[1:]):
            d = (b[0] - a[0], b[1] - a[1])
            for bit, v in DIRS.items():
                if v == d:
                    masks[a] = masks.get(a, 0) | bit
                    masks[b] = masks.get(b, 0) | OPP[bit]
    last = None
    for pos, m in masks.items():
        c = grid.cells[pos]
        if c.kind == "broken":
            top.act(pos)   # uses component
            assert c.kind == "pipe", "repair failed (no component?)"
        if not c.fixed:
            c.mask = m
            last = pos
    c = grid.cells[last]
    c.mask = rot(c.mask, 3)
    top.act(last)
    assert top.done_t is not None, "puzzle not solved"
    step(90)


def solve_cipher():
    top = g.top
    assert isinstance(top, CipherPuzzle)
    top.c.guess = (top.c.shift - 1) % 26
    top.handle_event(key(pygame.K_RIGHT))
    top.handle_event(key(pygame.K_RETURN))
    step(90)


def shot(name):
    pygame.image.save(g.screen, os.path.join(SHOTS, f"{name}.png"))


# patch PowerPuzzle to keep spec
_orig = PowerPuzzle.__init__
def _init(self, game, spec, state, on_solved):
    self._spec = spec
    _orig(self, game, spec, state, on_solved)
PowerPuzzle.__init__ = _init

save_manager.delete()
st = GameState()
g.replace_all(Gameplay(g, st))
settle()
step(60)
shot("ch1_start")
s = gp(); F = s.state.flags
# ch1
tp(4, 6); step(5); settle()
tp(9, 5); step(20); settle()
assert "opened:d_bay" in F
near("key1", 0, 0); step(5); settle()
assert s.state.inv.has("keycard_maint")
interact("d_power", 0, -1); step(20); settle()
assert "opened:d_power" in F, "power door"
interact("p_elev", 0, -1); settle()
solve_power(); settle()
assert "elevator_power" in F
interact("c_evac", 0, 1); settle()
solve_cipher(); settle()
assert "airlock_code" in F and "frag_evac" in s.state.fragments
interact("d_airlock", -1, 0); step(20); settle()
assert "opened:d_airlock" in F
shot("ch1_end")
tp(40, 5); step(5); settle(); step(5); settle()
assert gp().level["id"] == "ch2", gp().level["id"]
print("ch1 OK")

# ch2
s = gp(); F = s.state.flags
settle(); step(30); shot("ch2_start")
near("comp1", 0, 0); step(3); settle()
interact("t_env", 1, 0); settle()
assert "frag_garden" in s.state.fragments
interact("p_vent", 0, 1); settle(); solve_power(); settle()
assert "vents_on" in F
interact("p_junction", 0, 1); settle(); solve_power(); settle()
assert "garden_power" in F
interact("s_irrig", 0, -1); settle()
assert "irrigation_on" in F
interact("d_green", 1, 0); step(20); settle()
near("ckey", 0, 0); step(3); settle()
assert s.state.inv.has("command_key")
interact("d_exit", -1, 0); step(20); settle()
shot("ch2_end")
tp(44, 9); step(5); settle(); step(5); settle()
assert gp().level["id"] == "ch3"
print("ch2 OK")

# ch3 - choose comms + security (life off) for full archive
s = gp(); F = s.state.flags
settle(); step(30); shot("ch3_start")
interact("console", 0, 1); top = g.top
assert isinstance(top, ConsolePuzzle)
top.on = {"life": False, "comms": True, "security": True}
top.handle_event(key(pygame.K_RETURN)); settle()
assert "allocation_done" in F and "life_off" in F
interact("t_ai", 0, 1); settle()
for pid, dx, dy in (("p_a", 1, 0), ("p_b", -1, 0), ("p_c", 0, -1)):
    if pid == "p_c":
        near("comp", 0, 0); step(3); settle()
    interact(pid, dx, dy); settle(); solve_power(); settle()
step(10); settle()
assert "reactor_stable" in F, F
shot("ch3_end")
tp(42, 5); step(30); settle()
tp(42, 5); step(5); settle(); step(5); settle()
assert gp().level["id"] == "ch4", gp().level["id"]
print("ch3 OK")

# ch4
s = gp(); F = s.state.flags
settle(); step(30); shot("ch4_start")
for tid, dx, dy in (("t_rec1", 0, 1), ("t_rec2", 0, -1), ("t_rec3", 0, 1)):
    interact(tid, dx, dy); settle()
interact("d_sec", 0, -1); step(20); settle()
interact("t_rec4", 0, -1); settle()
interact("t_truth", 0, 1); settle(choice="isolate")
assert "fate_chosen" in F
shot("ch4_end")
tp(39, 22); step(5); settle(); step(5); settle()
assert gp().level["id"] == "ch5"
print("ch4 OK")

# ch5
s = gp(); F = s.state.flags
settle(); step(60); shot("ch5_start")
interact("p_ant", 0, 1); settle(); solve_power(); settle()
interact("t_final", 0, -1); settle(choice="C")
step(200)
assert isinstance(g.top, Ending), g.top
step(60 * 12); shot("ending_mid")
step(60 * 14); shot("ending_end")
print("ch5 OK, ending", g.top.ending)

# death test
st = GameState(); st.level_id = "ch1"; st.battery = 0.05
g.replace_all(Gameplay(g, st, show_intro=False)); settle()
step(5); settle(); tp(12, 4); step(300)
assert isinstance(g.top, SystemFailure), g.top
shot("death")
g.top.handle_event(key(pygame.K_RETURN)); step(120)
assert isinstance(gp(), Gameplay) and gp().state.battery >= 40
print("death OK")
print("ALL OK")

save_manager.delete()
