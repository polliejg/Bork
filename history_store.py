"""Persistent transcription history stored as JSON."""
import json
from pathlib import Path

from paths import app_dir

_FILE = app_dir() / "history.json"
MAX_ITEMS = 200


def load() -> list[str]:
    try:
        if _FILE.exists():
            return json.loads(_FILE.read_text(encoding="utf-8"))[:MAX_ITEMS]
    except Exception as e:
        print(f"[history] load failed: {e}")
    return []


def save(items: list[str]):
    try:
        _FILE.write_text(
            json.dumps(items[:MAX_ITEMS], ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    except Exception as e:
        print(f"[history] save failed: {e}")
