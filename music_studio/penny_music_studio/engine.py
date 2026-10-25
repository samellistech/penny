"""Backend contract for independently swappable symbolic, synthesis and neural engines."""
from typing import Protocol
from .composition import MusicRequest, compose
from .models import Song


class CompositionBackend(Protocol):
    name: str
    def generate(self, request: MusicRequest) -> Song: ...


class ProceduralCompositionBackend:
    name = 'pme-procedural-v1'
    def generate(self, request: MusicRequest) -> Song:
        return compose(request)


class NeuralAudioUnavailable(RuntimeError):
    pass


def require_neural_backend() -> None:
    raise NeuralAudioUnavailable('No neural generation backend is installed or trained; only procedural audio is available.')
