"""JSON save / load of the checkpoint snapshot."""
import json
import os

from settings import SAVE_PATH


def exists():
    return os.path.exists(SAVE_PATH)


def save(data):
    try:
        tmp = SAVE_PATH + ".tmp"
        with open(tmp, "w") as f:
            json.dump(data, f, indent=1)
        os.replace(tmp, SAVE_PATH)
        return True
    except OSError:
        return False


def load():
    try:
        with open(SAVE_PATH) as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


def delete():
    try:
        os.remove(SAVE_PATH)
    except OSError:
        pass
