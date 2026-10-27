"""Explicit opt-in SUSAN commands; importing the main Penny app never loads torch."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from ..composition import interpret_prompt, limitations
from ..midi import export_midi
from ..renderer import render_wav
from ..storage import save_project
from .composer import OptionalNeuralDependency, SusanComposerBackend, check_susan, train_susan


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog='python -m penny_music_studio.susan',
                                     description='SUSAN v0.1: CPU-first trainable SYMBOLIC music model')
    commands = parser.add_subparsers(dest='command', required=True)
    status = commands.add_parser('status', help='Report optional PyTorch and model availability')
    status.add_argument('--model', type=Path)

    train = commands.add_parser('train', help='Train a new symbolic GRU on in-memory synthetic sketches')
    train.add_argument('--model', type=Path, required=True)
    train.add_argument('--examples', type=int, default=40)
    train.add_argument('--epochs', type=int, default=4)
    train.add_argument('--seed', type=int, default=42)
    train.add_argument('--hidden-size', type=int, default=48)
    train.add_argument('--device', choices=('auto', 'cpu', 'cuda'), default='cpu')

    create = commands.add_parser('create', help='Generate a real editable song from trained symbolic weights')
    create.add_argument('--model', type=Path, required=True)
    create.add_argument('--prompt', required=True)
    create.add_argument('--title', default='SUSAN Original Sketch')
    create.add_argument('--bpm', type=int)
    create.add_argument('--key')
    create.add_argument('--bars', type=int, default=1)
    create.add_argument('--seed', type=int, default=42)
    create.add_argument('--temperature', type=float, default=.9)
    create.add_argument('--device', choices=('auto', 'cpu', 'cuda'), default='auto')
    create.add_argument('--out', type=Path, required=True)
    create.add_argument('--sample-rate', type=int, choices=(16000, 22050, 44100), default=22050)
    args = parser.parse_args(argv)
    try:
        if args.command == 'status':
            print(json.dumps(check_susan(args.model), indent=2))
        elif args.command == 'train':
            result = train_susan(args.model, examples=args.examples, epochs=args.epochs,
                                 seed=args.seed, device=args.device, hidden_size=args.hidden_size)
            print(json.dumps(result, indent=2))
        else:
            request = interpret_prompt(args.prompt, title=args.title, bpm=args.bpm,
                                       key=args.key, bars_per_section=args.bars, seed=args.seed)
            engine = SusanComposerBackend(args.model, device=args.device, temperature=args.temperature)
            song = engine.generate(request)
            target = args.out
            project = save_project(song, target / 'project.pennyjson')
            midi = export_midi(song, target / 'composition.mid')
            wav = render_wav(song, target / 'composition.wav', sample_rate=args.sample_rate)
            print(json.dumps({'project': str(project), 'midi': str(midi), 'wav': str(wav),
                              'tracks': len(song.tracks), 'seconds': round(song.duration_seconds, 1),
                              'provenance': song.provenance,
                              'limitations': limitations(args.prompt)}, indent=2))
        return 0
    except (ValueError, FileNotFoundError, FileExistsError, OptionalNeuralDependency) as exc:
        parser.exit(2, f'SUSAN: {exc}\n')


if __name__ == '__main__':
    raise SystemExit(main())
