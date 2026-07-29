# GrammarCheck — Local AI Grammar & Spelling Checker

Powered by **Gemma 4 E4B** running locally via Ollama. Zero cloud, zero cost per request, fully private.

---

## Phase 1: Python CLI Tool ✅

### Prerequisites

| Tool | Install |
|------|---------|
| Python 3.9+ | Already on macOS, or `brew install python` |
| Ollama | https://ollama.com/download → download the Mac app |
| Gemma model | `ollama pull gemma4:e4b` (≈ 3-4 GB download) |

### Setup

```bash
# 1. Clone / copy this folder
cd grammarcheck

# 2. Install the only dependency
pip install requests

# 3. Start Ollama (if not already running)
ollama serve          # or just open the Ollama.app on Mac

# 4. Pull the model (one-time, ~3-4 GB)
ollama pull gemma4:e4b
```

> **Lower-end Mac?** Use `gemma3:4b` instead — same quality, slightly faster:
> `ollama pull gemma3:4b`
> `python grammar_check.py --model gemma3:4b "your text"`

---

## Usage

### Interactive mode (paste long text)
```bash
python grammar_check.py
```
Type or paste text, then press **Enter twice** to submit.

### Inline argument
```bash
python grammar_check.py "I has went to teh store yesterday."
```

### Pipe from file
```bash
cat my_essay.txt | python grammar_check.py
```

### Use a different model
```bash
python grammar_check.py --model gemma3:4b "She dont likes coffee."
```

### Get raw JSON output (useful for integrations)
```bash
python grammar_check.py --json "He runned very fastly."
```

---

## Sample Output

```
── GRAMMAR CHECK RESULTS ────────────────────────────────────
Summary
  The text contains 3 errors: 1 spelling, 1 grammar, 1 word choice issue.

Issues  ✗ 3 issues found

  1.
  SPELLING
  'teh'  →  'the'
  Phonetic misspelling: letter transposition 'e' and 'h' swapped.

  2.
  GRAMMAR
  'has went'  →  'went'
  Incorrect verb tense. 'went' is the simple past of 'go'; 'has gone'
  would be present perfect. 'Has went' mixes auxiliary 'has' with simple
  past instead of past participle 'gone'.

  3.
  WORD_CHOICE
  'yesterday'  →  'yesterday'
  With simple past 'went', 'yesterday' is correct — no change needed here.

────────────────────────────────────────────────────────────
Corrected Text

  I went to the store yesterday.

────────────────────────────────────────────────────────────
Diff  (~~red~~ = removed   green = added)

  I ~~has went~~ went to ~~teh~~ the store yesterday.
```

---

## JSON Output Schema

```json
{
  "corrected_text": "Full corrected version of your text",
  "errors": [
    {
      "original": "teh",
      "corrected": "the",
      "type": "spelling",
      "reason": "Letter transposition — 'e' and 'h' swapped."
    }
  ],
  "summary": "One sentence assessment of overall text quality."
}
```

Error types: `spelling` | `grammar` | `punctuation` | `style` | `word_choice`

---

## Phase 2 Roadmap: System-Wide on Mac 🔜

Planned integrations to make this available everywhere on macOS:

### Option A — macOS Service (right-click anywhere)
- Register a macOS Automator Service / Shortcuts action
- Select any text in any app → right-click → "Check Grammar"
- Result shown in a popup notification or small window

### Option B — Menu Bar App
- Small Python app using `rumps` library sitting in your Mac menu bar
- Paste text → click menu bar icon → see corrections in a dropdown

### Option C — Global Hotkey (most Grammarly-like)
- Press `⌘ + Shift + G` anywhere on the system
- Floating window appears with selected text auto-filled
- Show corrections inline

### Option D — Browser Extension
- Chrome/Safari extension that adds a "Check Grammar" button to any `<textarea>`
- Calls your local FastAPI server (wraps `grammar_check.py`)

### Recommended Phase 2 Stack
```
grammar_check.py (core logic, already done)
    ↑
FastAPI server (grammar_server.py)  — HTTP wrapper
    ↑
macOS Service / Shortcut / Extension  — UI layer
```

---

## Performance Notes

| Mac | RAM | Expected Speed |
|-----|-----|----------------|
| M1/M2/M3/M4 any | 8 GB+ | 5–10 sec per check |
| Intel Mac | 16 GB+ | 10–25 sec per check |
| Intel Mac | 8 GB | Use `gemma3:1b` for speed |

Gemma runs on the GPU on Apple Silicon via Ollama's Metal backend — very fast.

---

## Troubleshooting

**"Cannot connect to Ollama"**
```bash
ollama serve   # start Ollama manually
```

**"Model not found"**
```bash
ollama pull gemma4:e4b
```

**Slow on Intel Mac**
```bash
# Use a smaller model
python grammar_check.py --model gemma3:1b "your text"
```
