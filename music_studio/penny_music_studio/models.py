"""Small, versioned symbolic project model. All event times are in quarter-note beats."""
from dataclasses import asdict, dataclass, field
import json
import math

SCHEMA = 1


def _finite(value: float) -> bool:
    return isinstance(value, (int, float)) and math.isfinite(value)


@dataclass
class Note:
    pitch: int
    start: float
    duration: float
    velocity: int = 90

    def validate(self) -> None:
        if not (isinstance(self.pitch, int) and 0 <= self.pitch <= 127):
            raise ValueError('MIDI pitch must be 0..127')
        if not (_finite(self.start) and self.start >= 0 and _finite(self.duration) and self.duration > 0):
            raise ValueError('Invalid note timing')
        if not (isinstance(self.velocity, int) and 1 <= self.velocity <= 127):
            raise ValueError('Velocity must be 1..127')


@dataclass
class Track:
    name: str
    instrument: str
    notes: list[Note] = field(default_factory=list)
    program: int = 0  # General MIDI zero-based program
    drums: bool = False
    volume: float = 0.75
    pan: float = 0.0  # -1..1
    mute: bool = False

    def validate(self) -> None:
        if not self.name.strip() or len(self.name) > 100:
            raise ValueError('Track name required (max 100 characters)')
        if not (0 <= self.program <= 127):
            raise ValueError('Invalid MIDI program')
        if not (_finite(self.volume) and 0 <= self.volume <= 1):
            raise ValueError('Track volume must be 0..1')
        if not (_finite(self.pan) and -1 <= self.pan <= 1):
            raise ValueError('Track pan must be -1..1')
        for note in self.notes:
            note.validate()


@dataclass
class Section:
    name: str
    start: float
    bars: int
    transpose: int = 0


@dataclass
class Song:
    title: str
    prompt: str
    bpm: int
    key: str
    seed: int
    tracks: list[Track]
    sections: list[Section]
    beats_per_bar: int = 4
    schema_version: int = SCHEMA
    provenance: str = 'PME procedural composition (no neural audio generation)'

    @property
    def duration_beats(self) -> float:
        return max([s.start + s.bars * self.beats_per_bar for s in self.sections] +
                   [n.start + n.duration for t in self.tracks for n in t.notes] + [0])

    @property
    def duration_seconds(self) -> float:
        return self.duration_beats * 60.0 / self.bpm

    def validate(self) -> None:
        if self.schema_version != SCHEMA:
            raise ValueError(f'Unsupported project schema: {self.schema_version}')
        if not self.title.strip() or len(self.title) > 200:
            raise ValueError('Title required (max 200 characters)')
        if not (40 <= self.bpm <= 240) or self.beats_per_bar != 4:
            raise ValueError('This version requires 4/4 at 40-240 BPM')
        if len(self.tracks) > 32 or len(self.sections) > 64:
            raise ValueError('Project exceeds MVP safety limits')
        if len(self.prompt) > 50000:
            raise ValueError('Prompt too long for project file')
        if not self.sections:
            raise ValueError('At least one section is required')
        for section in self.sections:
            if section.bars < 1 or not _finite(section.start) or section.start < 0:
                raise ValueError('Invalid section timing')
        for track in self.tracks:
            track.validate()
        if self.duration_seconds > 600:
            raise ValueError('MVP maximum duration is ten minutes')

    def to_json(self) -> str:
        self.validate()
        return json.dumps(asdict(self), indent=2, ensure_ascii=False)

    @classmethod
    def from_json(cls, text: str) -> 'Song':
        obj = json.loads(text)
        if obj.get('schema_version') != SCHEMA:
            raise ValueError('Unknown or unsupported project schema')
        tracks = [Track(**{**t, 'notes': [Note(**n) for n in t['notes']]}) for t in obj['tracks']]
        sections = [Section(**s) for s in obj['sections']]
        song = cls(**{**obj, 'tracks': tracks, 'sections': sections})
        song.validate()
        return song
