# Penny Music Studio — Phase 1 (procedural audio MVP)

## What this is

An independent, self-contained Python package intended for later integration into the private Penny desktop assistant. It does **not** download pretrained music models, call Suno or ACE-Step, or provide learned singing. Its compositions are deterministic procedural sketches. All audio sounds are synthesised approximations; a `choir_pad` is an **instrument**, not vocals. The generated MIDI can be imported into a DAW for better instruments and editing.

### Architecture / adapter boundaries

- `composition.py`: explicit keyword-to-request parser, deterministic note/section arranger. No LLM required. `limitations()` reports common unimplemented features.
- `models.py`: JSON schema v1; beat-timed notes, MIDI program, sections, editable per-track volume/pan/mute.
- `engine.py`: `CompositionBackend` protocol and CPU procedural implementation; neural audio is explicitly unavailable.
- `midi.py`: built-in Standard MIDI File format 1 exporter (tempo, tracks, programs, note events, 4/4, drum channel).
- `renderer.py`: pure Python CPU oscillator, percussion approximation, note envelopes, volume/panning, single-tap delay + low-pass-style tonal filtering; stereo PCM16 WAV export; optional FFmpeg MP3.
- `storage.py`: safe atomic `.pennyjson` writes and validated reads.
- `jobs.py`: background render execution, error states, progress, cancellation.
- `hardware.py`: CPU backend discovery without importing Torch or assuming a GPU.
- `gui.py`: basic tkinter desktop window to compose, view tracks, edit mix controls, save/load, export MIDI/WAV, listen on Windows.
- `cli.py`: noninteractive programmatic interface.

**Integration point:** The private Penny command router can call `interpret_prompt(...)`, then `ProceduralCompositionBackend().generate(...)`, then submit `render_wav(...)` to `JobManager`. A future dashboard can use the same API and its own worker/event loop. **Do not wire Penny's request handler by guessing private API names; review actual `D:\penny` implementation first.** This package has no import-time side effects, credentials, DB writes, or auto-installed plugins. It leaves the public request-service component alone.

## Windows installation, isolation first

Tested here with a separate Linux Python environment, **not** installed or tested on the user's Windows 11 / GTX 960 system. All required Phase 1 Python modules are standard-library (`tkinter` requires a Python build with Tcl/Tk). Python **3.11+** recommended; the user's Python 3.14 should support the core source but must be checked locally.

