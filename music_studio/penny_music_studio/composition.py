"""Deterministic, original rule-based arrangement generation (NOT a neural model)."""
from dataclasses import dataclass
import random
import re
from .models import Note, Section, Song, Track

KEYS = {'C':0, 'C#':1, 'DB':1, 'D':2, 'D#':3, 'EB':3, 'E':4, 'F':5,
        'F#':6, 'GB':6, 'G':7, 'G#':8, 'AB':8, 'A':9, 'A#':10, 'BB':10, 'B':11}
PROGRESSIONS = {
    'uplifting': [0, 4, 5, 3],  # I V vi IV
    'emotional': [5, 3, 0, 4],  # vi IV I V
    'anthem': [0, 5, 3, 4],
}
SCALE = [0, 2, 4, 5, 7, 9, 11]


@dataclass(frozen=True)
class MusicRequest:
    prompt: str
    bpm: int = 92
    key: str = 'G'
    seed: int = 42
    bars_per_section: int = 4
    title: str = 'Untitled Penny Composition'
    seconds_cap: int = 600


def interpret_prompt(prompt: str, *, bpm: int | None = None, key: str | None = None,
                     seed: int = 42, bars_per_section: int = 4,
                     title: str = 'Untitled Penny Composition') -> MusicRequest:
    """Explicit, transparent keyword interpreter. Unsupported features are reported separately."""
    if not isinstance(prompt, str) or not prompt.strip():
        raise ValueError('A music prompt is required')
    text = prompt.lower()
    tempo = re.search(r'\b(\d{2,3})\s*bpm\b', text)
    estimated = 74 if any(x in text for x in ('ballad', 'slow', 'intimate')) else 112 if 'rock' in text else 92
    chosen_bpm = bpm if bpm is not None else int(tempo.group(1)) if tempo else estimated
    key_match = re.search(r'\b(?:key of|in the key of)\s*([a-g](?:#|b)?)(?=\s|[.,!?]|$)', text, re.I)
    chosen_key = (key or (key_match.group(1) if key_match else 'G')).upper()
    if chosen_key not in KEYS:
        raise ValueError(f'Unsupported musical key: {chosen_key}')
    if not (40 <= chosen_bpm <= 240):
        raise ValueError('BPM must be 40..240')
    if not (1 <= bars_per_section <= 16):
        raise ValueError('Bars per section must be 1..16')
    return MusicRequest(prompt=prompt, bpm=chosen_bpm, key=chosen_key, seed=seed,
                        bars_per_section=bars_per_section, title=title)


def limitations(prompt: str) -> list[str]:
    s = prompt.lower()
    limitations_found = []
    if any(w in s for w in ('sing', 'vocal', 'lyrics', 'smoky voice', 'husky voice')):
        limitations_found.append('Expressive sung lead vocals and lyrics-to-singing are not implemented; instrumental melody only.')
    if any(w in s for w in ('choir', 'gospel')):
        limitations_found.append('Choir is a synthetic pad, not real singing or vocal harmonies.')
    if any(w in s for w in ('professional', 'master', 'radio-ready', 'suno')):
        limitations_found.append('This is a procedural demo mix, not studio-grade production or neural audio.')
    return limitations_found


