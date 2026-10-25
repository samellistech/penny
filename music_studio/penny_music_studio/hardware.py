"""Non-invasive hardware discovery; rendering does not require CUDA or torch."""
from dataclasses import dataclass, asdict
import importlib.util
import os
import platform


@dataclass(frozen=True)
class Hardware:
    platform: str
    cpu_threads: int
    backend: str
    torch_installed: bool
    gpu_status: str

    def describe(self) -> dict:
        return asdict(self)


def detect_hardware() -> Hardware:
    installed = importlib.util.find_spec('torch') is not None
    # Avoid loading large ML frameworks or touching GPU devices during app startup.
    return Hardware(platform=platform.platform(), cpu_threads=os.cpu_count() or 1,
                    backend='cpu-procedural', torch_installed=installed,
                    gpu_status='not probed (MVP uses CPU; optional adapters will probe at activation)')
