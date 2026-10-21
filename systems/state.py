"""Persistent game state: flags, inventory, battery, story choices."""
import copy

from settings import BATTERY_MAX
from systems.inventory import Inventory, FRAGMENTS, ITEMS


class GameState:
    def __init__(self):
        self.level_id = "ch1"
        self.flags = set()
        self.inv = Inventory()
        self.battery = 34.0
        self.fragments = []
        self.choices = {}
        self.playtime = 0.0
        self.pos = None          # tile position to respawn at (None = level start)
        self.heat = None
        self.timer = None
        self.deaths = 0

    # ---------------------------------------------------------------- requirements
    def check_one(self, req):
        neg = req.startswith("!")
        if neg:
            req = req[1:]
        kind, _, arg = req.partition(":")
        if kind == "flag":
            ok = arg in self.flags
        elif kind == "item":
            ok = self.inv.has(arg)
        elif kind == "frags":
            names, _, n = arg.partition(">=")
            want = [x for x in names.split(",") if x]
            ok = sum(1 for f in want if f in self.fragments) >= int(n or len(want))
        elif kind == "fragcount":
            ok = len(self.fragments) >= int(arg)
        else:
            ok = True
        return ok != neg

    def check(self, reqs):
        for r in reqs or []:
            if not self.check_one(r):
                return False, r
        return True, None

    @staticmethod
    def describe(req):
        if not req:
            return ""
        kind, _, arg = req.lstrip("!").partition(":")
        if kind == "item":
            return f"Requires {ITEMS.get(arg, {'name': arg})['name']}."
        if kind == "frags":
            return "Requires more recovered data fragments."
        return "Access denied."

    # ---------------------------------------------------------------- helpers
    def add_fragment(self, fid):
        if fid and fid not in self.fragments and fid in FRAGMENTS:
            self.fragments.append(fid)
            return True
        return False

    def set_flag(self, f):
        self.flags.add(f)

    def battery_add(self, v):
        self.battery = max(0.0, min(BATTERY_MAX, self.battery + v))

    # ---------------------------------------------------------------- snapshot
    def to_dict(self):
        return dict(level_id=self.level_id, flags=sorted(self.flags), inv=self.inv.to_dict(),
                    battery=self.battery, fragments=list(self.fragments), choices=dict(self.choices),
                    playtime=self.playtime, pos=self.pos, heat=self.heat, timer=self.timer, deaths=self.deaths)

    @classmethod
    def from_dict(cls, d):
        s = cls()
        s.level_id = d.get("level_id", "ch1")
        s.flags = set(d.get("flags", []))
        s.inv = Inventory(d.get("inv", {}))
        s.battery = float(d.get("battery", 50))
        s.fragments = list(d.get("fragments", []))
        s.choices = dict(d.get("choices", {}))
        s.playtime = float(d.get("playtime", 0))
        s.pos = d.get("pos")
        s.heat = d.get("heat")
        s.timer = d.get("timer")
        s.deaths = int(d.get("deaths", 0))
        return s

    def clone(self):
        return GameState.from_dict(copy.deepcopy(self.to_dict()))
