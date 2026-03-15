import time
import pyperclip
import pyautogui


def send_text(text: str, mode: str = "type"):
    """Send transcribed text to the previously-focused window.

    Always writes to clipboard first so the text is never lost.
    In 'type' mode, also attempts a Ctrl+V paste into whatever window
    was active when the hotkey was released.
    """
    if not text:
        return

    # Always put text on clipboard — safe fallback if paste fails
    pyperclip.copy(text)

    if mode == "type":
        try:
            # Brief pause to ensure the hotkey-release event has fully settled
            # and the target window still has focus
            time.sleep(0.1)
            pyautogui.hotkey("ctrl", "v")
        except Exception as e:
            # Paste failed (e.g. no focusable field) — text still on clipboard
            print(f"[output] paste failed ({e}), text saved to clipboard")
    # clipboard-only mode: already copied above, nothing more to do
