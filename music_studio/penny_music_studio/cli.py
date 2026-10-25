"""Penny Music Studio CLI. No paid/cloud services or model downloads."""
import argparse
import json
from pathlib import Path
from .composition import interpret_prompt, limitations
from .engine import ProceduralCompositionBackend
from .hardware import detect_hardware
from .midi import export_midi
from .renderer import render_wav, convert_mp3
from .storage import load_project, save_project


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog='penny-music', description='Penny Music Engine (procedural v1)')
    sub = parser.add_subparsers(dest='command', required=True)
    create = sub.add_parser('create', help='Compose and export MIDI, WAV and JSON')
    create.add_argument('--prompt', required=True)
    create.add_argument('--title', default='Penny Original')
    create.add_argument('--bpm', type=int)
    create.add_argument('--key')
    create.add_argument('--bars', type=int, default=2, help='Bars per song section (1..16)')
    create.add_argument('--seed', type=int, default=42)
    create.add_argument('--out', type=Path, default=Path('penny_music_output'))
    create.add_argument('--sample-rate', type=int, choices=(16000, 22050, 44100), default=22050)
    info = sub.add_parser('inspect', help='Inspect an existing project')
    info.add_argument('project', type=Path)
    rerender = sub.add_parser('render', help='Render an existing project after edits')
    rerender.add_argument('project', type=Path)
    rerender.add_argument('--wav', type=Path, required=True)
    rerender.add_argument('--sample-rate', type=int, choices=(16000,22050,44100), default=22050)
    mp3 = sub.add_parser('mp3', help='Convert a WAV to MP3 using optional FFmpeg')
    mp3.add_argument('wav', type=Path)
    mp3.add_argument('output', type=Path)
    sub.add_parser('hardware', help='Show safe CPU backend status')
    sub.add_parser('gui', help='Start the Tkinter desktop interface')
    args = parser.parse_args(argv)
    if args.command == 'hardware':
        print(json.dumps(detect_hardware().describe(), indent=2))
    elif args.command == 'gui':
        from .gui import launch
        launch()
    elif args.command == 'create':
        request = interpret_prompt(args.prompt, bpm=args.bpm, key=args.key,
                                   seed=args.seed, bars_per_section=args.bars, title=args.title)
        song = ProceduralCompositionBackend().generate(request)
        base = args.out
        project = save_project(song, base / 'project.pennyjson')
        midi = export_midi(song, base / 'composition.mid')
        wav = render_wav(song, base / 'composition.wav', sample_rate=args.sample_rate)
        print(json.dumps({'project':str(project), 'midi':str(midi), 'wav':str(wav),
                          'duration_seconds': round(song.duration_seconds, 1),
                          'tracks':len(song.tracks), 'limitations':limitations(args.prompt)}, indent=2))
    elif args.command == 'inspect':
        song = load_project(args.project)
        print(json.dumps({'title':song.title, 'bpm':song.bpm, 'key':song.key,
                          'duration_seconds':song.duration_seconds,
                          'tracks':[{'name':t.name, 'notes':len(t.notes), 'volume':t.volume,
                                     'pan':t.pan, 'mute':t.mute} for t in song.tracks]}, indent=2))
    elif args.command == 'render':
        song = load_project(args.project)
        print(render_wav(song, args.wav, sample_rate=args.sample_rate))
    elif args.command == 'mp3':
        print(convert_mp3(args.wav, args.output))
    return 0
