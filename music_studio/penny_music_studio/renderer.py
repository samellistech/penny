"""Built-in pure-Python stereo synth. Preview-quality, not sampled/AI instruments."""
from array import array
from math import sin, pi
from pathlib import Path
import subprocess
import shutil
import sys
import wave
from typing import Callable
from .models import Song, Track

# Precompute one cycle for inexpensive note synthesis on machines without NumPy.
_TABLE_SIZE = 4096
_SINE = tuple(sin(2 * pi * i / _TABLE_SIZE) for i in range(_TABLE_SIZE))


class RenderCancelled(Exception):
    pass


def _waveform(phase: float, inst: str, sine: float) -> float:
    if inst == 'piano':
        return 0.72 * sine + 0.18 * _SINE[int(2 * phase) % _TABLE_SIZE] + 0.1 * _SINE[int(3 * phase) % _TABLE_SIZE]
    if inst == 'acoustic_guitar':
        return 0.60 * sine + 0.27 * (2 * phase / _TABLE_SIZE - 1) + 0.13 * _SINE[int(2 * phase) % _TABLE_SIZE]
    if inst == 'electric_guitar':
        return max(-0.7, min(0.7, 2 * phase / _TABLE_SIZE - 1)) / 0.7
    if inst == 'bass':
        return 0.8 * sine + 0.2 * (1 if phase < _TABLE_SIZE / 2 else -1)
    if inst == 'strings' or inst == 'choir_pad':
        return 0.8 * sine + 0.2 * _SINE[int(2 * phase) % _TABLE_SIZE]
    return sine


def _envelope(inst: str, elapsed: float, total: float) -> float:
    remaining = total - elapsed
    if remaining <= 0:
        return 0
    attack = min(1.0, elapsed / (0.08 if inst in ('strings', 'choir_pad') else 0.012))
    release = min(1.0, remaining / (0.24 if inst in ('strings', 'choir_pad') else 0.04))
    if inst == 'piano':
        decay = 1 / (1 + elapsed * 1.8)
    elif inst in ('acoustic_guitar', 'electric_guitar'):
        decay = 1 / (1 + elapsed * 1.5)
    else:
        decay = 1.0
    return attack * release * decay


def _percussion(note: int, seconds: float, sample_index: int) -> float:
    # Deterministic short timbral approximations of kick, snare, hi-hat and crash.
    # These are synthetic effects; no copyrighted sample assets bundled.
    if note == 36:  # kick
        return sin(2 * pi * (70 - 35 * min(seconds, 0.25)) * seconds) * max(0.0, 1 - seconds / .24)
    noise = (((sample_index * 1103515245 + 12345) >> 9) & 65535) / 32767.5 - 1
    if note == 38:
        return (noise * 0.75 + sin(2*pi*190*seconds)*0.25) * max(0, 1-seconds/.17)
    return noise * max(0, 1-seconds / (.5 if note == 49 else .08)) * 0.46


def _make_audio(song: Song, sample_rate: int = 22050, *, cancel=None,
                progress: Callable[[float], None] | None = None,
                delay: float = .10, tone: float = .85) -> tuple[array, array]:
    song.validate()
    if sample_rate not in (16000, 22050, 44100):
        raise ValueError('Supported rates: 16000, 22050, 44100')
    if not (0 <= delay <= .35 and 0 <= tone <= 1):
        raise ValueError('Delay must be 0..0.35; tone must be 0..1')
    frames = int(song.duration_seconds * sample_rate) + int(sample_rate * .6)
    if frames > 12_000_000:
        raise ValueError('Export too large for built-in memory renderer')
    left = array('f', [0]) * frames
    right = array('f', [0]) * frames
    total_notes = sum(len(t.notes) for t in song.tracks if not t.mute) or 1
    finished = 0
    for track in song.tracks:
        if track.mute:
            continue
        gain = .21 * track.volume
        # Constant-power stereo pan.
        gain_l = gain * ((1 - track.pan) * .5) ** .5
        gain_r = gain * ((1 + track.pan) * .5) ** .5
        for note in track.notes:
            if cancel is not None and cancel.is_set():
                raise RenderCancelled('Render cancelled')
            begin = round(note.start * 60 / song.bpm * sample_rate)
            count = round(note.duration * 60 / song.bpm * sample_rate)
            max_count = min(count, frames - begin)
            if begin < 0 or max_count <= 0:
                continue
            percussive = track.drums
            period_step = 440 * 2 ** ((note.pitch - 69) / 12) * _TABLE_SIZE / sample_rate if not percussive else 0
            phase = 0.0
            amp = note.velocity / 127.0
            for k in range(max_count):
                if k % 8192 == 0 and cancel is not None and cancel.is_set():
                    raise RenderCancelled('Render cancelled')
                sec = k / sample_rate
                if percussive:
                    value = _percussion(note.pitch, sec, begin + k) * amp
                else:
                    value = _waveform(phase, track.instrument, _SINE[int(phase) % _TABLE_SIZE])
                    value *= _envelope(track.instrument, sec, max_count / sample_rate) * amp
                    phase = (phase + period_step) % _TABLE_SIZE
                left[begin + k] += value * gain_l
                right[begin + k] += value * gain_r
            finished += 1
            if progress is not None and (finished % 30 == 0 or finished == total_notes):
                progress(min(.92, finished / total_notes * .92))
    # Single-tap stereo cross-delay and gentle one-pole filtering are intentionally basic.
    offset = int(sample_rate * .185)
    prev_l = prev_r = 0.0
    for i in range(frames):
        if i % 8192 == 0 and cancel is not None and cancel.is_set():
            raise RenderCancelled('Render cancelled')
        l, r = left[i], right[i]
        if delay and i >= offset:
            l += delay * right[i-offset]
            r += delay * left[i-offset]
        prev_l += tone * (l - prev_l)
        prev_r += tone * (r - prev_r)
        left[i], right[i] = prev_l, prev_r
    if progress:
        progress(.97)
    return left, right


