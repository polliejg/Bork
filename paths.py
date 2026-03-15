"""Resolve the user-data directory for both script and frozen-exe contexts."""
import sys
from pathlib import Path


def app_dir() -> Path:
    """Directory where user-data files (config.yaml, history.json, workflows/) live.

    - Frozen PyInstaller .exe  → directory that contains the .exe
    - Normal Python script     → directory that contains this file
    """
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).parent
