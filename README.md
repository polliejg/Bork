# Bork 🐾

Voice-to-text for developers. Hold a hotkey, speak, release — your words appear wherever your cursor is. Pair it with an AI model to rewrite your dictation into clean, structured prompts before they land.

---

## How it works

| Hotkey | What happens |
|---|---|
| Hold `Right Ctrl` | Records your voice, transcribes on release, pastes instantly |
| Hold `Right Alt` + `Right Ctrl` | Same, but runs the transcript through an AI rewriter first |
| Highlight code/text → `Right Alt` + `Right Ctrl` | AI answers your voice question about the selected text |

All hotkeys are configurable.

---

## Setup

```bash
git clone https://github.com/polliejg/Bork.git
cd Bork

python -m venv .venv
.venv\Scripts\activate

pip install -r requirements.txt

copy config.example.yaml config.yaml

python main.py
```

On first run without a `config.yaml`, Bork creates one automatically with defaults.

---

## AI Enhancement

Works with **Ollama** (local, no key needed), **OpenAI**, **Anthropic/Claude**, **Google Gemini**, **Groq**, or any OpenAI-compatible endpoint. Configure the provider and API key in the **AI Settings** tab.

The default prompt rewrites your dictation into a clean coding prompt. You can customise it or pick from presets (Coding AI, Concise, Formal).

---

## Whisper models

Models download automatically on first use via HuggingFace. `base` is the default (145 MB, fast). Change it in Settings — options range from `tiny` to `large-v3`.

---

## Build .exe

```bash
pip install pyinstaller
pyinstaller bork.spec
# output: dist/bork/bork.exe
```

---

## License

MIT
