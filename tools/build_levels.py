"""Level authoring script: builds data/levels.json from room/corridor descriptions.

Editing levels as code keeps maps consistent (walls, doors, windows) and lets the
validator check that every interactable is reachable.

    python tools/build_levels.py
"""
import json
import os
import random
from collections import deque

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "data", "levels.json")

SOLID = set("#W ~\"")


class Level:
    def __init__(self, lid, chapter, title, theme, w, h):
        self.d = dict(id=lid, chapter=chapter, title=title, theme=theme, music="ambient",
                      entities=[], objectives=[])
        self.w, self.h = w, h
        self.g = [[" "] * w for _ in range(h)]
        self.n = 0

    # --- geometry
    def room(self, x, y, w, h, floor="."):
        for yy in range(y, y + h):
            for xx in range(x, x + w):
                border = xx in (x, x + w - 1) or yy in (y, y + h - 1)
                if border:
                    if self.g[yy][xx] == " ":
                        self.g[yy][xx] = "#"
                else:
                    self.g[yy][xx] = floor

    def fill(self, x, y, w, h, ch):
        for yy in range(y, y + h):
            for xx in range(x, x + w):
                self.g[yy][xx] = ch

    def open(self, x, y, ch="."):
        self.g[y][x] = ch

    # --- entities
    def ent(self, etype, x, y, eid=None, **props):
        self.n += 1
        e = dict(type=etype, x=x, y=y, id=eid or f"{etype}{self.n}")
        e.update(props)
        self.d["entities"].append(e)
        if self.g[y][x] in SOLID:
            self.g[y][x] = "."
        return e

    def door(self, x, y, eid=None, **props):
        return self.ent("door", x, y, eid, **props)

    def objective(self, text, done, target=None):
        o = dict(text=text, done=done)
        if target:
            o["target"] = target if isinstance(target, list) else [target]
        self.d["objectives"].append(o)

    # --- output
    def windows(self, seed):
        rng = random.Random(seed)
        for y in range(1, self.h - 1):
            for x in range(self.w):
                if self.g[y][x] == "#" and self.g[y - 1][x] == " " and self.g[y + 1][x] not in SOLID:
                    if rng.random() < 0.45:
                        self.g[y][x] = "W"

    def build(self, start):
        self.d["start"] = list(start)
        self.windows(hash(self.d["id"]) & 0xff)
        self.d["map"] = ["".join(r) for r in self.g]
        validate(self)
        return self.d


def validate(lv):
    g = lv.g
    blocked = set()
    for e in lv.d["entities"]:
        if e["type"] in ("terminal", "panel", "switch", "console", "cipher", "crate", "barrel", "plant",
                         "transmitter", "core", "aicore", "holotable", "cryo"):
            for dx in range(e.get("w", 1)):
                for dy in range(e.get("h", 1)):
                    blocked.add((e["x"] + dx, e["y"] + dy))
    sx, sy = lv.d["start"]
    seen = {(sx, sy)}
    q = deque([(sx, sy)])
    while q:
        x, y = q.popleft()
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nx, ny = x + dx, y + dy
            if 0 <= nx < lv.w and 0 <= ny < lv.h and (nx, ny) not in seen:
                if g[ny][nx] not in SOLID and (nx, ny) not in blocked:
                    seen.add((nx, ny))
                    q.append((nx, ny))
    bad = []
    for e in lv.d["entities"]:
        if e["type"] in ("lamp", "decor", "hazard", "trigger", "pipe", "light", "sparks"):
            continue
        if e["type"] == "drone":
            for p in e["path"]:
                if tuple(p) not in seen:
                    bad.append(f"drone {e['id']} waypoint {p}")
            continue
        ok = (e["x"], e["y"]) in seen or any(
            (e["x"] + dx, e["y"] + dy) in seen for dx in range(-1, e.get("w", 1) + 1) for dy in range(-1, e.get("h", 1) + 1))
        if not ok:
            bad.append(f"{e['type']} {e['id']} at {e['x']},{e['y']}")
    if bad:
        print(f"[{lv.d['id']}] UNREACHABLE:", *bad, sep="\n  ")
    else:
        print(f"[{lv.d['id']}] ok, {len(seen)} reachable tiles, {len(lv.d['entities'])} entities")
    for row in lv.d["map"]:
        print("   ", row)


