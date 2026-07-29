# GrammarCheck

**Privacy-first, self-hosted grammar and spelling checker.** No cloud, no API keys, no data leaves your machine.

Powered by a local LLM (via Ollama) running on your own hardware. Available as a web app or a native macOS menu-bar app.

---

## Features

- **Grammar & spell check** — detects spelling, grammar, punctuation, style, and word choice issues
- **Inline diff** — see exactly what changed with color-coded word-level diffs
- **Apply corrections selectively** — apply individual fixes one at a time, or apply all at once
- **Cancel in-flight checks** — abort long-running LLM calls instantly
- **Live health status** — green/red indicator for backend connectivity
- **Keyboard shortcuts** — `Cmd+Enter` to check, `Ctrl+Shift+G` (desktop) to open popover
- **Feedback** — thumbs up/down stored locally for quality tracking
- **Docker support** — `docker compose up` for backend + Ollama in containers

---

## Quick Start

```bash
# 1. Prerequisites
# Install Ollama: https://ollama.com/download
ollama pull qwen3.5:9b-mlx
ollama serve

# 2. Backend
pip install -r backend/requirements.txt
uvicorn main:app --reload --port 8000     # or: make dev

# 3. Frontend (separate terminal)
cd frontend && npm install && npm run dev

# Open http://localhost:5173
```

## Desktop (macOS)

```bash
cd desktop/GrammarCheck
xcodegen generate
open GrammarCheck.xcodeproj
# Build & run — menu-bar icon appears, Ctrl+Shift+G to open
```

## Docker (backend only)

```bash
docker compose up -d
```

---

## Architecture

```
Browser (port 5173)  ──proxy──▶  Backend (port 8000)  ────▶  Ollama (port 11434)
macOS App            ──HTTP───▶  Backend (port 8000)  ────▶  Ollama (port 11434)
```

Three components, all optional — use just the web app, just the desktop app, or both:

| Component | Stack | When to use |
|-----------|-------|-------------|
| [Backend](./docs/backend.md) | FastAPI + SQLAlchemy + SQLite | Always required |
| [Frontend](./docs/frontend.md) | React 18 + TypeScript + Vite + Tailwind | Browser-based use |
| [Desktop](./docs/desktop.md) | SwiftUI + Swift 5.9 | Native macOS experience |

---

## Per-Component Docs

- [Backend](./docs/backend.md) — env vars, API endpoints, guardrails, caching, rate limiting
- [Frontend](./docs/frontend.md) — file layout, features explained, dev proxy
- [Desktop](./docs/desktop.md) — Swift app structure, features, global hotkey

---

## Project Structure

```
grammarcheck/
  backend/     # FastAPI server (15 source files, 98 tests)
  frontend/    # React SPA (16 source files)
  desktop/     # macOS SwiftUI app (16 source files)
  docs/        # Per-component documentation
  Makefile     # dev, install, test, lint, docker-up/down
  docker-compose.yml
```

## Requirements

- **Ollama** running locally on `http://localhost:11434`
- **Model**: `qwen3.5:9b-mlx` (or any — override via `GRAMMARCHECK_OLLAMA_MODEL`)
- **macOS 14+** for the desktop app
- Python 3.9+ / Node 18+ / Xcode 15+ as needed per component
