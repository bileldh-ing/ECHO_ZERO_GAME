"""Item definitions and the inventory container."""

ITEMS = {
    "battery":       {"name": "Energy Cell", "icon": "item_battery", "desc": "Restores 35% battery when collected."},
    "keycard_maint": {"name": "Maintenance Keycard", "icon": "item_keycard_maint", "desc": "Opens maintenance doors."},
    "component":     {"name": "Circuit Component", "icon": "item_component", "desc": "Repairs a broken conduit in a power puzzle."},
    "command_key":   {"name": "Command Key", "icon": "item_command_key", "desc": "Authorises the reactor lift."},
}

FRAGMENTS = {
    "frag_evac":    "Evacuation order (14.03.2187)",
    "frag_garden":  "Environmental log - shelter lockout",
    "frag_reactor": "HALCYON core dump",
    "frag_rec1":    "Recording - Dr. Voss",
    "frag_rec2":    "Recording - Cmdr. Okafor",
    "frag_rec3":    "Personal message - Mbeki",
    "frag_rec4":    "Security log 7731",
}
TOTAL_FRAGMENTS = len(FRAGMENTS)


class Inventory:
    def __init__(self, data=None):
        self.items = dict(data or {})

    def add(self, item, n=1):
        self.items[item] = self.items.get(item, 0) + n

    def has(self, item, n=1):
        return self.items.get(item, 0) >= n

    def take(self, item, n=1):
        if not self.has(item, n):
            return False
        self.items[item] -= n
        if self.items[item] <= 0:
            del self.items[item]
        return True

    def listing(self):
        return [(k, v, ITEMS.get(k, {"name": k, "icon": "item_component", "desc": ""})) for k, v in self.items.items()]

    def to_dict(self):
        return dict(self.items)