def path(*pts):
    """Manhattan path through waypoints (x first, then y) as a list of cells."""
    cells = [list(pts[0])]
    for (x1, y1) in pts[1:]:
        x0, y0 = cells[-1]
        while x0 != x1:
            x0 += 1 if x1 > x0 else -1
            cells.append([x0, y0])
        while y0 != y1:
            y0 += 1 if y1 > y0 else -1
            cells.append([x0, y0])
    return cells


def puzzle(w, h, source, *paths, broken=None, decoys=0.5, seed=1):
    return dict(w=w, h=h, source=list(source), paths=list(paths), broken=broken or [], decoys=decoys, seed=seed)


# =========================================================================== CHAPTER 1
def chapter1():
    L = Level("ch1", 1, "The Awakening", "maint", 44, 18)
    L.d["intro"] = "ch1_intro"
    L.room(1, 1, 9, 7)                 # dock bay
    L.room(9, 3, 24, 4)                # corridor (interior y4..5)
    L.room(9, 6, 14, 10)               # storage
    L.room(22, 6, 11, 8)               # power room
    L.room(24, 0, 7, 4)                # alcove
    L.open(27, 3)
    L.room(32, 2, 11, 8)               # elevator hall
    for x in range(10, 32, 3):
        L.open(x, 5, ":")
    L.fill(35, 5, 6, 1, ":")

    L.ent("dock", 4, 4, "dock1")
    L.ent("lamp", 5, 2, color=[120, 200, 255], radius=150)
    L.ent("crate", 2, 2)
    L.ent("barrel", 8, 6)
    L.ent("trigger", 3, 3, "t_move", w=5, h=3, dialogue="ch1_tut_move")
    L.door(9, 4, "d_bay")
    L.ent("pickup", 13, 5, "b1", item="battery")
    L.ent("terminal", 19, 4, "t_halcyon", dialogue="ch1_halcyon")
    L.ent("trigger", 15, 4, "t_scan", w=2, h=2, dialogue="ch1_tut_scan")

    # storage with first drone
    L.door(15, 6, "d_store")
    L.ent("trigger", 14, 7, "t_drone", w=3, h=1, dialogue="ch1_tut_drone")
    for (x, y) in ((13, 10), (14, 10), (17, 11), (18, 11), (11, 7), (20, 7)):
        L.ent("crate", x, y)
    L.ent("barrel", 12, 12)
    L.ent("drone", 11, 9, "dr1", path=[[11, 9], [20, 9], [20, 13], [11, 13]])
    L.ent("pickup", 21, 14, "key1", item="keycard_maint")
    L.ent("pickup", 10, 14, "b2", item="battery")

    # power room
    L.door(27, 6, "d_power", requires=["item:keycard_maint"], locked_msg="Access requires a MAINTENANCE keycard.")
    L.ent("lamp", 24, 8, color=[255, 220, 160], radius=170, flag="elevator_power")
    L.ent("lamp", 30, 8, color=[255, 220, 160], radius=170, flag="elevator_power")
    L.ent("pipe", 23, 10, vertical=True)
    L.ent("pipe", 23, 11, vertical=True)
    L.ent("panel", 27, 12, "p_elev", sets="elevator_power", dialogue_after="ch1_power_on",
          puzzle=puzzle(5, 4, (0, 1), path((0, 1), (2, 1), (2, 3), (4, 3)), seed=11))

    # alcove with damaged terminal (cipher)
    L.ent("cipher", 27, 1, "c_evac", text="EVACUATION ORDER ISSUED 14.03.2187 ALL CREW TO PODS",
          shift=7, sets="airlock_code", fragment="frag_evac", dialogue_after="ch1_evac_twist")
    L.ent("sparks", 27, 1)
    L.ent("pickup", 25, 1, "b3", item="battery")

    # airlock + elevator
    L.door(32, 4, "d_airlock", requires=["flag:airlock_code"],
           locked_msg="AIRLOCK SEALED. Override code required.", airlock=True)
    L.ent("lamp", 37, 3, color=[120, 200, 255], radius=160, flag="elevator_power")
    L.ent("exit", 40, 5, "exit1", requires=["flag:elevator_power"],
          locked_msg="Elevator has no power.", next="ch2", dialogue="ch1_outro")
    L.ent("trigger", 34, 4, "t_air", w=2, h=2, dialogue="ch1_airlock")

    L.objective("Leave the charging bay", "flag:opened:d_bay", "d_bay")
    L.objective("Find a maintenance keycard", "item:keycard_maint", "key1")
    L.objective("Restore power to the central elevator", "flag:elevator_power", "p_elev")
    L.objective("Recover the airlock override code", "flag:airlock_code", "c_evac")
    L.objective("Ride the central elevator", "flag:never", "exit1")
    return L.build((4, 4))


