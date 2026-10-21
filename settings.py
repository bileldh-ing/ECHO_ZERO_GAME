"""Global configuration for ECHO//ZERO."""
import os

ROOT = os.path.dirname(os.path.abspath(__file__))
ASSET_DIR = os.path.join(ROOT, "assets")
DATA_DIR = os.path.join(ROOT, "data")
SAVE_PATH = os.path.join(ROOT, "save.json")

TITLE = "ECHO//ZERO - The Last Signal"
W, H = 960, 640
TILE = 32
FPS = 60

# Player tuning (pixels / second)
WALK_SPEED = 125
SPRINT_SPEED = 195
ACCEL = 1400
FRICTION = 1600

# Battery tuning (% per second / per use)
BATTERY_MAX = 100.0
DRAIN_IDLE = 0.10          # core systems
DRAIN_LIGHT = 0.22         # flashlight on
DRAIN_SPRINT = 2.6
SCAN_COST = 6.0
DOOR_COST = 0.0
CELL_RESTORE = 35.0
DOCK_RATE = 22.0

# Drone tuning
DRONE_PATROL_SPEED = 58
DRONE_CHASE_SPEED = 128
DRONE_VIEW = 150
DRONE_VIEW_LIT = 235
DRONE_FOV = 36             # half angle, degrees
DRONE_ZAP = 18.0

# Colours
CYAN = (90, 210, 255)
CYAN_DIM = (40, 110, 150)
WHITE = (235, 242, 250)
GREY = (140, 150, 165)
DARK = (8, 10, 16)
RED = (255, 70, 60)
AMBER = (255, 180, 60)
GREEN = (110, 240, 150)
PANEL_BG = (10, 16, 26)

SPEAKER_COLORS = {
    "ECHO": CYAN,
    "HALCYON": (255, 95, 80),
    "LOG": (200, 200, 140),
    "CREW": (170, 220, 170),
    "SYSTEM": (160, 170, 190),
    "DR. VOSS": (180, 200, 255),
    "CMDR. OKAFOR": (255, 210, 150),
}

# Per chapter theme: ambient light colour multiplied over the scene.
THEMES = {
    "maint":   {"ambient": (46, 54, 72),  "accent": (70, 170, 230)},
    "garden":  {"ambient": (42, 62, 52),  "accent": (90, 220, 140)},
    "reactor": {"ambient": (70, 46, 38),  "accent": (255, 140, 60)},
    "command": {"ambient": (40, 48, 76),  "accent": (90, 190, 255)},
    "signal":  {"ambient": (66, 34, 40),  "accent": (255, 70, 70)},
}
