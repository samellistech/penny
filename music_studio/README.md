# Penny Music Studio — portable Phase 1 package

A standalone, pure-Python, CPU-first extension for Penny. Generates reproducible procedural country/pop/rock song sketches as multitrack MIDI and synthesised stereo WAV. **Not a neural text-to-song or singing-voice generator.**

Run from the folder containing `penny_music_studio`:

```sh
python -m unittest discover -s tests -v
python -m penny_music_studio gui
python -m penny_music_studio create --prompt "country rock piano intro, guitar solo, dramatic final chorus key change" --bars 1 --out output
```

Documentation: [docs/MUSIC_STUDIO.md](docs/MUSIC_STUDIO.md). No dependencies needed for core CLI/synth. `tkinter` for UI; Windows `winsound` for playback; optional FFmpeg for MP3. These files are designed to be added, not to replace the private assistant.

> Integration status: this branch currently stages the documentation only. The full tested source is supplied in the Penny Music Studio Phase 1 ZIP attachment in the development conversation and must be reviewed and added before merging.
