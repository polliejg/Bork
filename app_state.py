"""Shared application state — connects hotkeys, recorder, transcriber, and GUI."""
import threading
from enum import Enum, auto
from typing import Callable


class Status(Enum):
    IDLE = auto()
    RECORDING = auto()
    TRANSCRIBING = auto()
    ENHANCING = auto()
    LOADING = auto()


class AppState:
    def __init__(self):
        self.status = Status.LOADING
        self._listeners: list[Callable[[Status], None]] = []
        self._history: list[str] = []  # recent transcriptions
        self._lock = threading.Lock()

    # ── Status ────────────────────────────────────────────────────────────────

    def set_status(self, status: Status):
        self.status = status
        for fn in self._listeners:
            try:
                fn(status)
            except Exception:
                pass

    def on_status_change(self, fn: Callable[[Status], None]):
        self._listeners.append(fn)

    # ── History ───────────────────────────────────────────────────────────────

    def add_history(self, text: str):
        with self._lock:
            self._history.insert(0, text)
            self._history = self._history[:50]  # keep last 50

    def clear_history(self):
        with self._lock:
            self._history.clear()

    def get_history(self) -> list[str]:
        with self._lock:
            return list(self._history)