1. Back up `D:\penny` or commit existing work. **Do not overwrite existing modules.**
2. Keep the whole studio in its own directory: `D:\penny\music_studio\` (from the GitHub feature branch or by extracting this ZIP into that folder). Do not overwrite private Penny folders. The directory should contain `penny_music_studio/`, `tests/`, `docs/` and `pyproject.toml`.
3. In PowerShell:

```powershell
cd D:\penny\music_studio
python --version
python -m unittest discover -s tests -v
python -m penny_music_studio hardware
python -m penny_music_studio gui
```

If the GUI reports `_tkinter` not found, install standard CPython with Tcl/Tk support. The GUI offers **Play WAV** on Windows after a render; it uses built-in `winsound` (not real-time synthesized instruments).

## Quick generate

```powershell
cd D:\penny\music_studio
python -m penny_music_studio create --prompt "An emotional country-rock love anthem with piano introduction, guitar solo, gospel choir and dramatic final chorus key change" --title "Sammy Demo Sketch" --key G --bpm 100 --bars 1 --out "D:\penny\Data\music\sammy-demo"
```

Output (files are created at the explicit output path):

- `project.pennyjson` — editable project with notes, song sections and track controls.
- `composition.mid` — Standard MIDI Format 1, editable in a DAW.
- `composition.wav` — stereo 16-bit synthesis preview.

Inspect and rerender after editing track parameters in `project.pennyjson` (make a backup; keep valid JSON):

```powershell
python -m penny_music_studio inspect "D:\penny\Data\music\sammy-demo\project.pennyjson"
python -m penny_music_studio render "D:\penny\Data\music\sammy-demo\project.pennyjson" --wav "D:\penny\Data\music\sammy-demo\remix.wav" --sample-rate 44100
```

Optional MP3 (requires *your own separately installed* FFmpeg build with libmp3lame):

```powershell
ffmpeg -version
python -m penny_music_studio mp3 "D:\penny\Data\music\sammy-demo\remix.wav" "D:\penny\Data\music\sammy-demo\remix.mp3"
```

The default WAV rate is 22050Hz to reduce CPU cost, with optional 44100Hz export. Current renderer holds PCM in memory, sets a ten-minute project length limit, and may be slow for complex arrangements at 44100Hz. Keep sections short initially (1–2 bars). No CUDA or neural model needed.

## Current limitations

- The interpreter is a **keyword-based parser**, not a language model. It supports key/BPM and selected arrangement tags but not arbitrary semantic requirements. English only.
- The generator produces diatonic progressions, simple motifs, conventional 4/4 patterns and rule-based transitions. The key change is a +2 semitone transposition in final chorus/outro when requested. No interactive piano roll, advanced chord voicings, live soundfont, pitch-bend, dynamic mastering, or lyrical alignment.
- The synth is original procedural code, but **does not** have authentic guitar, piano, drum or voice timbre. The `choir_pad` is instrumental. No singing voice is generated, cloned or trained.
- FX are simple global delay and low-pass-like filtering. A proper reverb and full per-track EQ remain future work.
- The desktop UI has volume/pan/mute editing, not yet a waveform/MIDI timeline. The GUI render button runs in a worker; playback uses Windows `winsound` only.
- Desktop integration into private Penny's speech, local-model, request router, dashboard, or memory is **not verified**. It requires separate review of the actual private code.
- MP3 functionality is conditional on availability of a compatible FFmpeg executable. No automatic downloader.

## Next milestones

**Phase 1B:** Inspect private command/router, add an opt-in `music.create` command adapter with confirmation, permission boundary, standard path policy and existing logging; add CI smoke on Windows and verify local Python 3.14 performance. Improve error handling and add a visual piano-roll track editor. Add bundled sample-free setup UX.

**Phase 2:** Harmonic grammar, genre-specific groove templates, editable chord chart, meaningful motifs/fills, true multitrack rendering with per-track FX, loops, stem export, SoundFont support via licensed SF2/FluidSynth (optional). Consider `mido` or `symusic` for richer MIDI editing, `music21` for theory. Isolate dependencies in extras.

**Phase 3:** Dataset licence provenance and reproducible audio model experiments. Benchmark lightweight symbolic transformers on CPU first; neural waveform/diffusion models likely require significantly more VRAM and RAM. Track model licences separately from code licences, with a real backend capability probe.

**Phase 4:** Authorised vocal dataset curation, explicit performer consent, isolated personalised voice model, pronunciation/phoneme and pitch conditioning, harmony/choir, source-stem training rights tracking, objective and subjective listening tests.

**Phase 5:** Standalone DAW editing and non-destructive multitrack timeline, plug-in host boundary, advanced synthesis, mixing, versioned projects, independent training/inference, audio continuation and inpainting.

## Licensing and publication boundary

This repository does not yet select a public licence. The new code does not grant third parties permission to reuse your private tracks. Keep lyrics, voice recordings, licensed audio samples, credentials and models out of the public GitHub repo. For each third-party dependency and music dataset, document code/model/data licences, commercial terms, provenance, permissions and applicable UK rights before training/distribution. Even permitted input material can generate outputs that still require clearance. A copyright-safe release is not guaranteed by procedural novelty or by the absence of platform restrictions.

## Verified tests in development environment

`python -m unittest discover -s tests -v` includes deterministic composition, key parsing, project persistence, version validation, real MIDI format structure and percussion channel, stereo WAV generation, silence/mute, render cancellation protection, async failure handling and FFmpeg-missing behaviour. The standard-library test suite runs without paid APIs or model downloads.
