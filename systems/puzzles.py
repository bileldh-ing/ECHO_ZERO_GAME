"""Puzzle logic (no rendering): power routing grid and terminal cipher."""
import random
from collections import deque

UP, RIGHT, DOWN, LEFT = 1, 2, 4, 8
DIRS = {UP: (0, -1), RIGHT: (1, 0), DOWN: (0, 1), LEFT: (-1, 0)}
OPP = {UP: DOWN, DOWN: UP, LEFT: RIGHT, RIGHT: LEFT}


def rot(mask, n=1):
    for _ in range(n % 4):
        mask = ((mask << 1) | (mask >> 3)) & 15
    return mask


class Cell:
    __slots__ = ("mask", "kind", "fixed")

    def __init__(self, mask, kind="pipe", fixed=False):
        self.mask, self.kind, self.fixed = mask, kind, fixed


class PowerGrid:
    """Rotate conduit tiles so current flows from the source to every target."""

    def __init__(self, spec):
        self.w, self.h = spec["w"], spec["h"]
        self.source = tuple(spec["source"])
        rng = random.Random(spec.get("seed", 1))
        masks = {}
        ends = []
        for p in spec["paths"]:
            cells = [tuple(c) for c in p]
            for a, b in zip(cells, cells[1:]):
                d = (b[0] - a[0], b[1] - a[1])
                for bit, v in DIRS.items():
                    if v == d:
                        masks[a] = masks.get(a, 0) | bit
                        masks[b] = masks.get(b, 0) | OPP[bit]
            ends.append(cells[-1])
        self.cells = {}
        for pos, m in masks.items():
            self.cells[pos] = Cell(m)
        self.cells[self.source].kind = "source"
        self.cells[self.source].fixed = True
        self.targets = []
        for e in ends:
            if e != self.source and bin(self.cells[e].mask).count("1") == 1:
                self.cells[e].kind = "target"
                self.cells[e].fixed = True
                self.targets.append(e)
        for b in spec.get("broken", []):
            b = tuple(b)
            if b in self.cells:
                self.cells[b].kind = "broken"
        for y in range(self.h):
            for x in range(self.w):
                if (x, y) not in self.cells and rng.random() < spec.get("decoys", 0.5):
                    self.cells[(x, y)] = Cell(rng.choice([5, 3, 3, 7]))
        # scramble
        for _ in range(20):
            for pos, c in self.cells.items():
                if not c.fixed:
                    c.mask = rot(c.mask, rng.randrange(4))
            if not self.solved():
                break

    def rotate(self, pos):
        c = self.cells.get(pos)
        if c and not c.fixed and c.kind != "broken":
            c.mask = rot(c.mask)
            return True
        return False

    def repair(self, pos):
        c = self.cells.get(pos)
        if c and c.kind == "broken":
            c.kind = "pipe"
            return True
        return False

    def powered(self):
        on = {self.source}
        q = deque([self.source])
        while q:
            x, y = q.popleft()
            c = self.cells[(x, y)]
            for bit, (dx, dy) in DIRS.items():
                if c.mask & bit:
                    n = (x + dx, y + dy)
                    nc = self.cells.get(n)
                    if nc and n not in on and nc.kind != "broken" and nc.mask & OPP[bit]:
                        on.add(n)
                        q.append(n)
        return on

    def solved(self):
        on = self.powered()
        return all(t in on for t in self.targets)


class Cipher:
    """Caesar-shifted terminal message; the player tunes the decode offset."""

    def __init__(self, plain, shift):
        self.plain = plain.upper()
        self.shift = shift % 26
        self.guess = 0
        self.cipher = self.encode(self.plain, self.shift)

    @staticmethod
    def encode(text, k):
        out = []
        for ch in text:
            if "A" <= ch <= "Z":
                out.append(chr((ord(ch) - 65 + k) % 26 + 65))
            else:
                out.append(ch)
        return "".join(out)

    def decoded(self):
        return self.encode(self.cipher, -self.guess)

    def nudge(self, d):
        self.guess = (self.guess + d) % 26

    def solved(self):
        return self.guess == self.shift
