"""Entry point."""
import subprocess
import sys
import threading
import time
from pathlib import Path

from paths import app_dir

# Log to file — C-level crashes won't appear here but Python output will
_log = open(app_dir() / "voice_tool.log", "w", encoding="utf-8", buffering=1)
sys.stdout = _log
sys.stderr = _log

import traceback as _tb
import yaml

# ── Load Whisper model BEFORE any PyQt6 import ───────────────────────────────
# PyQt6's DLLs conflict with CTranslate2 (faster-whisper backend) if loaded
# into the process first, causing a silent C-level crash. Importing gui/PyQt6
# must happen only after the model is in memory.
from app_state import AppState, Status
from transcriber import Transcriber

CONFIG_PATH = app_dir() / "config.yaml"

_DEFAULT_CONFIG = {
    "transcription": {"model": "base", "language": "en", "device": "cpu"},
    "hotkeys":       {"record_key": "right ctrl", "enhance_key": "right alt"},
    "output":        {"mode": "type"},
    "ai_enhancement": {
        "provider": "ollama",
        "model": "",
        "preset": "Coding AI",
        "system_prompt": (
            "You are a prompt rewriting assistant. The user has dictated text they "
            "want to send to a coding AI. Rewrite it as a clear, well-structured "
            "prompt. Do NOT answer the question. Do NOT address the user. "
            "ONLY output the rewritten prompt, nothing else."
        ),
        "providers": {
            "ollama":    {"api_url": "http://localhost:11434/v1", "api_key": ""},
            "openai":    {"api_url": "https://api.openai.com/v1",  "api_key": ""},
            "anthropic": {"api_url": "https://api.anthropic.com",  "api_key": ""},
            "groq":      {"api_url": "https://api.groq.com/openai/v1", "api_key": ""},
            "google":    {"api_url": "https://generativelanguage.googleapis.com/v1beta/openai", "api_key": ""},
            "custom":    {"api_url": "", "api_key": ""},
        },
    },
}


def load_config() -> dict:
    if not CONFIG_PATH.exists():
        save_config(_DEFAULT_CONFIG)
        return dict(_DEFAULT_CONFIG)
    with open(CONFIG_PATH, encoding="utf-8") as f:
        return yaml.safe_load(f)


def save_config(config: dict):
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        yaml.dump(config, f, default_flow_style=False, allow_unicode=True)


def main():
    sys.excepthook = lambda t, v, tb: print(
        "".join(_tb.format_exception(t, v, tb)), flush=True)

    config = load_config()

    print("[main] loading whisper model (before Qt DLLs)...", flush=True)
    transcriber = Transcriber(
        model=config["transcription"]["model"],
        language=config["transcription"]["language"],
        device=config["transcription"]["device"],
    )
    print("[main] model ready — importing Qt...", flush=True)

    # NOW it is safe to import PyQt6 and everything that depends on it
    from PyQt6.QtWidgets import QApplication
    from recorder import Recorder
    from enhancer import Enhancer
    from hotkeys import HotkeyManager
    from gui import VoiceToolWindow
    from workflow_engine import WorkflowEngine
    import history_store

    print("[main] Qt imported OK", flush=True)

    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)

    state           = AppState()
    workflow_engine = WorkflowEngine()
    recorder        = Recorder()
    enhancer        = Enhancer()

    # ── Migrate old flat config schema to nested providers schema ────────────
    raw_ai = config.setdefault("ai_enhancement", {})
    if "backend" in raw_ai and "provider" not in raw_ai:
        old_backend = raw_ai.pop("backend", "ollama")
        old_url     = raw_ai.pop("api_url", "")
        old_key     = raw_ai.pop("api_key", "")
        raw_ai["provider"] = old_backend
        raw_ai.setdefault("providers", {}).setdefault(old_backend, {
            "api_url": old_url, "api_key": old_key})
        save_config(config)
        print("[main] migrated config to nested providers schema", flush=True)

    # Ensure nested providers block exists for all known providers
    from enhancer import PROVIDERS as _PROV, CONTEXT_SYSTEM_PROMPT as _CTX_PROMPT
    raw_ai.setdefault("provider", "ollama")
    raw_ai.setdefault("model", "")
    raw_ai.setdefault("preset", "Coding AI")
    raw_ai.setdefault("system_prompt", (
        "You are a prompt rewriting assistant. The user has dictated text they "
        "want to send to a coding AI. Rewrite it as a clear, well-structured "
        "prompt. Do NOT answer the question. Do NOT address the user. "
        "ONLY output the rewritten prompt, nothing else."
    ))
    raw_ai.setdefault("context_system_prompt", _CTX_PROMPT)
    providers_block = raw_ai.setdefault("providers", {})
    for pid, pdef in _PROV.items():
        providers_block.setdefault(pid, {"api_url": pdef.default_url, "api_key": ""})

    ai_cfg = raw_ai

    hotkey_mgr = HotkeyManager(
        state=state,
        recorder=recorder,
        transcriber=transcriber,
        enhancer=enhancer,
        workflow_engine=workflow_engine,
        output_mode=config["output"]["mode"],
        enhance_cfg=ai_cfg,
    )

    def refresh_connection():
        from enhancer import resolve_provider_config
        provider, api_url, api_key = resolve_provider_config(ai_cfg)
        connected = enhancer.check_connection(provider, api_url, api_key)
        window.set_ollama_status(connected)
        if connected:
            models     = enhancer.list_models(provider, api_url, api_key)
            configured = ai_cfg.get("model", "")
            selected   = enhancer.auto_select_model(configured, provider, api_url, api_key)
            ai_cfg["model"] = selected
            window.set_ollama_models(models, selected)

    def start_ollama():
        try:
            subprocess.Popen(
                ["ollama", "serve"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=subprocess.CREATE_NO_WINDOW,
            )
            time.sleep(2)
        except FileNotFoundError:
            print("[ollama] ollama not found in PATH", flush=True)
        except Exception as e:
            print(f"[ollama] failed to start: {e}", flush=True)
        finally:
            refresh_connection()

    def on_settings_save(new_config: dict):
        save_config(new_config)
        hotkey_mgr.output_mode = new_config["output"]["mode"]
        hotkey_mgr.enhance_cfg = new_config.get("ai_enhancement", ai_cfg)
        hotkey_mgr.update_keys(
            new_config["hotkeys"]["record_key"],
            new_config["hotkeys"].get("enhance_key", "right alt"),
        )

    window = VoiceToolWindow(
        state=state,
        config=config,
        workflow_engine=workflow_engine,
        on_settings_save=on_settings_save,
        on_refresh_models=refresh_connection,
        on_start_ollama=start_ollama,
    )

    recorder.level_callback  = window.update_level
    window._enhancer_ref     = enhancer
    hotkey_mgr.on_context_result = window.show_context_popup

    persisted = history_store.load()
    state._history = persisted
    if persisted:
        window.refresh_history(list(reversed(persisted)))

    original_add_history = state.add_history
    original_clear_history = state.clear_history

    def add_history_and_persist(text: str):
        original_add_history(text)
        history_store.save(state._history)
        window.refresh_history(list(reversed(state._history)))

    def clear_history_and_persist():
        original_clear_history()
        history_store.save(state._history)   # saves empty list

    state.add_history   = add_history_and_persist
    state.clear_history = clear_history_and_persist

    window.show()

    def _post_load():
        hotkey_mgr.start(
            config["hotkeys"]["record_key"],
            config["hotkeys"].get("enhance_key", "right alt"),
        )
        state.set_status(Status.IDLE)
        refresh_connection()

    threading.Thread(target=_post_load, daemon=True).start()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
