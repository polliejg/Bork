# Bork 🐾

Voice-to-text for developers. Hold a hotkey, speak, release — your words appear wherever your cursor is. Works standalone or paired with an AI model to clean up your dictation before it lands.

---

## Usage

### Basic transcription
Hold `Right Ctrl`, speak, release. Text is pasted instantly into whatever you were typing in.

### AI-enhanced transcription
Hold `Right Alt` + `Right Ctrl`, speak, release. Your dictation is rewritten by an AI before pasting — great for turning rough spoken thoughts into clean, structured prompts.

### Ask a question about highlighted text
Highlight any text on screen, then hold `Right Ctrl`, ask your question out loud, release. The AI reads the highlighted text and answers your question in a floating popup. No Alt needed — just highlight and record.

All hotkeys are configurable in the **Settings** tab.

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

A `config.yaml` is created automatically on first run if one doesn't exist.

---

## AI providers

Configure your provider and API key in the **AI Settings** tab. Supported:

| Provider | Key required | Notes |
|---|---|---|
| **Ollama** | No | Local models, runs fully offline |
| **OpenAI** | Yes | GPT-4o, etc. |
| **Anthropic** | Yes | Claude models |
| **Google Gemini** | Yes | Gemini 2.0 Flash, 2.5 Pro, etc. |
| **Groq** | Yes | Fast inference, free tier available |
| **Custom** | Optional | Any OpenAI-compatible endpoint |

---

## Whisper models

Models download automatically on first use. `base` is the default (145 MB, good for most uses). Change the model in **Settings** — options range from `tiny` to `large-v3`.

---

## Workflows

Map voice phrases to keyboard shortcuts or shell commands. Bork fuzzy-matches what you said and fires the action. Manage them in the **Workflows** tab or edit `workflows/definitions.yaml` directly.

---

## Build .exe

```bash
pip install pyinstaller
pyinstaller bork.spec
# output: dist/bork/bork.exe
```

Or download a pre-built release from the [Releases](https://github.com/polliejg/Bork/releases) page.

---

## License

MIT
