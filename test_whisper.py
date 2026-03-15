"""Minimal test — run this directly to check if WhisperModel loads."""
import numpy as np
from faster_whisper import WhisperModel

print("trying float32...", flush=True)
try:
    m = WhisperModel("base", device="cpu", compute_type="float32")
    print("float32 OK", flush=True)
except Exception as e:
    print(f"float32 FAILED: {e}", flush=True)
    m = None

if m:
    dummy = np.zeros(16000, dtype=np.float32)
    segs, _ = m.transcribe(dummy, language="en")
    print("transcribe OK:", list(segs), flush=True)
