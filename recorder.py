import threading
from typing import Callable

import numpy as np
import sounddevice as sd

SAMPLE_RATE = 16000
CHANNELS = 1


class Recorder:
    def __init__(self, level_callback: Callable[[float], None] | None = None):
        self._chunks = []
        self._lock = threading.Lock()
        self._stream = None
        self.recording = False
        self.level_callback = level_callback

    def _callback(self, indata, frames, time, status):
        if self.recording:
            if self.level_callback:
                rms = float(np.sqrt(np.mean(indata ** 2)))
                self.level_callback(min(rms * 12, 1.0))  # scale 0→1
            with self._lock:
                self._chunks.append(indata.copy())

    def start(self):
        if self.recording:
            return
        self._chunks = []
        self.recording = True
        self._stream = sd.InputStream(
            samplerate=SAMPLE_RATE,
            channels=CHANNELS,
            dtype="float32",
            callback=self._callback,
        )
        self._stream.start()

    def stop(self) -> np.ndarray | None:
        if not self.recording:
            return None
        self.recording = False
        if self.level_callback:
            self.level_callback(0.0)
        self._stream.stop()
        self._stream.close()
        self._stream = None

        with self._lock:
            if not self._chunks:
                return None
            audio = np.concatenate(self._chunks, axis=0).flatten()

        if len(audio) < SAMPLE_RATE * 0.3:
            print("[recorder] audio too short, discarding")
            return None

        return audio
