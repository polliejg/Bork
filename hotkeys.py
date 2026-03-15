"""Global hotkey manager."""
import time
import threading
from threading import Lock

import numpy as np
import pyperclip
import sounddevice as sd
import keyboard

from app_state import AppState, Status
from recorder import Recorder
from transcriber import Transcriber
from enhancer import Enhancer
from workflow_engine import WorkflowEngine
from output import send_text
from enhancer import CONTEXT_SYSTEM_PROMPT

_SAMPLE_RATE = 16000


def _tone(freq: int, dur_ms: int = 160, volume: float = 0.07):
    """Subtle pop: very short, soft, fast decay."""
    def _play():
        n = int(_SAMPLE_RATE * dur_ms / 1000)
        t = np.linspace(0, dur_ms / 1000, n, False)
        wave = np.sin(2 * np.pi * freq * t)
        attack = int(_SAMPLE_RATE * 0.005)
        env = np.exp(-t * 18)
        env[:attack] = np.linspace(0, env[attack], attack)
        sd.play((wave * env * volume).astype(np.float32), _SAMPLE_RATE)
    threading.Thread(target=_play, daemon=True).start()


def _capture_selection() -> str:
    """
    Grab whatever text is currently selected in the active window.
    Uses the clipboard trick: save → Ctrl+C → compare → restore if nothing new.
    Returns the selected text, or '' if nothing was selected.
    """
    try:
        original = pyperclip.paste()
        keyboard.send("ctrl+c")
        time.sleep(0.08)          # give the target app time to write the clipboard
        selected = pyperclip.paste()
        if selected and selected != original:
            pyperclip.copy(original)   # restore so we don't clobber their clipboard
            return selected.strip()
        # Nothing new on clipboard — restore just in case
        pyperclip.copy(original)
    except Exception as e:
        print(f"[hotkeys] capture_selection failed: {e}", flush=True)
    return ""


