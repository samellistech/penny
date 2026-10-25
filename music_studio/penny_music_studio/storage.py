"""Atomic JSON project saving to user-chosen paths."""
from pathlib import Path
import os
import tempfile
from .models import Song


def save_project(song: Song, path: str | Path) -> Path:
    target = Path(path)
    if target.suffix.lower() != '.pennyjson':
        raise ValueError('Projects must use .pennyjson')
    target.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_path = tempfile.mkstemp(prefix='.pme-', suffix='.tmp', dir=target.parent)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as out:
            out.write(song.to_json())
            out.flush()
            os.fsync(out.fileno())
        os.replace(temp_path, target)
    finally:
        if os.path.exists(temp_path):
            os.unlink(temp_path)
    return target


def load_project(path: str | Path) -> Song:
    return Song.from_json(Path(path).read_text(encoding='utf-8'))
