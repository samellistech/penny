"""Penny Music Studio: CPU-friendly procedural music composition and audio tools."""
from .composition import compose, interpret_prompt, limitations
from .models import Song, Track, Note, Section
from .engine import ProceduralCompositionBackend
__all__ = ['compose', 'interpret_prompt', 'limitations', 'Song', 'Track', 'Note', 'Section', 'ProceduralCompositionBackend']
__version__ = '0.1.0'
