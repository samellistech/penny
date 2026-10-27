"""SUSAN v0.1: a real, optional PyTorch GRU symbolic melody composer.

Learns from original procedural sketches generated in memory. Does not generate
neural audio, imitate a singer, or use downloaded training data. Torch is loaded
only when specifically training or using SUSAN, not when opening Penny.
"""
from __future__ import annotations

import importlib.util
import os
from pathlib import Path
import random
import tempfile
from typing import Callable

from ..composition import MusicRequest, compose
from ..models import Song
from .sequence import REST, VOCAB, STEPS_PER_BAR, decode_note, minor_mode, song_steps

FORMAT_VERSION = 1
MODEL_VERSION = 'susan-symbolic-gru-v0.1'


class OptionalNeuralDependency(RuntimeError):
    """A requested optional neural feature cannot run in this environment."""


def _torch():
    if importlib.util.find_spec('torch') is None:
        raise OptionalNeuralDependency('SUSAN symbolic neural composer requires optional PyTorch. Install the CPU build into a separate Python environment.')
    import torch
    return torch


def choose_device(torch, requested: str = 'auto') -> str:
    """Avoid GTX 960/CUDA unsupported-architecture failures. Explicit CPU is safest."""
    if requested not in ('cpu', 'cuda', 'auto'):
        raise ValueError('Device must be cpu, cuda or auto')
    if requested == 'cpu':
        return 'cpu'
    supported = False
    if torch.cuda.is_available():
        try:
            major, minor = torch.cuda.get_device_capability(0)
            archs = set(torch.cuda.get_arch_list())
            supported = f'sm_{major}{minor}' in archs
        except (RuntimeError, AssertionError, AttributeError):
            supported = False
    if requested == 'cuda' and not supported:
        raise OptionalNeuralDependency('The installed PyTorch CUDA build does not support this GPU architecture. Use --device cpu.')
    return 'cuda' if supported else 'cpu'


def _model_class(torch, hidden_size: int):
    nn = torch.nn

    class TinyComposer(nn.Module):
        def __init__(self):
            super().__init__()
            self.previous = nn.Embedding(VOCAB, 16)
            self.chord = nn.Embedding(7, 8)
            self.beat = nn.Embedding(STEPS_PER_BAR, 6)
            self.section = nn.Embedding(6, 6)
            self.mode = nn.Embedding(2, 4)
            self.gru = nn.GRU(40, hidden_size, batch_first=True)
            self.head = nn.Linear(hidden_size, VOCAB)

        def forward(self, x, state=None):
            features = torch.cat([embedding(x[:, :, i]) for i, embedding in enumerate(
                (self.previous, self.chord, self.beat, self.section, self.mode))], dim=-1)
            out, state = self.gru(features, state)
            return self.head(out), state

    return TinyComposer


def _training_corpus(count: int, seed: int):
    from ..composition import interpret_prompt
    prompts = (
        'emotional country rock piano introduction guitar solo',
        'uplifting pop rock anthem cinematic strings',
        'sad minor rock ballad guitar solo gospel choir',
        'dramatic cinematic country rock key change',
    )
    keys = ('C', 'D', 'G', 'A', 'F', 'F#')
    rng = random.Random(seed)
    for _ in range(count):
        p = rng.choice(prompts)
        r = interpret_prompt(p, seed=rng.randrange(2**31), key=rng.choice(keys), bars_per_section=1)
        yield song_steps(compose(r))


def train_susan(checkpoint: str | Path, *, examples: int = 40, epochs: int = 4,
                seed: int = 42, device: str = 'cpu', hidden_size: int = 48,
                cancel=None, progress: Callable[[float], None] | None = None) -> dict:
    """Train a small symbolic neural network from original synthetic songs.

    Outputs a PyTorch weights-only-compatible checkpoint. Training never downloads
    datasets or models, nor does it overwrite an existing checkpoint.
    """
    if not 4 <= examples <= 10000 or not 1 <= epochs <= 500:
        raise ValueError('Expected examples=4..10000 and epochs=1..500')
    if not 16 <= hidden_size <= 256:
        raise ValueError('hidden_size must be 16..256')
    path = Path(checkpoint)
    if path.exists():
        raise FileExistsError(f'Checkpoint already exists: {path}')
    torch = _torch()
    dev = choose_device(torch, device)
    torch.manual_seed(seed)
    torch.set_num_threads(min(4, os.cpu_count() or 1))
    model = _model_class(torch, hidden_size)().to(dev)
    opt = torch.optim.AdamW(model.parameters(), lr=.004)
    loss_fn = torch.nn.CrossEntropyLoss()
    corpus = list(_training_corpus(examples, seed))
    done = 0
    final_loss = None
    try:
        model.train()
        for epoch in range(epochs):
            order = list(range(len(corpus)))
            random.Random(seed + epoch).shuffle(order)
            for idx in order:
                if cancel is not None and cancel.is_set():
                    raise InterruptedError('SUSAN training cancelled; no checkpoint was saved')
                rows = corpus[idx]
                inp = torch.tensor([[[s.previous, s.chord, s.beat, s.section, s.mode] for s in rows]],
                                   dtype=torch.long, device=dev)
                goal = torch.tensor([[s.target for s in rows]], dtype=torch.long, device=dev)
                opt.zero_grad(set_to_none=True)
                logits, _ = model(inp)
                loss = loss_fn(logits.reshape(-1, VOCAB), goal.reshape(-1))
                loss.backward()
                torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
                opt.step()
                final_loss = float(loss.detach().cpu())
                done += 1
                if progress is not None:
                    progress(done / (epochs * len(corpus)))
        path.parent.mkdir(parents=True, exist_ok=True)
        fd, temp_name = tempfile.mkstemp(prefix='.susan-', suffix='.pt', dir=path.parent)
        os.close(fd)
        try:
            torch.save({'version': FORMAT_VERSION, 'model': MODEL_VERSION,
                        'hidden_size': hidden_size, 'seed': seed,
                        'training_data': 'procedural-original-synthetic-only',
                        'state_dict': {k: v.cpu() for k, v in model.state_dict().items()}}, temp_name)
            if path.exists():
                raise FileExistsError(f'Checkpoint already exists: {path}')
            os.replace(temp_name, path)
        finally:
            if os.path.exists(temp_name):
                os.unlink(temp_name)
    finally:
        del model
    return {'checkpoint': str(path), 'model': MODEL_VERSION, 'device': dev,
            'training_examples': examples, 'epochs': epochs,
            'final_training_loss': round(final_loss, 4),
            'data_source': 'original in-memory procedural songs',
            'note': 'Training loss is not independent quality evaluation.'}


