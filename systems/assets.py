"""Asset loading with caching, plus a tolerant audio wrapper."""
import os
import pygame

from settings import ASSET_DIR

_images = {}
_sounds = {}
_fonts = {}
_scaled = {}
audio_ok = False
music_volume = 0.55
sfx_volume = 0.7
_current_music = None


def ensure_generated():
    marker = os.path.join(ASSET_DIR, "sprites", "echo_down_0.png")
    music = os.path.join(ASSET_DIR, "music", "ambient.wav")
    if not (os.path.exists(marker) and os.path.exists(music)):
        from tools.generate_assets import generate_all
        generate_all()


def init_audio():
    global audio_ok
    try:
        pygame.mixer.pre_init(22050, -16, 2, 512)
        pygame.mixer.init()
        pygame.mixer.set_num_channels(24)
        audio_ok = True
    except Exception:
        audio_ok = False


def image(name, folder="sprites"):
    key = (folder, name)
    if key not in _images:
        path = os.path.join(ASSET_DIR, folder, name + ".png")
        try:
            img = pygame.image.load(path)
            img = img.convert_alpha() if pygame.display.get_surface() else img
        except Exception:
            img = pygame.Surface((32, 32), pygame.SRCALPHA)
            img.fill((255, 0, 255, 160))
        _images[key] = img
    return _images[key]


def tile(theme, name):
    return image(name, os.path.join("tiles", theme))


def frames(prefix, count, folder="sprites"):
    return [image(f"{prefix}_{i}", folder) for i in range(count)]


def scaled(name, size, folder="sprites"):
    key = (folder, name, size)
    if key not in _scaled:
        _scaled[key] = pygame.transform.smoothscale(image(name, folder), size)
    return _scaled[key]


def font(size, bold=False):
    key = (size, bold)
    if key not in _fonts:
        fname = "DejaVuSansMono-Bold.ttf" if bold else "DejaVuSansMono.ttf"
        path = os.path.join(ASSET_DIR, "fonts", fname)
        try:
            _fonts[key] = pygame.font.Font(path, size)
        except Exception:
            _fonts[key] = pygame.font.SysFont("consolas,dejavusansmono,monospace", size, bold=bold)
    return _fonts[key]


def sound(name):
    if not audio_ok:
        return None
    if name not in _sounds:
        path = os.path.join(ASSET_DIR, "sounds", name + ".wav")
        try:
            _sounds[name] = pygame.mixer.Sound(path)
        except Exception:
            _sounds[name] = None
    return _sounds[name]


def play(name, volume=1.0):
    s = sound(name)
    if s is not None:
        s.set_volume(max(0.0, min(1.0, volume * sfx_volume)))
        s.play()


def play_music(name, fade=1200):
    global _current_music
    if not audio_ok or name == _current_music:
        return
    path = os.path.join(ASSET_DIR, "music", name + ".wav")
    try:
        pygame.mixer.music.fadeout(300)
        pygame.mixer.music.load(path)
        pygame.mixer.music.set_volume(music_volume)
        pygame.mixer.music.play(-1, fade_ms=fade)
        _current_music = name
    except Exception:
        pass


def stop_music(fade=800):
    global _current_music
    if audio_ok:
        pygame.mixer.music.fadeout(fade)
    _current_music = None
