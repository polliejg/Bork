"""Workflow engine — fuzzy-matches transcribed text to saved voice commands."""
import subprocess
from pathlib import Path

import yaml
import pyautogui
import pyperclip
from rapidfuzz import fuzz

from paths import app_dir

_FILE = app_dir() / "workflows" / "definitions.yaml"


class WorkflowEngine:
    def __init__(self):
        self.workflows: list[dict] = []
        self.threshold: int = 75
        self.load()

    def load(self):
        try:
            if _FILE.exists():
                data = yaml.safe_load(_FILE.read_text(encoding="utf-8")) or {}
                self.workflows = data.get("workflows", [])
                self.threshold = data.get("threshold", 75)
        except Exception as e:
            print(f"[workflows] load failed: {e}")

    def save(self):
        _FILE.parent.mkdir(exist_ok=True)
        _FILE.write_text(
            yaml.dump(
                {"threshold": self.threshold, "workflows": self.workflows},
                default_flow_style=False,
                allow_unicode=True,
            ),
            encoding="utf-8",
        )

    def match(self, text: str) -> dict | None:
        """Return first workflow whose phrase fuzzy-matches text, or None."""
        text_lower = text.lower().strip()
        for wf in self.workflows:
            for phrase in wf.get("phrases", []):
                score = fuzz.ratio(text_lower, phrase.lower())
                if score >= self.threshold:
                    print(f"[workflows] matched '{wf['name']}' score={score}")
                    return wf
        return None

    def execute(self, workflow: dict):
        for action in workflow.get("actions", []):
            t = action.get("type")
            try:
                if t == "exec":
                    subprocess.Popen(action["command"], shell=True)
                elif t == "keys":
                    pyautogui.hotkey(*action["keys"])
                elif t == "type_text":
                    pyperclip.copy(action["text"])
                    pyautogui.hotkey("ctrl", "v")
            except Exception as e:
                print(f"[workflows] action failed: {e}")