def _load_checkpoint(path: str | Path, *, device: str = 'auto'):
    torch = _torch()
    dev = choose_device(torch, device)
    checkpoint = Path(path)
    if not checkpoint.is_file():
        raise FileNotFoundError(f'SUSAN checkpoint not found: {checkpoint}. Run susan-train first.')
    # weights_only protects against arbitrary Python object deserialization in torch.load.
    raw = torch.load(checkpoint, map_location='cpu', weights_only=True)
    if not isinstance(raw, dict) or raw.get('version') != FORMAT_VERSION or raw.get('model') != MODEL_VERSION:
        raise ValueError('Unsupported or invalid SUSAN checkpoint version')
    hidden = raw.get('hidden_size')
    if type(hidden) is not int or not (16 <= hidden <= 256) or not isinstance(raw.get('state_dict'), dict):
        raise ValueError('Malformed SUSAN checkpoint')
    model = _model_class(torch, hidden)().to(dev)
    model.load_state_dict(raw['state_dict'], strict=True)
    model.eval()
    return torch, model, dev, raw


def check_susan(checkpoint: str | Path | None = None) -> dict:
    """Lightweight installation check; no GPU probing until model activation."""
    status = {'name': MODEL_VERSION, 'torch_installed': importlib.util.find_spec('torch') is not None,
              'checkpoint_available': bool(checkpoint and Path(checkpoint).is_file()),
              'audio_generation': False, 'trained_model_required': True}
    return status


class SusanComposerBackend:
    """Neural lead melody + existing Penny procedural rhythm section and WAV renderer."""
    name = MODEL_VERSION

    def __init__(self, checkpoint: str | Path, *, device: str = 'auto', temperature: float = .9):
        if not .1 <= temperature <= 2:
            raise ValueError('Temperature must be in .1..2')
        self.checkpoint = Path(checkpoint)
        self.device = device
        self.temperature = temperature

    def generate(self, request: MusicRequest) -> Song:
        torch, model, dev, _ = _load_checkpoint(self.checkpoint, device=self.device)
        song = compose(request)
        steps = song_steps(song)
        rng = torch.Generator(device='cpu').manual_seed(request.seed)
        previous = REST
        state = None
        lead = next(t for t in song.tracks if t.instrument == 'lead')
        lead.notes.clear()
        mode = minor_mode(song.prompt)
        with torch.inference_mode():
            for row in steps:
                data = torch.tensor([[[previous, row.chord, row.beat, row.section, row.mode]]],
                                    dtype=torch.long, device=dev)
                logits, state = model(data, state)
                probs = torch.softmax(logits[0, -1].cpu() / self.temperature, dim=-1)
                # Reduce the chance of an all-rest lead, but preserve rests as part of phrasing.
                if row.section not in (0, 5):
                    probs[REST] *= .45
                    probs /= probs.sum()
                token = int(torch.multinomial(probs, 1, generator=rng).item())
                if row.section in (0, 5):
                    token = REST
                elif row.beat == 0 and row.section == 2 and token == REST:
                    token = row.chord
                note = decode_note(token, song.key, row.start, minor=mode,
                                   transpose=row.transpose, velocity=90 if row.section == 2 else 77)
                if note is not None:
                    lead.notes.append(note)
                previous = token
        song.provenance = (f'{MODEL_VERSION}: trained neural symbolic lead melody from {self.checkpoint.name}; '
                           'procedural backing and oscillator WAV; no neural audio or singing')
        song.validate()
        return song