def compose(request: MusicRequest) -> Song:
    """Generate independent editable instrument parts with reproducible random motifs."""
    rng = random.Random(request.seed)
    text = request.prompt.lower()
    root = 60 + KEYS[request.key]
    if root > 71:
        root -= 12
    is_minor = 'minor' in text or ('sad' in text and 'uplifting' not in text)
    degree_scale = [0, 2, 3, 5, 7, 8, 10] if is_minor else SCALE
    chord_quality = [0, 0, 1, 0, 0, 1, 1] if not is_minor else [1, 1, 0, 1, 1, 0, 0]
    progression = PROGRESSIONS['uplifting' if 'uplifting' in text else 'anthem' if 'anthem' in text else 'emotional']
    key_change = any(x in text for x in ('key change', 'modulation', 'dramatic final chorus'))
    piano_intro = any(x in text for x in ('piano intro', 'piano introduction', 'piano opening'))
    solo = any(x in text for x in ('solo', 'lead guitar'))
    strings = any(x in text for x in ('cinematic', 'strings', 'orchestral'))
    choir = any(x in text for x in ('gospel', 'choir', 'backing vocal'))
    names = ['Intro', 'Verse 1', 'Chorus', 'Verse 2', 'Chorus', 'Bridge']
    if solo:
        names.append('Guitar Solo')
    names += ['Final Chorus', 'Outro']
    sections = [Section(name, i * request.bars_per_section * 4, request.bars_per_section,
                        2 if key_change and name in ('Final Chorus', 'Outro') else 0)
                for i, name in enumerate(names)]
    tracks = {
        'piano': Track('Piano', 'piano', program=0, pan=-0.15),
        'acoustic': Track('Acoustic Guitar', 'acoustic_guitar', program=25, volume=0.65, pan=-0.45),
        'electric': Track('Electric Guitar', 'electric_guitar', program=29, pan=0.35),
        'bass': Track('Bass', 'bass', program=33, volume=0.85),
        'drums': Track('Drums', 'drums', program=0, drums=True, volume=0.78),
        'melody': Track('Lead Instrument (vocal guide)', 'lead', program=80, volume=0.8),
    }
    if strings:
        tracks['strings'] = Track('Strings', 'strings', program=48, volume=0.55, pan=0.2)
    if choir:
        tracks['choir'] = Track('Choir Pad (not vocals)', 'choir_pad', program=52, volume=0.48, pan=0.1)
    for section in sections:
        is_intro = section.name == 'Intro'
        is_outro = section.name == 'Outro'
        is_bridge = section.name == 'Bridge'
        is_chorus = 'Chorus' in section.name
        is_solo = section.name == 'Guitar Solo'
        energy = 1.0 if (is_chorus or is_solo) else 0.60 if is_bridge else 0.74
        for bar in range(section.bars):
            t = section.start + bar * 4
            idx = progression[bar % len(progression)]
            base = root + degree_scale[idx] + section.transpose
            chord = [base, base + (3 if chord_quality[idx] else 4), base + 7]
            if piano_intro or not is_intro:
                for beat, pitch in enumerate((chord[0], chord[1], chord[2], chord[1], chord[0], chord[2], chord[1], chord[2])):
                    tracks['piano'].notes.append(Note(min(127, pitch), t + beat * 0.5, 0.42, 55 if is_intro else 48))
            if not (is_intro and piano_intro) and not is_outro:
                for beat in (0, 1.5, 2, 3.5):
                    for p in chord:
                        tracks['acoustic'].notes.append(Note(p, t + beat, 0.25, 62))
                for beat in (0, 2, 2.5):
                    tracks['bass'].notes.append(Note(max(0, base - 24) if beat != 2.5 else max(0, base - 17),
                                                     t + beat, 0.75 if beat != 2.5 else 0.35, 82))
                if is_chorus or is_solo:
                    for beat in (0, 2):
                        for p in (base - 12, base - 5):
                            tracks['electric'].notes.append(Note(max(0, p), t + beat, 1.8, 85))
                # Standard GM percussion note numbers, one rhythmic instrument per note.
                for beat in (0, 2):
                    tracks['drums'].notes.append(Note(36, t + beat, 0.11, 95))
                for beat in (1, 3):
                    tracks['drums'].notes.append(Note(38, t + beat, 0.10, 90))
                for n in range(8):
                    tracks['drums'].notes.append(Note(42, t + n * 0.5, 0.08, 45 + int(20 * energy)))
                if bar == 0 and (is_chorus or is_solo):
                    tracks['drums'].notes.append(Note(49, t, 0.4, 92))
            if not is_intro and not is_outro and not is_solo:
                # Phrases tied to the current chord, with restrained melodic movement.
                tones = chord + [chord[0] + 12, chord[1] + 12]
                for beat in (0, 0.75, 1.5, 2.5, 3.25):
                    pitch = min(127, max(0, rng.choice(tones)))
                    tracks['melody'].notes.append(Note(pitch, t + beat, 0.58, 68 + rng.randint(0, 18)))
            if is_solo:
                for n in range(8):
                    pitch = base + rng.choice((0, 2, 4, 7, 9, 12))
                    tracks['melody'].notes.append(Note(min(127,pitch), t + n * .5, 0.38, 93))
            if strings and (is_chorus or is_bridge or is_outro):
                for p in chord:
                    tracks['strings'].notes.append(Note(p, t, 3.85, 62))
            if choir and (is_chorus or is_outro):
                for p in chord:
                    tracks['choir'].notes.append(Note(p, t, 3.80, 52))
    song = Song(title=request.title, prompt=request.prompt, bpm=request.bpm, key=request.key,
                seed=request.seed, sections=sections, tracks=list(tracks.values()))
    song.validate()
    return song
