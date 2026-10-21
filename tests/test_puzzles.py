"""Unit tests for puzzle logic and game state requirements (pytest or plain python)."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from systems.puzzles import PowerGrid, Cipher, rot  # noqa: E402
from systems.state import GameState  # noqa: E402


def test_rotation_cycles():
    for m in range(16):
        assert rot(m, 4) == m
    assert rot(1) == 2 and rot(8) == 1


def test_grid_scrambled_then_solvable():
    spec = dict(w=5, h=4, source=[0, 1], paths=[[[0, 1], [1, 1], [2, 1], [2, 2], [2, 3], [3, 3], [4, 3]]], seed=3)
    g = PowerGrid(spec)
    assert not g.solved()
    # brute force: rotate every free path cell until solved (small grid)
    cells = [p for p, c in g.cells.items() if not c.fixed]
    import itertools
    path = {tuple(c) for c in spec["paths"][0]}
    free = [p for p in cells if p in path]
    for combo in itertools.product(range(4), repeat=len(free)):
        for p, n in zip(free, combo):
            g.cells[p].mask = rot(g.cells[p].mask, n)
        if g.solved():
            break
        for p, n in zip(free, combo):
            g.cells[p].mask = rot(g.cells[p].mask, 4 - n)
    assert g.solved()


def test_broken_cell_blocks_power():
    spec = dict(w=3, h=1, source=[0, 0], paths=[[[0, 0], [1, 0], [2, 0]]], broken=[[1, 0]], decoys=0, seed=1)
    g = PowerGrid(spec)
    g.cells[(1, 0)].mask = 10
    assert not g.solved()
    assert g.repair((1, 0))
    assert g.solved()


def test_cipher():
    c = Cipher("HELLO WORLD", 7)
    assert c.cipher != "HELLO WORLD"
    c.guess = 7
    assert c.solved() and c.decoded() == "HELLO WORLD"


def test_requirements():
    s = GameState()
    assert not s.check(["item:keycard_maint"])[0]
    s.inv.add("keycard_maint")
    s.flags.add("x")
    assert s.check(["item:keycard_maint", "flag:x", "!flag:y"])[0]
    s.fragments = ["frag_rec1"]
    assert not s.check(["frags:frag_rec1,frag_rec2>=2"])[0]
    s.fragments.append("frag_rec2")
    assert s.check(["frags:frag_rec1,frag_rec2>=2"])[0]
    assert GameState.from_dict(s.to_dict()).to_dict() == s.to_dict()


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print("ok", name)