# =========================================================================== CHAPTER 2
def chapter2():
    L = Level("ch2", 2, "The Silent Garden", "garden", 48, 28)
    L.d["intro"] = "ch2_intro"
    L.room(1, 12, 8, 7)                # arrival lift
    L.room(8, 5, 22, 20, floor=";")    # atrium
    L.room(1, 19, 8, 8)                # storage
    L.room(14, 0, 8, 6)                # vent control
    L.room(29, 5, 12, 12)              # east wing (spores)
    L.room(29, 17, 14, 10, floor=";")  # greenhouse
    L.room(40, 7, 7, 6)                # exit lift
    # plant beds
    for by in (7, 12, 19):
        for bx in (11, 17, 23):
            L.fill(bx, by, 4, 3, '"')
    L.fill(9, 16, 20, 1, "~")
    for x in (12, 18, 24):
        L.open(x, 16, ",")
    L.fill(9, 6, 20, 1, ".")

    L.ent("dock", 3, 14, "dock2")
    L.ent("lamp", 4, 13, color=[140, 255, 190], radius=150)
    L.ent("exit", 2, 17, "lift_back", requires=["flag:never"], locked_msg="The lift will not go back up.")
    L.door(8, 15, "d_atrium")
    L.ent("trigger", 9, 14, "t_garden", w=1, h=3, dialogue="ch2_atrium")
    L.ent("terminal", 9, 6, "t_env", dialogue="ch2_envlog", fragment="frag_garden")
    L.ent("pickup", 28, 23, "b1", item="battery")
    L.ent("pickup", 9, 23, "b2", item="battery")
    for (x, y, k) in ((16, 11, 0), (22, 11, 1), (15, 22, 2), (27, 22, 0)):
        L.ent("plant", x, y, variant=k)
    L.ent("drone", 10, 10, "dr1", path=[[10, 10], [27, 10], [27, 11], [10, 11]])
    L.ent("drone", 27, 17, "dr2", path=[[27, 17], [10, 17], [10, 18], [27, 18]])
    for (x, y) in ((12, 6), (20, 22), (26, 6)):
        L.ent("lamp", x, y, color=[150, 255, 170], radius=130, flag="garden_power")

    # storage (component)
    L.door(8, 21, "d_store")
    L.ent("pickup", 3, 24, "comp1", item="component")
    L.ent("pickup", 6, 20, "b3", item="battery")
    L.ent("crate", 2, 20)
    L.ent("crate", 7, 25)
    L.ent("barrel", 2, 22)

    # vent control
    L.door(18, 5, "d_vent")
    L.ent("panel", 17, 1, "p_vent", sets="vents_on", dialogue_after="ch2_vents",
          puzzle=puzzle(5, 4, (0, 0), path((0, 0), (2, 0), (2, 2), (4, 2), (4, 3)), broken=[[2, 1]], seed=21))
    L.ent("lamp", 15, 2, color=[150, 255, 200], radius=120, flag="vents_on")

    # east wing with spores
    L.door(29, 9, "d_east")
    L.ent("hazard", 30, 6, "spores", w=10, h=10, drain=7.0, disabled_by="vents_on", kind="spores")
    L.ent("panel", 39, 6, "p_junction", sets="garden_power", dialogue_after="ch2_power",
          puzzle=puzzle(6, 4, (0, 3), path((0, 3), (1, 3), (1, 0), (3, 0), (3, 2), (5, 2)), seed=22))
    L.ent("switch", 34, 15, "s_irrig", requires=["flag:garden_power"], sets="irrigation_on",
          locked_msg="Irrigation pump has no power.", dialogue_after="ch2_irrigation")
    for (x, y) in ((31, 8), (36, 11), (32, 13)):
        L.ent("plant", x, y, variant=1)
    L.ent("pickup", 38, 13, "b4", item="battery")

    # greenhouse
    L.door(29, 21, "d_green", requires=["flag:irrigation_on"],
           locked_msg="Hydraulic seal. No irrigation pressure.")
    L.fill(31, 19, 3, 2, '"')
    L.fill(36, 19, 3, 2, '"')
    L.fill(31, 23, 3, 2, '"')
    L.fill(36, 23, 3, 2, '"')
    L.ent("drone", 30, 18, "dr3", path=[[30, 18], [40, 18], [40, 25], [30, 25]], pingpong=False)
    L.ent("pickup", 41, 22, "ckey", item="command_key")
    L.ent("lamp", 35, 22, color=[170, 255, 150], radius=160, flag="irrigation_on")

    # exit lift
    L.door(40, 9, "d_exit", requires=["item:command_key"], locked_msg="Command key required.")
    L.ent("exit", 44, 9, "exit2", next="ch3", dialogue="ch2_outro")

    L.objective("Find a way through the garden", "flag:opened:d_atrium", "d_atrium")
    L.objective("Restore power to the irrigation grid", "flag:garden_power", "p_junction")
    L.objective("Activate irrigation", "flag:irrigation_on", "s_irrig")
    L.objective("Recover the command key from the greenhouse", "item:command_key", "ckey")
    L.objective("Reach the reactor lift", "flag:never", "exit2")
    return L.build((4, 15))


