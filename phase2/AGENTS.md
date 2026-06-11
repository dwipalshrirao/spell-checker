# GrammarCheck — Agent Guide

## What it is

Single-file Python CLI (`grammar_check.py`) that sends text to a local Ollama model and displays spelling/grammar corrections with explanations.

## Prerequisites (not in code — agent must know)

- **Ollama** must be running locally (`http://localhost:11434`)
- **Model must be pulled**: `ollama pull gemma4:e4b`
- Only dependency: `pip install requests`

## Commands

```bash
# Inline check
python grammar_check.py "your text here"

# Interactive mode (double-enter to submit)
python grammar_check.py

# Pipe input
cat file.txt | python grammar_check.py

# JSON output
python grammar_check.py --json "text"

# Custom model
python grammar_check.py --model gemma3:4b "text"
```

## Non-obvious details

- Default model in code is `"gemma4"` (not `"gemma4:e4b"` as README suggests). The `format: "json"` flag is sent to Ollama — model is expected to return valid JSON.
- System prompt lives inside `grammar_check.py:29-54` — edit there to change behavior.
- No tests, linter, typechecker, or formatter configured. No test framework.


## Project Phase 2 Details
- CREATICAL: Please read and follow the full repository structure and instructions outlined in [phase2_project_overview.md](./phase2_project_overview.md).

---

## Phase 2 Backend — `grammarcheck/backend/`

FastAPI backend exposing a REST API for grammar checking via local Ollama.

### Directory layout

```
grammarcheck/
├── .env.example
├── docker-compose.yml          # Backend + Ollama
├── Makefile                    # dev, install, test, lint, docker-up/down
└── backend/
    ├── main.py                 # FastAPI entry point (lifespan)
    ├── config.py               # Pydantic Settings (GRAMMARCHECK_* env vars)
    ├── database.py             # SQLAlchemy engine + session
    ├── dependencies.py         # API key verification (optional)
    ├── models/
    │   ├── request_models.py   # Pydantic schemas (CheckRequest, CheckResponse, Error, FeedbackCreate…)
    │   └── db_models.py        # ORM models (CheckRequest, Feedback)
    ├── services/
    │   ├── grammar_service.py  # Async Ollama LLM call via httpx (ported from Phase 1 CLI)
    │   ├── cache_service.py    # In-memory LRU cache (optional Redis)
    │   └── guardrail_service.py # Input validation, PII detection, length limits
    ├── routers/
    │   ├── check.py            # POST /check — main grammar check endpoint
    │   ├── health.py           # GET /health, GET /ready
    │   ├── feedback.py         # POST /feedback — store rating/comment
    │   └── metrics.py          # GET /metrics — request stats, latency
    ├── middleware/
    │   ├── correlation_id.py    # X-Correlation-ID header per request
    │   ├── request_logger.py   # Structured request logging
    │   └── rate_limiter.py     # Sliding window rate limiter (configurable)
    ├── evals/
    │   ├── eval_cases.json     # Ground-truth test cases
    │   ├── eval_runner.py      # Run eval suite against live model
    │   └── eval_report.py      # Generate HTML report from results
    ├── tests/
    │   ├── conftest.py
    │   ├── test_api_routes.py   # 8 integration tests
    │   ├── test_cache.py        # 5 unit tests
    │   ├── test_grammar_service.py  # 4 async unit tests (mocked httpx)
    │   └── test_guardrails.py   # 9 unit tests
    ├── requirements.txt         # fastapi, uvicorn, httpx, pydantic-settings, sqlalchemy, structlog
    ├── requirements-dev.txt     # + pytest, pytest-asyncio, pytest-httpx, ruff
    ├── pytest.ini
    └── Dockerfile
```

### API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/` | Root info |
| GET | `/health` | App + Ollama health check |
| GET | `/ready` | Readiness probe (503 if Ollama down) |
| POST | `/check` | Check text for spelling/grammar errors |
| GET | `/metrics` | Request stats (count, avg/p95 latency) |
| POST | `/feedback` | Submit rating + comment |

### Key details

- **Default model**: `gemma4` (same as Phase 1 CLI). Change via `GRAMMARCHECK_OLLAMA_MODEL`.
- **Core logic** in `services/grammar_service.py` — same system prompt as Phase 1, but using `httpx` (async) instead of `requests`.
- **Cache**: In-memory LRU (256 entries). Redis optional, set `GRAMMARCHECK_REDIS_URL` to enable.
- **Guardrails**: Empty text, length limits, PII detection (phone/email/SSN). Runs before model call.
- **Rate limiting**: 20 req/min per IP by default. Bypassed for `/health`, `/ready`, `/metrics`.
- **Auth**: Disabled by default. Set `GRAMMARCHECK_ENABLE_API_KEY=true` and `GRAMMARCHECK_API_KEY=<key>` to enable.
- **DB**: SQLite via SQLAlchemy, auto-creates tables on startup. Stores check requests + feedback.

### Commands

```bash
# Run dev server (hot-reload)
make dev
# or: uvicorn main:app --reload --port 8000

# Install deps
make install

# Run tests (25 tests, all pass)
make test

# Lint
make lint

# Eval suite (requires Ollama running with model pulled)
make eval

# Docker
make docker-up
make docker-down
```
