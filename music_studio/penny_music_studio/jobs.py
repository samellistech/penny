"""Non-blocking cancellable operations for the studio UI."""
from concurrent.futures import ThreadPoolExecutor
from threading import Event, Lock
from uuid import uuid4


class MusicJob:
    def __init__(self):
        self.id = uuid4().hex
        self.cancel_event = Event()
        self._lock = Lock()
        self.progress = 0.0
        self.state = 'queued'
        self.result = None
        self.error = None

    def cancel(self) -> None:
        self.cancel_event.set()

    def update(self, progress: float) -> None:
        with self._lock:
            self.progress = max(0, min(1, progress))

    def snapshot(self) -> dict:
        with self._lock:
            return {'id': self.id, 'state': self.state, 'progress': self.progress,
                    'error': str(self.error) if self.error else None,
                    'result': str(self.result) if self.result is not None else None}


class JobManager:
    def __init__(self, max_workers: int = 1):
        self.executor = ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix='pme')

    def submit(self, function, *args, **kwargs) -> MusicJob:
        job = MusicJob()
        def run():
            from .renderer import RenderCancelled
            if job.cancel_event.is_set():
                job.state = 'cancelled'
                return
            job.state = 'running'
            try:
                job.result = function(*args, cancel=job.cancel_event, progress=job.update, **kwargs)
                job.state = 'cancelled' if job.cancel_event.is_set() else 'done'
            except RenderCancelled:
                job.state = 'cancelled'
            except Exception as exc:
                job.error = exc
                job.state = 'failed'
        self.executor.submit(run)
        return job

    def close(self):
        self.executor.shutdown(wait=False, cancel_futures=True)