class HotkeyManager:
    def __init__(self, state: AppState, recorder: Recorder,
                 transcriber: Transcriber, enhancer: Enhancer,
                 workflow_engine: WorkflowEngine,
                 output_mode: str, enhance_cfg: dict):
        self.state          = state
        self.recorder       = recorder
        self.transcriber    = transcriber
        self.enhancer       = enhancer
        self.workflow_engine = workflow_engine
        self.output_mode    = output_mode
        self.enhance_cfg    = enhance_cfg
        self._record_key: str | None  = None
        self._enhance_key: str | None = None
        self._enhance_held      = False
        self._enhance_activated = False
        self._context_text      = ""
        self._release_lock      = Lock()
        # Optional callback: fn(context_text, question, answer, messages)
        self.on_context_result  = None

    def start(self, record_key: str, enhance_key: str):
        self._record_key = record_key
        self._enhance_key = enhance_key
        self._enhance_held      = False
        self._enhance_activated = False
        self._context_text      = ""
        keyboard.on_press_key(record_key,  self._on_record_press,  suppress=False)
        keyboard.on_release_key(record_key, self._on_record_release, suppress=False)
        keyboard.on_press_key(enhance_key, self._on_enhance_press,  suppress=False)
        keyboard.on_release_key(enhance_key, self._on_enhance_release, suppress=False)

    def stop(self):
        keyboard.unhook_all()
        self._enhance_held      = False
        self._enhance_activated = False
        self._context_text      = ""

    def update_keys(self, record_key: str, enhance_key: str):
        self.stop()
        self.start(record_key, enhance_key)

    # ── Key callbacks ──────────────────────────────────────────────────────────

    def _on_enhance_press(self, event):
        if event.name != self._enhance_key:
            return
        self._enhance_held      = True
        self._enhance_activated = True

    def _on_enhance_release(self, event):
        if event.name != self._enhance_key:
            return
        self._enhance_held = False

    def _on_record_press(self, event):
        if event.name != self._record_key:
            return
        if self.state.status == Status.IDLE:
            self._enhance_activated = self._enhance_held
            # Capture any selected text BEFORE starting the recorder
            self._context_text = _capture_selection()
            if self._context_text:
                print(f"[hotkeys] context captured ({len(self._context_text)} chars)",
                      flush=True)
            self.state.set_status(Status.RECORDING)
            self.recorder.start()
            _tone(880)
        elif self.state.status not in (Status.IDLE,):
            self.state.set_status(self.state.status)

    def _on_record_release(self, event):
        if event.name != self._record_key:
            return
        with self._release_lock:
            if self.state.status != Status.RECORDING:
                return
            self.state.set_status(Status.TRANSCRIBING)
            enhance       = self._enhance_activated
            context_text  = self._context_text
            self._context_text = ""   # reset for next press
        _tone(660)
        threading.Thread(
            target=self._process, args=(enhance, context_text), daemon=True).start()

    # ── Processing ─────────────────────────────────────────────────────────────

    def _process(self, enhance: bool, context_text: str):
        audio = self.recorder.stop()
        if audio is None:
            self.state.set_status(Status.IDLE)
            return

        if self.transcriber is None:
            print("[hotkeys] model not ready yet", flush=True)
            self.state.set_status(Status.IDLE)
            return

        question = self.transcriber.transcribe(audio)
        if not question:
            self.state.set_status(Status.IDLE)
            return

        # ── Workflow check (plain transcription only, skip in context mode) ───
        if not context_text:
            workflow = self.workflow_engine.match(question)
            if workflow:
                self.workflow_engine.execute(workflow)
                self.state.add_history(f"[workflow] {question}")
                self.state.set_status(Status.IDLE)
                return

        # ── Context mode: highlighted text + voice question → AI answer ───────
        if context_text:
            cfg = self.enhance_cfg
            messages = [{"role": "user", "content": question}]
            result   = ""

            if not self.enhancer.connected:
                print("[hotkeys] context mode — enhancer not connected", flush=True)
            else:
                from enhancer import resolve_provider_config
                provider, api_url, api_key = resolve_provider_config(cfg)
                model = cfg.get("model", "")
                if model:
                    self.state.set_status(Status.ENHANCING)
                    try:
                        ctx_prompt = cfg.get("context_system_prompt", CONTEXT_SYSTEM_PROMPT)
                        # Question first so the model knows what it's doing,
                        # then the text to operate on — works with weak local models.
                        messages = [{
                            "role": "user",
                            "content": f"{question}\n\n{context_text}",
                        }]
                        result = self.enhancer.chat(
                            messages, model, ctx_prompt,
                            provider, api_url, api_key)
                        messages.append({"role": "assistant", "content": result})
                        print(f"[hotkeys] context answer: {result!r}", flush=True)
                    except Exception as e:
                        print(f"[hotkeys] context enhance failed: {e}", flush=True)

            if not result:
                result = "(No response — check AI connection in settings)"

            self.state.add_history(f"[context] {question}")

            # Show floating popup if callback is wired; otherwise paste the answer
            if self.on_context_result:
                self.on_context_result(context_text, question, result, messages)
            else:
                send_text(result, mode=self.output_mode)

            self.state.set_status(Status.IDLE)
            return

        # ── Standard enhancement mode ─────────────────────────────────────────
        text = question
        if enhance:
            cfg = self.enhance_cfg
            if not self.enhancer.connected:
                print("[enhancer] skipped — not connected", flush=True)
            else:
                from enhancer import resolve_provider_config
                provider, api_url, api_key = resolve_provider_config(cfg)
                model         = cfg.get("model", "")
                system_prompt = cfg.get("system_prompt", "")
                if model and system_prompt:
                    self.state.set_status(Status.ENHANCING)
                    try:
                        text = self.enhancer.enhance(
                            text, model, system_prompt, provider, api_url, api_key)
                        print(f"[enhancer] result: {text!r}", flush=True)
                    except Exception as e:
                        print(f"[enhancer] failed: {e}", flush=True)

        self.state.add_history(text)
        send_text(text, mode=self.output_mode)
        self.state.set_status(Status.IDLE)
