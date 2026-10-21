"""Optional gamepad support: maps buttons to keyboard events and exposes the left stick."""
import pygame

sticks = []
BUTTON_KEYS = {0: pygame.K_e, 2: pygame.K_f, 3: pygame.K_q, 6: pygame.K_TAB, 7: pygame.K_ESCAPE}
DEAD = 0.25


def init():
    try:
        pygame.joystick.init()
        refresh()
    except Exception:
        pass


def refresh():
    sticks.clear()
    for i in range(pygame.joystick.get_count()):
        try:
            j = pygame.joystick.Joystick(i)
            j.init()
            sticks.append(j)
        except Exception:
            pass


def translate(e):
    """Turn a gamepad event into an equivalent KEYDOWN event (or None)."""
    if e.type in (pygame.JOYDEVICEADDED, pygame.JOYDEVICEREMOVED):
        refresh()
        return None
    if e.type == pygame.JOYBUTTONDOWN and e.button in BUTTON_KEYS:
        return pygame.event.Event(pygame.KEYDOWN, key=BUTTON_KEYS[e.button], mod=0, unicode="")
    if e.type == pygame.JOYHATMOTION:
        x, y = e.value
        k = {(-1, 0): pygame.K_LEFT, (1, 0): pygame.K_RIGHT, (0, 1): pygame.K_UP, (0, -1): pygame.K_DOWN}.get((x, y))
        if k:
            return pygame.event.Event(pygame.KEYDOWN, key=k, mod=0, unicode="")
    return None


def stick():
    for j in sticks:
        try:
            x, y = j.get_axis(0), j.get_axis(1)
        except Exception:
            continue
        if abs(x) > DEAD or abs(y) > DEAD:
            return x, y
    return 0.0, 0.0


def sprint_held():
    for j in sticks:
        try:
            if j.get_numbuttons() > 1 and j.get_button(1):
                return True
        except Exception:
            pass
    return False
