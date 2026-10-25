"""Dependency-free Standard MIDI File (format 1) exporter."""
from pathlib import Path
import struct
from .models import Song

TPB = 480


def vlq(value: int) -> bytes:
    if value < 0:
        raise ValueError('Negative MIDI delta')
    result = [value & 0x7f]
    value >>= 7
    while value:
        result.insert(0, 0x80 | (value & 0x7f))
        value >>= 7
    return bytes(result)


def _chunk(events: list[tuple[int, int, bytes]]) -> bytes:
    result = bytearray()
    previous = 0
    for tick, _, payload in sorted(events, key=lambda e: (e[0], e[1])):
        result.extend(vlq(tick - previous))
        result.extend(payload)
        previous = tick
    result.extend(b'\x00\xff\x2f\x00')
    return b'MTrk' + struct.pack('>I', len(result)) + bytes(result)


def to_midi_bytes(song: Song) -> bytes:
    song.validate()
    tempo = round(60000000 / song.bpm)
    master = [(0, 0, b'\xff\x51\x03' + tempo.to_bytes(3, 'big')),
              (0, 1, b'\xff\x58\x04\x04\x02\x18\x08')]
    chunks = [_chunk(master)]
    channels = [c for c in range(16) if c != 9]
    melodic_index = 0
    for track in song.tracks:
        if track.drums:
            ch = 9
        else:
            ch = channels[melodic_index % len(channels)]
            melodic_index += 1
        name = track.name.encode('utf-8')[:120]
        events = [(0, 0, b'\xff\x03' + bytes([len(name)]) + name),
                  (0, 1, bytes([0xc0 | ch, track.program])),
                  (0, 2, bytes([0xb0 | ch, 7, int(track.volume * 127)])),
                  (0, 3, bytes([0xb0 | ch, 10, int(64 + track.pan * 63)]))]
        if not track.mute:
            for note in track.notes:
                start = round(note.start * TPB)
                end = max(start + 1, round((note.start + note.duration) * TPB))
                events.append((start, 6, bytes([0x90 | ch, note.pitch, note.velocity])))
                events.append((end, 4, bytes([0x80 | ch, note.pitch, 0])))
        chunks.append(_chunk(events))
    return b'MThd' + struct.pack('>IHHH', 6, 1, len(chunks), TPB) + b''.join(chunks)


def export_midi(song: Song, path: str | Path) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(to_midi_bytes(song))
    return path