# =========================================================================== CHAPTER 3
def chapter3():
    L = Level("ch3", 3, "The Reactor", "reactor", 46, 30)
    L.d["intro"] = "ch3_intro"
    L.d["heat"] = dict(start=30, rate=0.45, per_coolant=0.2, coolant=["coolant_a", "coolant_b", "coolant_c"],
                       stable_flag="reactor_stable", needs=["flag:allocation_done"])
    L.room(1, 1, 8, 7)                 # entry
    L.room(8, 3, 30, 6)                # corridor (y4..7)
    L.room(19, 0, 8, 4)                # console nook
    L.open(22, 3)
    L.open(23, 3)
    L.room(14, 8, 20, 14, floor=",")   # reactor chamber
    L.room(5, 11, 10, 7)               # pump A
    L.room(33, 11, 10, 7)              # pump B
    L.room(19, 21, 10, 7)              # pump C
    L.room(37, 3, 8, 6)                # exit
    for x in range(9, 37):
        L.open(x, 6, ":")

    L.ent("dock", 3, 5, "dock3")
    L.ent("lamp", 4, 2, color=[255, 170, 110], radius=150)
    L.door(8, 4, "d_entry")
    L.ent("console", 22, 1, "console", dialogue_after="ch3_console")
    L.ent("terminal", 25, 1, "t_ai", dialogue="ch3_ai", fragment="frag_reactor")
    L.door(23, 8, "d_chamber")
    L.ent("core", 22, 13, "core", w=3, h=3)
    L.ent("drone", 16, 10, "dr1", path=[[16, 10], [31, 10], [31, 19], [16, 19]], requires_off="security_off")
    L.ent("drone", 10, 5, "dr2", path=[[10, 5], [35, 5]], pingpong=True, requires_off="security_off")

    L.door(14, 14, "d_pa")
    L.ent("panel", 6, 14, "p_a", sets="coolant_a", dialogue_after="ch3_pump",
          puzzle=puzzle(6, 5, (0, 2), path((0, 2), (2, 2), (2, 0), (4, 0), (4, 4), (5, 4)), seed=31))
    L.ent("pickup", 12, 16, "b1", item="battery")
    L.ent("barrel", 7, 12)
    L.ent("lamp", 9, 12, color=[120, 200, 255], radius=130, flag="coolant_a")

    L.door(33, 14, "d_pb")
    L.ent("panel", 41, 14, "p_b", sets="coolant_b", dialogue_after="ch3_pump",
          puzzle=puzzle(6, 5, (0, 0), path((0, 0), (3, 0), (3, 4), (5, 4)), path((3, 2), (5, 2)), seed=32))
    L.ent("pickup", 35, 16, "b2", item="battery")
    L.ent("barrel", 40, 12)
    L.ent("lamp", 37, 12, color=[120, 200, 255], radius=130, flag="coolant_b")

    L.door(23, 21, "d_pc")
    L.ent("panel", 23, 26, "p_c", sets="coolant_c", dialogue_after="ch3_pump",
          puzzle=puzzle(6, 5, (0, 4), path((0, 4), (0, 1), (2, 1), (2, 3), (5, 3)), path((2, 1), (2, 0), (5, 0)), broken=[[2, 2]], seed=33))
    L.ent("pickup", 20, 22, "comp", item="component")
    L.ent("pickup", 27, 25, "b3", item="battery")
    L.ent("lamp", 21, 24, color=[120, 200, 255], radius=130, flag="coolant_c")

    L.door(37, 5, "d_exit", requires=["flag:reactor_stable"], locked_msg="Containment lock: reactor unstable.")
    L.ent("exit", 42, 5, "exit3", next="ch4", dialogue="ch3_outro")

    L.objective("Set the power allocation at the reactor console", "flag:allocation_done", "console")
    L.objective("Restart all three coolant pumps", "flag:coolant_all", ["p_a", "p_b", "p_c"])
    L.objective("Leave the reactor deck", "flag:never", "exit3")
    return L.build((4, 4))


