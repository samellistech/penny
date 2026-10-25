"""Basic stand-alone Tk desktop editor; compatible with the wider Penny dashboard via future adapter."""
import os
from pathlib import Path
import sys
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from .composition import interpret_prompt, limitations
from .engine import ProceduralCompositionBackend
from .jobs import JobManager
from .midi import export_midi
from .renderer import render_wav
from .storage import save_project, load_project


class StudioApp:
    def __init__(self, root):
        self.root = root
        self.song = None
        self.job = None
        self.jobs = JobManager()
        self.last_wav = None
        root.title('Penny Music Studio · Procedural MVP')
        root.geometry('860x690')
        self.title_var = tk.StringVar(value='Sammy Rock Anthem Sketch')
        self.bpm_var = tk.StringVar(value='')
        self.key_var = tk.StringVar(value='G')
        self.bars_var = tk.StringVar(value='2')
        self.status_var = tk.StringVar(value='Ready · CPU procedural backend')
        root.columnconfigure(0, weight=1)
        root.rowconfigure(5, weight=1)
        ttk.Label(root, text='PENNY MUSIC STUDIO', font=('Segoe UI', 19, 'bold')).grid(row=0, column=0, sticky='w', padx=16, pady=10)
        options = ttk.Frame(root)
        options.grid(row=1, column=0, sticky='ew', padx=16)
        for i, (label, var, width) in enumerate([('Title', self.title_var, 32), ('BPM (auto if blank)', self.bpm_var, 8),
                                                 ('Key', self.key_var, 5), ('Bars/section', self.bars_var, 5)]):
            ttk.Label(options, text=label).grid(row=0, column=i, sticky='w')
            ttk.Entry(options, textvariable=var, width=width).grid(row=1, column=i, padx=(0,12), sticky='w')
        ttk.Label(root, text='Describe the composition (procedural arrangement, no sung vocals):').grid(row=2, column=0, sticky='w', padx=16, pady=(14,2))
        self.prompt = tk.Text(root, height=4, wrap='word')
        self.prompt.insert('1.0', 'Create an emotional country-rock love song with a piano introduction, acoustic guitars, powerful drums, bass, a soaring electric guitar solo, gospel choir and a dramatic final chorus with a key change.')
        self.prompt.grid(row=3, column=0, sticky='ew', padx=16)
        buttons = ttk.Frame(root)
        buttons.grid(row=4, column=0, sticky='w', padx=16, pady=14)
        for i, (label, cb) in enumerate([('Compose', self.compose), ('Open Project', self.open_project),
                                        ('Save Project', self.save), ('Export MIDI', self.midi),
                                        ('Render WAV', self.wav), ('Play WAV', self.play), ('Cancel Render', self.cancel)]):
            ttk.Button(buttons, text=label, command=cb).grid(row=0, column=i, padx=3)
        frame = ttk.LabelFrame(root, text='Editable tracks · volume, pan and mute')
        frame.grid(row=5, column=0, sticky='nsew', padx=16)
        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(0, weight=1)
        self.tree = ttk.Treeview(frame, columns=('instrument','notes','volume','pan','mute'), show='headings')
        for name in ('instrument','notes','volume','pan','mute'):
            self.tree.heading(name, text=name.title())
            self.tree.column(name, width=115)
        self.tree.grid(row=0, column=0, sticky='nsew')
        scroll = ttk.Scrollbar(frame, orient='vertical', command=self.tree.yview)
        scroll.grid(row=0, column=1, sticky='ns')
        self.tree.configure(yscrollcommand=scroll.set)
        controls = ttk.Frame(root)
        controls.grid(row=6, column=0, sticky='w', padx=16, pady=7)
        ttk.Label(controls, text='Selected track volume:').pack(side='left')
        self.volume = ttk.Scale(controls, from_=0, to=1, length=130, command=self.change_volume)
        self.volume.pack(side='left', padx=8)
        ttk.Label(controls, text='Pan:').pack(side='left')
        self.pan = ttk.Scale(controls, from_=-1, to=1, length=130, command=self.change_pan)
        self.pan.pack(side='left', padx=8)
        ttk.Button(controls, text='Toggle Mute', command=self.toggle_mute).pack(side='left', padx=8)
        self.tree.bind('<<TreeviewSelect>>', self.selected)
        ttk.Label(root, textvariable=self.status_var).grid(row=7, column=0, sticky='w', padx=16, pady=9)
        self.progress = ttk.Progressbar(root, mode='determinate', maximum=100)
        self.progress.grid(row=8, column=0, sticky='ew', padx=16, pady=(0,15))
        self.root.protocol('WM_DELETE_WINDOW', self.close)

    def selected_track(self):
        if self.song and self.tree.selection():
            return self.song.tracks[int(self.tree.selection()[0])]
        return None

    def selected(self, *_):
        track = self.selected_track()
        if track:
            self.volume.set(track.volume)
            self.pan.set(track.pan)

    def change_volume(self, value):
        track = self.selected_track()
        if track:
            track.volume = round(float(value), 2)
            self.refresh()

    def change_pan(self, value):
        track = self.selected_track()
        if track:
            track.pan = round(float(value), 2)
            self.refresh()

    def toggle_mute(self):
        track = self.selected_track()
        if track:
            track.mute = not track.mute
            self.refresh()

    def refresh(self):
        selection = self.tree.selection()
        for item in self.tree.get_children():
            self.tree.delete(item)
        if self.song:
            for i, t in enumerate(self.song.tracks):
                self.tree.insert('', 'end', iid=str(i), values=(t.name, len(t.notes),t.volume,t.pan,str(t.mute)))
        if selection and self.tree.exists(selection[0]):
            self.tree.selection_set(selection[0])

    def compose(self):
        try:
            request = interpret_prompt(self.prompt.get('1.0','end').strip(),
                bpm=int(self.bpm_var.get()) if self.bpm_var.get().strip() else None,
                key=self.key_var.get(), bars_per_section=int(self.bars_var.get()), title=self.title_var.get())
            self.song = ProceduralCompositionBackend().generate(request)
            self.refresh()
            caveats = ' '.join(limitations(request.prompt))
            self.status_var.set(f'{len(self.song.tracks)} tracks · {self.song.duration_seconds:.1f}s. {caveats}')
        except Exception as exc:
            messagebox.showerror('Composition error', str(exc))

    def open_project(self):
        path = filedialog.askopenfilename(filetypes=[('Penny projects','*.pennyjson')])
        if path:
            try:
                self.song = load_project(path)
                self.title_var.set(self.song.title)
                self.bpm_var.set(str(self.song.bpm))
                self.key_var.set(self.song.key)
                self.prompt.delete('1.0','end')
                self.prompt.insert('1.0',self.song.prompt)
                self.refresh()
                self.status_var.set(f'Opened {path}')
            except Exception as exc:
                messagebox.showerror('Load error', str(exc))

    def save(self):
        if not self.song:
            return messagebox.showinfo('Penny', 'Compose or open a project first')
        path = filedialog.asksaveasfilename(defaultextension='.pennyjson',filetypes=[('Penny projects','*.pennyjson')])
        if path:
            try:
                save_project(self.song,path)
                self.status_var.set(f'Saved {path}')
            except Exception as exc:
                messagebox.showerror('Save error',str(exc))

    def midi(self):
        if not self.song:
            return messagebox.showinfo('Penny', 'Compose or open a project first')
        path = filedialog.asksaveasfilename(defaultextension='.mid',filetypes=[('MIDI files','*.mid')])
        if path:
            try:
                export_midi(self.song,path)
                self.status_var.set(f'Exported {path}')
            except Exception as exc:
                messagebox.showerror('MIDI error',str(exc))

    def wav(self):
        if not self.song:
            return messagebox.showinfo('Penny','Compose or open a project first')
        if self.job and self.job.snapshot()['state'] in ('queued','running'):
            return messagebox.showinfo('Penny','A render is already running')
        path = filedialog.asksaveasfilename(defaultextension='.wav',filetypes=[('WAV files','*.wav')])
        if path:
            self.last_wav = None
            self.job = self.jobs.submit(render_wav, self.song, path)
            self.status_var.set('Rendering WAV in background...')
            self.poll()

    def poll(self):
        if not self.job:
            return
        state = self.job.snapshot()
        self.progress['value'] = state['progress'] * 100
        if state['state'] in ('queued','running'):
            self.root.after(200,self.poll)
        else:
            self.status_var.set(f"Render {state['state']}: {state['result'] or state['error'] or ''}")
            if state['state'] == 'done':
                self.last_wav = Path(state['result'])

    def cancel(self):
        if self.job:
            self.job.cancel()

    def play(self):
        if not self.last_wav or not self.last_wav.exists():
            return messagebox.showinfo('Penny','Render a WAV in this session first')
        if sys.platform == 'win32':
            import winsound
            winsound.PlaySound(str(self.last_wav), winsound.SND_FILENAME | winsound.SND_ASYNC)
        else:
            messagebox.showinfo('Penny','Open the WAV in your system audio player. Windows playback is built in.')

    def close(self):
        if self.job:
            self.job.cancel()
        self.jobs.close()
        self.root.destroy()


def launch():
    root = tk.Tk()
    StudioApp(root)
    root.mainloop()
