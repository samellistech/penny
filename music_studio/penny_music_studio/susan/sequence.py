"""Deterministic, inspectable symbolic encoding for the SUSAN composer.

One token is produced per half-beat of the guide melody. Each token denotes
one of 15 diatonic pitches (two octaves) or silence. This is *not* waveform
encoding or neural audio generation.
"""
from __future__ import annotations

from dataclasses import dataclass
from ..composition import KEYS, PROGRESSIONS, SCALE
from ..models import Note, Song

REST = 15
VOCAB = 16
STEPS_PER_BAR = 8
MAJOR = tuple(SCALE)
MINOR = (0, 2, 3, 5, 7, 8, 10)
PROGRESSION = tuple(PROGRESSIONS['emotional'])


def minor_mode(prompt: str) -> bool:
    txt = prompt.lower()
    return 'minor' in txt or ('sad' in txt and 'uplifting' not in txt)


def section_type(name: str) -> int:
    text = name.lower()
    if 'solo' in text:
        return 4
    if 'chorus' in text:
        return 2
    if 'verse' in text:
        return 1
    if 'bridge' in text:
        return 3
    if 'outro' in text:
        return 5
    return 0


def chord_degree(song: Song, bar_in_section: int) -> int:
    text = song.prompt.lower()
    kind = 'uplifting' if 'uplifting' in text else 'anthem' if 'anthem' in text else 'emotional'
    return PROGRESSIONS[kind][bar_in_section % len(PROGRESSIONS[kind])]


def key_root(key: str) -> int:
    if key.upper() not in KEYS:
        raise ValueError(f'Unsupported musical key: {key}')
    return 60 + KEYS[key.upper()]


def scale_pitches(key: str, *, minor: bool, transpose: int = 0) -> tuple[int, ...]:
    root = key_root(key) + transpose
    offsets = MINOR if minor else MAJOR
    return tuple(root + offsets[i % 7] + 12 * (i // 7) for i in range(15))


@dataclass(frozen=True)
class Step:
    previous: int
    chord: int
    beat: int
    section: int
    mode: int
    target: int
    start: float
    transpose: int


def song_steps(song: Song) -> list[Step]:
    """Convert the procedural melody to supervised next-token training rows."""
    song.validate()
    lead = next((t for t in song.tracks if t.instrument == 'lead'), None)
    if lead is None:
        raise ValueError('SUSAN needs a guide melody track (instrument=lead)')
    minor = minor_mode(song.prompt)
    rows: list[Step] = []
    previous = REST
    notes = sorted(lead.notes, key=lambda x: x.start)
    for section in song.sections:
        pitches = scale_pitches(song.key, minor=minor, transpose=section.transpose)
        for bar in range(section.bars):
            chord = chord_degree(song, bar)
            for beat in range(STEPS_PER_BAR):
                start = section.start + bar * 4 + beat * .5
                # Nearest onset within 0.24 beats to quantise the procedural guide.
                candidates = [n for n in notes if abs(n.start - start) < .251]
                if not candidates:
                    target = REST
                else:
                    target = min(range(15), key=lambda i: abs(pitches[i] - candidates[0].pitch))
                rows.append(Step(previous, chord, beat, section_type(section.name),
                                 int(minor), target, start, section.transpose))
                previous = target
    return rows


def decode_note(token: int, key: str, start: float, *, minor: bool,
                transpose: int = 0, velocity: int = 86) -> Note | None:
    if token == REST:
        return None
    if not 0 <= token < REST:
        raise ValueError(f'Invalid SUSAN pitch token: {token}')
    pitch = scale_pitches(key, minor=minor, transpose=transpose)[token]
    return Note(pitch=pitch, start=start, duration=.42, velocity=velocity)
