# SUSAN: first trainable symbolic neural composer

**Status:** experimental v0.1, opt-in. The parent `music_studio/` procedural engine still works with no machine-learning packages installed. No private Penny code, vocals, third-party song recordings, AI checkpoints or web APIs are required.

## What is actually neural here?

SUSAN's independently defined **PyTorch GRU** predicts the next **symbolic melodic note or rest**. Inputs include the previous note, chord degree, half-beat position, song section and major/minor mode. It trains on synthetic melodies written by Penny Music Engine in memory. For inference it replaces the instrumental lead-guide notes in an ordinary `.pennyjson` song while retaining the original rhythm-section arrangement, MIDI exporter and procedural oscillator WAV renderer.

This **does not** generate waveforms using a neural model. No realistic singing, trained Sammy Ellis voice, real guitar performances, natural language understanding model, stem separation or neural mastering exists in SUSAN v0.1. The audio rendering sounds like the existing basic instrument synthesiser. Training loss is not proof of musical quality. Avoid attributing third-party work to SUSAN.

## Install on Windows 11 (isolated trial; do not overwrite private Penny)

Assuming this code lives in `D:\penny\music_studio`, first back up `D:\penny` and verify the parent project is unchanged. **Do not copy the public GitHub repository over the existing private project.** PyTorch is **optional**, and the official supported wheels/versions change over time; check [the official install selector](https://pytorch.org/get-started/locally/). A supported Python 3.11–3.13 environment is a conservative starting point if a compatible PyTorch wheel is unavailable for your Python 3.14.

```powershell
cd D:\penny\music_studio
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
# Select the current official PyTorch CPU Windows pip command at pytorch.org before installing.
python -m unittest discover -s tests -v
python -m penny_music_studio.susan status
```

For a first small CPU-only training run (creates **new** local weights, never downloads pretrained weights):

```powershell
python -m penny_music_studio.susan train --device cpu --examples 12 --epochs 3 --model "D:\penny\Data\music\models\susan-symbolic-v01.pt"
python -m penny_music_studio.susan create --model "D:\penny\Data\music\models\susan-symbolic-v01.pt" --device cpu --prompt "an emotional country-rock anthem with guitar solo and a dramatic final chorus" --key G --bars 1 --out "D:\penny\Data\music\projects\susan-test"
```

Files produced: `project.pennyjson` (editable symbolic multitrack project), `composition.mid` (multitrack MIDI), and `composition.wav` (basic synthesis preview). Generation is reproducible given the same checkpoint, prompt/settings and seed. To compare with procedural Penny Music Engine, use `python -m penny_music_studio create` instead.

**Resource limits:** Start with `--device cpu` even on GTX 960 4GB; recent PyTorch CUDA wheels may not support this older GPU's compute capability. `--device auto` probes on deliberate SUSAN model activation, not at Penny startup, and falls back to CPU if the installed CUDA wheel lacks that architecture. When the RTX 3090 24GB arrives and compatible drivers/PyTorch are installed, try `--device auto`. The already-ordered 64GB RAM is helpful for model experiments but is not needed for this tiny GRU.

## Model safety, licences and reproducibility

- Synthetic corpus uses original procedural composition only: no scraped recordings, copyrighted lyrics or user vocal data.
- Torch checkpoint loading uses `weights_only=True`; nevertheless, **only load models from trusted sources**. Training refuses to overwrite an existing checkpoint, and cancelled training does not leave one behind.
- `.pt` models, `.pennyjson`, audio files and recordings are excluded from the repository. Personal music data belongs in `D:\penny\Data\music` or another locally controlled folder.
- The original research code may be published subject to repository licensing review. If commercial music is the goal, audit licences for any future audio backends, training data, soundfonts or performances independently.
- The public GitHub repo is an extraction and does not include the private assistant command router/dashboard. SUSAN is not integrated with voice or Gemma 4 yet. Add a private, opt-in adapter only after inspecting the real private implementation.

## Next stage

1. Evaluate quality against held-out *authorised* MIDI with pitch/rhythm measures and blind listening tests.
2. Improve rhythm modelling, multiple melodic instruments, chords, expressive MIDI controllers and interactive timeline editing.
3. Create a separate `NeuralAudioBackend` interface and benchmark research models, always checking model/data licences and honest capability reporting.
4. When appropriate, connect Gemma 4 through structured song-planning instructions; unload large GPU-resident models before neural audio inference.
5. Design consent-based vocal datasets and a separately gated singing-voice module.
