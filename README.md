# Bork 🐾

A lightweight Windows voice-to-text tool with AI enhancement. Hold a hotkey, speak, release — your words appear wherever your cursor is.

---

## Features

| Feature | Description |
|---|---|
| **Voice transcription** | Whisper-powered speech-to-text (runs fully offline) |
| **AI enhancement** | Rewrites your dictation before pasting — great for prompts, emails, and code |
| **Context mode** | Highlight text, hold Enhance + Record, ask a voice question — AI answers inline |
| **Multi-provider AI** | Works with Ollama (local), OpenAI, Anthropic/Claude, Groq, or any OpenAI-compatible endpoint |
| **Workflows** | Map voice phrases to keyboard shortcuts or shell commands via fuzzy matching |
| **System tray** | Runs quietly in the background; shows recording/transcribing state |
| **Transcript history** | Last 200 transcriptions stored and shown in the app |

---

## Hotkeys

| Action | Default |
|---|---|
| Record & transcribe | `Right Ctrl` (hold to record, release to transcribe) |
| Record & AI-enhance | `Right Alt` + `Right Ctrl` (hold both, release to transcribe + enhance) |
| Context mode | Highlight text in any app → hold `Right Alt` + `Right Ctrl` → ask your question |

> Hotkeys are fully configurable in the **Settings** tab.

---

## Setup

### Requirements

- Windows 10 / 11
- Python 3.10+ (for running from source)
- A working microphone

### Run from source

```bash
git clone https://github.com/polliejg/Bork.git
cd bork

python -m venv .venv
.venv\Scripts\activate

pip install -r requirements.txt

# Copy the example config and (optionally) add API keys
copy config.example.yaml config.yaml

python main.py
```

On first run without a `config.yaml`, Bork creates one automatically with default settings.

### Run the pre-built .exe

Download the latest release from the [Releases](https://github.com/polliejg/Bork/releases) page, unzip, and run `bork.exe`. No Python required.

> **Note:** Windows Defender may flag the `.exe` as suspicious (false positive common with PyInstaller apps). You can build from source to avoid this — see below.

---

## AI Providers

### Ollama (local, no API key needed)

1. Install [Ollama](https://ollama.com)
2. Pull a model: `ollama pull qwen2.5-coder:14b`
3. Bork auto-connects on startup

### OpenAI

1. Get an API key from [platform.openai.com](https://platform.openai.com)
2. Enter it in **AI Settings → OpenAI → API Key**

### Anthropic / Claude

1. Get an API key from [console.anthropic.com](https://console.anthropic.com)
2. Enter it in **AI Settings → Anthropic → API Key**

### Groq

1. Get a free API key from [console.groq.com](https://console.groq.com)
2. Enter it in **AI Settings → Groq → API Key**

### Custom endpoint

Any OpenAI-compatible API (e.g. LM Studio, Jan, vLLM). Set the base URL in **AI Settings → Custom**.

---

## Whisper models

Bork uses [faster-whisper](https://github.com/SYSTRAN/faster-whisper). Models are downloaded automatically on first use and cached in `~/.cache/huggingface/`.

| Model | Size | Speed | Accuracy |
|---|---|---|---|
| `tiny` | 75 MB | Fastest | Lower |
| `base` | 145 MB | Fast | Good *(default)* |
| `small` | 465 MB | Medium | Better |
| `medium` | 1.5 GB | Slow | High |
| `large-v3` | 3 GB | Slowest | Best |

Change the model in **Settings → Transcription Model** (restart required).

---

## Workflows

Workflows let you trigger actions by voice. Bork fuzzy-matches your speech against a list of phrases and executes the mapped action.

Workflows are stored in `workflows/definitions.yaml`:

```yaml
threshold: 75   # fuzzy match strictness (0–100)
workflows:
  - name: Open Terminal
    phrases:
      - open terminal
      - launch terminal
    actions:
      - type: exec
        command: wt.exe

  - name: Copy All
    phrases:
      - select all and copy
    actions:
      - type: keys
        keys: [ctrl, a]
      - type: keys
        keys: [ctrl, c]
```

**Action types:**

| Type | Description |
|---|---|
| `exec` | Run a shell command |
| `keys` | Send a keyboard shortcut |
| `type_text` | Paste a fixed string |

---

## Building the .exe

Requires `pyinstaller`:

```bash
pip install pyinstaller
pyinstaller bork.spec
```

The output is in `dist/bork/`. Copy the entire `dist/bork/` folder to distribute. The first launch will download the Whisper model.

---

## Security

- **`config.yaml` is gitignored** — your API keys are never committed.
- **`history.json` is gitignored** — your transcription history stays local.
- All AI requests go directly from your machine to the provider (no proxy).
- Workflows with `exec` actions run commands you define — review your workflow file if you share configs.

---

## License

MIT
