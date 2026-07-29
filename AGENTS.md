# GrammarCheck — Agent Guide

## What it is

Self-hosted grammar checker with 3 components:
- **Backend** — FastAPI server wrapping Ollama LLM calls
- **Frontend** — React SPA (Vite + Tailwind)
- **Desktop** — Native macOS SwiftUI menu-bar app

## Prerequisites

- **Ollama** running locally (`http://localhost:11434`)
- **Model pulled**: `ollama pull qwen3.5:9b-mlx` (or set via `GRAMMARCHECK_OLLAMA_MODEL`)
- Python deps: `pip install -r backend/requirements.txt`
- Frontend deps: `npm install` in `frontend/`
- Desktop: Xcode 15+ (macOS 14.0+)

## Commands

```bash
# Backend
make dev       # uvicorn main:app --reload --port 8000
make test      # pytest -v (98 tests)
make lint      # ruff check + ruff format --check
make eval      # Run eval suite

# Frontend
cd frontend && npm run dev    # Vite dev server, port 5173
cd frontend && npm run build  # tsc && vite build

# Desktop
cd desktop/GrammarCheck && xcodegen generate && open GrammarCheck.xcodeproj
```

## Non-obvious details

- Backend default model is `qwen3.5:9b-mlx` (not `gemma4`). Override via `GRAMMARCHECK_OLLAMA_MODEL`.
- System prompt lives in `backend/services/grammar_service.py:8-33`.
- 6 API routes: `/` `/health` `/ready` `/check` `/metrics` `/feedback`.
- Frontend proxies all API routes to `localhost:8000` in dev mode.
- Desktop generates `.xcodeproj` from `project.yml` via XcodeGen — never commit `.xcodeproj`.
- 16 Swift source files, 6 views, 1 view model, 3 services.

## Project Structure

```
backend/        # FastAPI (15 source files, 98 tests)
frontend/       # React (16 source files)
desktop/        # SwiftUI (16 source files)
docs/
  backend.md
  frontend.md
  desktop.md
Makefile
docker-compose.yml
grammar_check.py  # Phase 1 CLI
```

## Key Backend Config

All env vars prefixed with `GRAMMARCHECK_`. See `backend/config.py` for 15 configurable settings.
