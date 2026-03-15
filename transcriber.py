import numpy as np
from faster_whisper import WhisperModel


class Transcriber:
    def __init__(self, model: str = "base", language: str = "en", device: str = "cpu"):
        self.language = language
        print(f"[transcriber] loading whisper model '{model}' on {device}...", flush=True)
        self._model = WhisperModel(model, device=device, compute_type="float32")
        print("[transcriber] model ready", flush=True)

    def transcribe(self, audio: np.ndarray) -> str:
        segments, _ = self._model.transcribe(
            audio,
            language=self.language,
            beam_size=5,
        )
        text = " ".join(seg.text.strip() for seg in segments).strip()
        print(f"[transcriber] result: {text!r}")
        return text
