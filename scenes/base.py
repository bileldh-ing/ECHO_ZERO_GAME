"""Scene base class. Scenes live on a stack; overlay scenes draw on top of the one below."""


class Scene:
    overlay = False

    def __init__(self, game):
        self.game = game

    def handle_event(self, e):
        pass

    def update(self, dt):
        pass

    def draw(self, surf):
        pass

    def on_enter(self):
        pass

    def close(self):
        self.game.remove(self)