# =========================================================================== CHAPTER 4
def chapter4():
    L = Level("ch4", 4, "The Truth", "command", 44, 30)
    L.d["intro"] = "ch4_intro"
    L.room(1, 12, 8, 7)                # lift
    L.room(8, 8, 20, 15)               # command hall
    L.room(12, 1, 10, 8)               # comms room
    L.room(12, 22, 10, 7)              # security office
    L.room(27, 6, 14, 19)              # AI core room
    for x in range(9, 27):
        L.open(x, 15, ":")

    L.ent("dock", 3, 14, "dock4")
    L.ent("lamp", 4, 13, color=[140, 190, 255], radius=150)
    L.door(8, 15, "d_hall")
    L.ent("holotable", 16, 13, "holo", w=2, h=2)
    for (x, y) in ((12, 9), (23, 9), (12, 21), (23, 21)):
        L.ent("lamp", x, y, color=[120, 170, 255], radius=150)
    for (x, y) in ((30, 8), (38, 20)):
        L.ent("lamp", x, y, color=[255, 110, 100], radius=150)
    L.ent("terminal", 10, 9, "t_rec1", dialogue="ch4_rec1", fragment="frag_rec1")
    L.ent("terminal", 25, 21, "t_rec2", dialogue="ch4_rec2", fragment="frag_rec2")
    L.ent("drone", 10, 11, "dr1", path=[[10, 11], [25, 11], [25, 19], [10, 19]], requires_off="security_off")
    L.ent("drone", 20, 9, "dr2", path=[[20, 9], [20, 21]], pingpong=True, requires_off="security_off")
    for (x, y) in ((11, 13), (23, 17)):
        L.ent("cryo", x, y)

    L.door(16, 8, "d_comms")
    L.ent("terminal", 16, 2, "t_rec3", dialogue="ch4_rec3", fragment="frag_rec3",
          requires=["flag:comms_on"], locked_dialogue="ch4_comms_off")
    L.ent("pickup", 20, 6, "b1", item="battery")
    L.ent("lamp", 14, 3, color=[140, 220, 255], radius=130, flag="comms_on")

    L.door(16, 22, "d_sec", requires=["flag:security_on"],
           locked_msg="Security office: biometric lock unpowered.")
    L.ent("terminal", 16, 27, "t_rec4", dialogue="ch4_rec4", fragment="frag_rec4")
    L.ent("pickup", 13, 23, "b2", item="battery")
    L.ent("pickup", 20, 23, "b3", item="battery")

    L.door(27, 15, "d_core")
    L.ent("aicore", 35, 10, "aicore", w=3, h=3)
    L.ent("terminal", 34, 16, "t_truth", dialogue="ch4_truth",
          requires=["frags:frag_rec1,frag_rec2,frag_rec3,frag_rec4>=2"], locked_dialogue="ch4_need_frags",
          choice="ai_fate")
    L.ent("pickup", 29, 23, "b4", item="battery")
    L.ent("exit", 39, 22, "exit4", requires=["flag:fate_chosen"], locked_msg="HALCYON will not release the uplink yet.",
          next="ch5", dialogue="ch4_outro")

    L.objective("Recover crew recordings (2 needed)", "frags:frag_rec1,frag_rec2,frag_rec3,frag_rec4>=2", ["t_rec1", "t_rec2", "t_rec3", "t_rec4"])
    L.objective("Reconstruct the truth at the AI core", "flag:fate_chosen", "t_truth")
    L.objective("Take the uplink lift", "flag:never", "exit4")
    return L.build((4, 15))