def render_wav(song: Song, path: str | Path, sample_rate: int = 22050,
               *, cancel=None, progress=None, delay: float = .10, tone: float = .85) -> Path:
    """Render atomically; cancellation leaves no partial target or temporary file."""
    import tempfile
    import os
    target = Path(path)
    if target.suffix.lower() != '.wav':
        raise ValueError('WAV output must use .wav')
    left, right = _make_audio(song, sample_rate, cancel=cancel, progress=progress, delay=delay, tone=tone)
    peak = max(max((abs(x) for x in left), default=0), max((abs(x) for x in right), default=0), .00001)
    scale = min(1.0, 0.96 / peak)
    target.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_path = tempfile.mkstemp(prefix='.pme-', suffix='.wav', dir=target.parent)
    os.close(fd)
    try:
        with wave.open(temp_path, 'wb') as out:
            out.setnchannels(2)
            out.setsampwidth(2)
            out.setframerate(sample_rate)
            for start in range(0, len(left), 2048):
                if cancel is not None and cancel.is_set():
                    raise RenderCancelled('Render cancelled')
                pcm = array('h')
                for a, b in zip(left[start:start+2048], right[start:start+2048]):
                    pcm.append(max(-32768,min(32767,int(a*scale*32767))))
                    pcm.append(max(-32768,min(32767,int(b*scale*32767))))
                if sys.byteorder != 'little':
                    pcm.byteswap()
                out.writeframesraw(pcm.tobytes())
        os.replace(temp_path, target)
        if progress:
            progress(1.0)
    finally:
        if os.path.exists(temp_path):
            os.unlink(temp_path)
    return target


def convert_mp3(wav_path: str | Path, mp3_path: str | Path) -> Path:
    """Optional export via explicitly installed ffmpeg containing libmp3lame."""
    tool = shutil.which('ffmpeg')
    if not tool:
        raise RuntimeError('MP3 unavailable: install FFmpeg and add ffmpeg.exe to PATH')
    target = Path(mp3_path)
    if target.suffix.lower() != '.mp3':
        raise ValueError('Output must be .mp3')
    source = Path(wav_path)
    if not source.is_file():
        raise FileNotFoundError(source)
    target.parent.mkdir(parents=True, exist_ok=True)
    import tempfile
    temp = tempfile.NamedTemporaryFile(prefix='.pme-', suffix='.mp3', dir=target.parent, delete=False)
    tmp_path = Path(temp.name)
    temp.close()
    try:
        proc = subprocess.run([tool, '-nostdin', '-hide_banner', '-loglevel', 'error',
                               '-y', '-i', str(source), '-codec:a', 'libmp3lame',
                               '-qscale:a', '2', str(tmp_path)], capture_output=True, text=True, timeout=180)
        if proc.returncode != 0:
            raise RuntimeError(f'FFmpeg failed: {proc.stderr[-500:]}')
        tmp_path.replace(target)
    finally:
        tmp_path.unlink(missing_ok=True)
    return target
