# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec for Bork — run:  pyinstaller bork.spec
#
# Output: dist/bork/bork.exe  (onedir bundle — fast startup)

from PyInstaller.utils.hooks import collect_all, collect_data_files
import os

# Collect all data/binaries for packages with native extensions
ct2_d, ct2_b, ct2_h  = collect_all("ctranslate2")
fw_d,  fw_b,  fw_h   = collect_all("faster_whisper")
hf_d,  hf_b,  hf_h   = collect_all("huggingface_hub")
tok_d, tok_b, tok_h  = collect_all("tokenizers")

# Workflow definitions (created lazily, include dir if it exists)
extra_datas = []
if os.path.isdir("workflows"):
    extra_datas.append(("workflows", "workflows"))

import glob as _glob

# Explicitly pull ctranslate2 DLLs to the top-level _internal dir so Windows
# can find them without needing AddDllDirectory on older Python builds.
_ct2_site = os.path.join(os.path.dirname(os.path.abspath("bork.spec")),
                         ".venv", "Lib", "site-packages", "ctranslate2")
_ct2_dlls = [(p, ".") for p in _glob.glob(os.path.join(_ct2_site, "*.dll"))]

a = Analysis(
    ["main.py"],
    pathex=[],
    binaries=ct2_b + fw_b + hf_b + tok_b + _ct2_dlls,
    datas=ct2_d + fw_d + hf_d + tok_d + extra_datas,
    hiddenimports=(
        ct2_h + fw_h + hf_h + tok_h + [
            "PyQt6",
            "PyQt6.QtCore",
            "PyQt6.QtGui",
            "PyQt6.QtWidgets",
            "PyQt6.sip",
            "sounddevice",
            "_sounddevice_data",
            "keyboard",
            "pyperclip",
            "pyautogui",
            "rapidfuzz",
            "rapidfuzz.fuzz",
            "rapidfuzz.process",
            "httpx",
            "yaml",
            "numpy",
            "paths",
        ]
    ),
    hookspath=[],
    hooksconfig={},
    runtime_hooks=["hooks/rthook_ctranslate2.py"],
    excludes=["tkinter", "customtkinter", "pystray", "ollama", "pynput",
              "matplotlib", "scipy", "pandas"],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="bork",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,             # UPX can break some DLLs; disable for safety
    console=False,         # No terminal window — windowed app
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,             # Add an .ico path here if you have one
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="bork",
)