# =========================================================================== CHAPTER 5
def chapter5():
    L = Level("ch5", 5, "The Last Signal", "signal", 56, 22)
    L.d["intro"] = "ch5_intro"
    L.d["timer"] = 240
    L.d["music"] = "tension"
    L.room(1, 8, 7, 7)
    L.room(7, 9, 20, 5)
    L.room(26, 3, 8, 17)
    L.room(33, 3, 14, 5)
    L.room(33, 15, 14, 5)
    L.room(46, 3, 9, 17)
    for y in (10, 11, 12):
        L.open(26, y)
    L.open(33, 5)
    L.open(46, 5)
    L.open(33, 17)
    L.open(46, 17)
    for x in range(8, 26):
        L.open(x, 11, ":")

    L.ent("lamp", 3, 9, color=[255, 90, 80], radius=150, alarm=True)
    L.door(7, 11, "d_start")
    L.ent("pickup", 4, 13, "b0", item="battery")
    L.ent("drone", 12, 10, "dr1", path=[[12, 10], [12, 12]], pingpong=True)
    L.ent("drone", 19, 12, "dr2", path=[[19, 12], [19, 10]], pingpong=True)
    L.ent("pickup", 24, 10, "b1", item="battery")
    for (x, y) in ((9, 10), (16, 12), (22, 10)):
        L.ent("debris", x, y)
    L.ent("lamp", 16, 10, color=[255, 90, 80], radius=140, alarm=True)

    L.ent("lamp", 30, 6, color=[255, 90, 80], radius=150, alarm=True)
    L.ent("lamp", 30, 16, color=[255, 90, 80], radius=150, alarm=True)
    L.ent("drone", 28, 5, "dr3", path=[[28, 5], [31, 5], [31, 17], [28, 17]])
    L.ent("pickup", 27, 18, "b2", item="battery")

    # upper route: drones; lower route: fire hazard
    L.ent("drone", 36, 4, "dr4", path=[[36, 4], [44, 4], [44, 6], [36, 6]])
    L.ent("pickup", 40, 6, "b3", item="battery")
    L.ent("hazard", 34, 16, "fire", w=12, h=3, drain=9.0, kind="fire")

    L.ent("lamp", 50, 11, color=[255, 90, 80], radius=180, alarm=True)
    L.ent("panel", 50, 4, "p_ant", sets="antenna_aligned", dialogue_after="ch5_antenna",
          puzzle=puzzle(7, 5, (0, 2), path((0, 2), (2, 2), (2, 0), (4, 0), (4, 4), (6, 4)), path((4, 2), (6, 2)), seed=51))
    L.ent("transmitter", 51, 9, "dish", w=2, h=2)
    L.ent("pickup", 48, 18, "b4", item="battery")
    L.ent("terminal", 50, 15, "t_final", requires=["flag:antenna_aligned"], locked_dialogue="ch5_need_antenna",
          dialogue="ch5_final", choice="ending")

    L.objective("Reach the transmitter array before the reactor fails", "flag:opened:d_start", "d_start")
    L.objective("Align the antenna array", "flag:antenna_aligned", "p_ant")
    L.objective("Send the last signal", "flag:never", "t_final")
    return L.build((3, 11))


if __name__ == "__main__":
    levels = [chapter1(), chapter2(), chapter3(), chapter4(), chapter5()]
    with open(OUT, "w") as f:
        json.dump(levels, f, indent=1)
    print("wrote", OUT)
