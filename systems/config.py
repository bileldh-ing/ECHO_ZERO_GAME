"""User preferences (volume, effects) persisted to config.json."""
import json
import os

from settings import ROOT

PATH = os.path.join(ROOT, "config.json")
DEFAULTS = {"music": 0.55, "sfx": 0.7, "shake": True, "scanlines": True, "minimap": True}
values = dict(DEFAULTS)


def load():
    try:
        with open(PATH) as f:
            values.update({k: v for k, v in json.load(f).items() if k in DEFAULTS})
    except (OSError, ValueError):
        pass
    apply()


def save():
    try:
        with open(PATH, "w") as f:
            json.dump(values, f, indent=1)
    except OSError:
        pass
    apply()


def apply():
    from systems import assets
    assets.sfx_volume = values["sfx"]
    assets.music_volume = values["music"]
    if assets.audio_ok:
        import pygame
        pygame.mixer.music.set_volume(values["music"])


def get(k):
    return values.get(k, DEFAULTS.get(k))
