"""Runtime hook — fix ctranslate2 DLL loading in a PyInstaller frozen build.

ctranslate2's __init__.py uses importlib.resources.files() to locate its DLLs
and loads them with ctypes.CDLL before importing the C extension. In a frozen
app importlib.resources.files() can return a Traversable that doesn't resolve to
a filesystem path that glob/ctypes can use directly, so we do the job ourselves
here before ctranslate2 is imported.
"""
import ctypes
import glob
import os
import sys

if sys.platform == "win32" and getattr(sys, "frozen", False):
    _base = sys._MEIPASS  # e.g. dist/bork/_internal
    _ct2  = os.path.join(_base, "ctranslate2")
    if os.path.isdir(_ct2):
        os.add_dll_directory(_ct2)
        os.add_dll_directory(_base)   # also add root for anything copied there
        # Pre-load every DLL in the ctranslate2 package dir
        for _dll in glob.glob(os.path.join(_ct2, "*.dll")):
            try:
                ctypes.CDLL(_dll)
            except OSError:
                pass
