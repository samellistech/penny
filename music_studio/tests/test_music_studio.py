import json
from pathlib import Path
import tempfile
import threading
import unittest
import wave
from unittest.mock import patch

from penny_music_studio.composition import compose, interpret_prompt, limitations
from penny_music_studio.midi import to_midi_bytes, export_midi
from penny_music_studio.models import Note, Song, Track, Section
from penny_music_studio.renderer import RenderCancelled, render_wav, convert_mp3
from penny_music_studio.storage import save_project, load_project
from penny_music_studio.jobs import JobManager
from penny_music_studio.engine import NeuralAudioUnavailable, require_neural_backend


class StudioTests(unittest.TestCase):
    def setUp(self):
        self.request = interpret_prompt('emotional country rock piano introduction guitar solo gospel choir dramatic final chorus key change',
                                        bars_per_section=1, seed=113, title='Test Song')

    def test_determinism_and_independent_tracks(self):
        a, b = compose(self.request), compose(self.request)
        self.assertEqual(a.to_json(), b.to_json())
        self.assertGreater(len(a.tracks), 5)
        self.assertTrue(any(t.drums for t in a.tracks))
        self.assertTrue(any(t.instrument == 'choir_pad' for t in a.tracks))
        self.assertTrue(any(s.transpose == 2 for s in a.sections))
        self.assertGreater(sum(len(t.notes) for t in a.tracks), 50)

    def test_tempos_and_keys(self):
        x = interpret_prompt('rock song at 124 bpm in the key of F#')
        self.assertEqual((x.bpm, x.key), (124, 'F#'))
        with self.assertRaises(ValueError):
            interpret_prompt('rock', bpm=900)
        with self.assertRaises(ValueError):
            interpret_prompt('rock', key='Q')

    def test_limitations_not_misrepresented(self):
        cautions = limitations('professional gospel choir singing lyrics')
        self.assertGreaterEqual(len(cautions), 3)
        with self.assertRaises(NeuralAudioUnavailable):
            require_neural_backend()

    def test_serialization_validation_and_persistence(self):
        song = compose(self.request)
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / 'track.pennyjson'
            save_project(song, path)
            new = load_project(path)
            self.assertEqual(song.to_json(), new.to_json())
            new.tracks[0].pan = .65
            save_project(new,path)
            self.assertEqual(load_project(path).tracks[0].pan, .65)
            bad = json.loads(path.read_text())
            bad['schema_version'] = 500
            with self.assertRaises(ValueError):
                Song.from_json(json.dumps(bad))
            with self.assertRaises(ValueError):
                save_project(song, Path(d)/'track.txt')
            song.tracks[0].notes[0].duration = -1
            with self.assertRaises(ValueError):
                song.to_json()

    def test_real_type1_midi_output(self):
        song = compose(self.request)
        raw = to_midi_bytes(song)
        self.assertTrue(raw.startswith(b'MThd\x00\x00\x00\x06\x00\x01'))
        self.assertEqual(raw.count(b'MTrk'), len(song.tracks) + 1)
        self.assertIn(b'\xff\x51\x03',raw)
        self.assertIn(b'\x99\x24',raw)  # channel 10 kick on
        with tempfile.TemporaryDirectory() as d:
            p=export_midi(song,Path(d)/'example.mid')
            self.assertEqual(p.read_bytes(),raw)

    def test_real_stereo_audio_and_cancellation(self):
        small = Song(title='tiny', prompt='tone', bpm=120, key='C', seed=1,
                     tracks=[Track(name='Test',instrument='piano',notes=[Note(60, 0, 1)])],
                     sections=[Section('Intro',0,1)])
        with tempfile.TemporaryDirectory() as d:
            output=Path(d)/'tiny.wav'
            events=[]
            render_wav(small,output,sample_rate=16000,progress=events.append)
            self.assertTrue(output.is_file())
            self.assertEqual(events[-1],1.)
            with wave.open(str(output),'rb') as wf:
                self.assertEqual(wf.getnchannels(),2)
                self.assertEqual(wf.getframerate(),16000)
                self.assertEqual(wf.getsampwidth(),2)
                self.assertGreater(wf.getnframes(),16000)
                self.assertNotEqual(wf.readframes(4000),b'\x00'*16000)
            before=output.read_bytes()
            token=threading.Event();token.set()
            with self.assertRaises(RenderCancelled):
                render_wav(small,output,cancel=token,sample_rate=16000)
            self.assertEqual(output.read_bytes(),before)

    def test_muted_tracks_do_not_sound(self):
        song = Song(title='tiny', prompt='tone', bpm=120, key='C', seed=1,
                    tracks=[Track(name='Test', instrument='piano',mute=True,notes=[Note(60,0,1)])],
                    sections=[Section('Intro',0,1)])
        with tempfile.TemporaryDirectory() as d:
            wav=Path(d)/'silence.wav'
            render_wav(song,wav,sample_rate=16000,delay=0)
            with wave.open(str(wav),'rb') as f:
                self.assertEqual(set(f.readframes(500)),{0})

    def test_job_errors_and_cancel(self):
        import time
        jobs = JobManager()
        try:
            def broken(*, cancel, progress):
                raise ValueError('expected job failure')
            job = jobs.submit(broken)
            for _ in range(100):
                if job.snapshot()['state'] == 'failed':
                    break
                time.sleep(.01)
            self.assertEqual(job.snapshot()['state'], 'failed')
            self.assertIn('expected job failure', job.snapshot()['error'])
        finally:
            jobs.close()

    def test_mp3_requires_ffmpeg(self):
        with patch('penny_music_studio.renderer.shutil.which',return_value=None):
            with self.assertRaisesRegex(RuntimeError,'FFmpeg'):
                convert_mp3('in.wav','out.mp3')


if __name__ == '__main__':
    unittest.main()
