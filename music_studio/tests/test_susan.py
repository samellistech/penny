"""SUSAN integration tests use original in-memory songs, never private audio."""
from __future__ import annotations

import importlib.util
from pathlib import Path
import tempfile
import threading
import unittest

from penny_music_studio.composition import interpret_prompt, compose
from penny_music_studio.midi import to_midi_bytes
from penny_music_studio.storage import load_project, save_project
from penny_music_studio.susan import SusanComposerBackend, check_susan, train_susan
from penny_music_studio.susan.sequence import REST, VOCAB, decode_note, song_steps

TORCH_AVAILABLE = importlib.util.find_spec('torch') is not None


class SusanEncodingTests(unittest.TestCase):
    def test_sequence_encoding_and_note_decode(self):
        req = interpret_prompt('emotional country rock guitar solo', key='G', bars_per_section=1, seed=9)
        original = compose(req)
        seq = song_steps(original)
        self.assertEqual(len(seq), len(original.sections) * 8)
        self.assertTrue(all(0 <= s.target < VOCAB and 0 <= s.previous < VOCAB for s in seq))
        self.assertIsNone(decode_note(REST, 'G', 0, minor=False))
        self.assertEqual(decode_note(0, 'G', 1.5, minor=False).start, 1.5)
        with self.assertRaises(ValueError):
            decode_note(99, 'G', 0, minor=False)

    def test_missing_optional_dependency_is_reported(self):
        result = check_susan()
        self.assertFalse(result['audio_generation'])
        self.assertFalse(result['checkpoint_available'])
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises((FileNotFoundError, RuntimeError)):
                SusanComposerBackend(Path(d)/'absent.pt', device='cpu').generate(
                    interpret_prompt('country ballad', bars_per_section=1))


@unittest.skipUnless(TORCH_AVAILABLE, 'Optional PyTorch is not installed')
class SusanNeuralTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.directory = tempfile.TemporaryDirectory()
        cls.checkpoint = Path(cls.directory.name) / 'model.pt'
        cls.info = train_susan(cls.checkpoint, examples=6, epochs=2, seed=17,
                               hidden_size=16, device='cpu')

    @classmethod
    def tearDownClass(cls):
        cls.directory.cleanup()

    def test_checkpoint_metadata_and_no_overwrite(self):
        self.assertTrue(self.checkpoint.is_file())
        self.assertEqual(self.info['data_source'], 'original in-memory procedural songs')
        with self.assertRaises(FileExistsError):
            train_susan(self.checkpoint, examples=4, epochs=1, hidden_size=16)

    def test_trained_neural_melody_is_reproducible_and_exportable(self):
        req = interpret_prompt('cinematic country rock guitar solo dramatic final chorus',
                               key='F#', bars_per_section=1, seed=192, title='Susan Test')
        backend = SusanComposerBackend(self.checkpoint, device='cpu')
        a = backend.generate(req)
        b = backend.generate(req)
        self.assertEqual(a.to_json(), b.to_json())
        self.assertIn('symbolic', a.provenance)
        self.assertIn('no neural audio', a.provenance)
        lead = next(t for t in a.tracks if t.instrument == 'lead')
        self.assertGreater(len(lead.notes), 0)
        self.assertNotEqual(lead.notes, next(t for t in compose(req).tracks if t.instrument == 'lead').notes)
        self.assertTrue(to_midi_bytes(a).startswith(b'MThd'))
        with tempfile.TemporaryDirectory() as d:
            path = save_project(a, Path(d) / 'test.pennyjson')
            self.assertEqual(load_project(path).to_json(), a.to_json())

    def test_cancellation_and_no_partial_checkpoint(self):
        with tempfile.TemporaryDirectory() as d:
            target = Path(d) / 'cancelled.pt'
            event = threading.Event()
            event.set()
            with self.assertRaises(InterruptedError):
                train_susan(target, examples=4, epochs=1, hidden_size=16, cancel=event)
            self.assertFalse(target.exists())

    def test_rejects_invalid_checkpoint(self):
        with tempfile.TemporaryDirectory() as d:
            target = Path(d) / 'corrupt.pt'
            target.write_bytes(b'This is not a PyTorch model')
            with self.assertRaises(Exception):
                SusanComposerBackend(target, device='cpu').generate(
                    interpret_prompt('country', bars_per_section=1))


if __name__ == '__main__':
    unittest.main()
