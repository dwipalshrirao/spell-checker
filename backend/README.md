# Backend — FastAPI Server

FastAPI backend that wraps Ollama LLM calls, with caching, rate limiting, auth, metrics, and feedback storage.

## Directory Layout

```
backend/
  main.py               # FastAPI app entry (lifespan, middleware, routes)
  config.py             # Pydantic Settings via GRAMMARCHECK_* env vars
  database.py           # SQLAlchemy engine + session
  dependencies.py       # Optional API key verification
  requirements.txt      # fastapi, uvicorn, httpx, pydantic-settings, sqlalchemy, structlog
  requirements-dev.txt  # + pytest, pytest-asyncio, pytest-httpx, ruff
  pytest.ini
  Dockerfile
  models/
    request_models.py   # Pydantic schemas (CheckRequest, CheckResponse, Error, …)
    db_models.py        # ORM models (CheckRequest, Feedback)
  services/
    grammar_service.py  # Async Ollama LLM call via httpx
    cache_service.py    # In-memory LRU (256 entries), optional Redis
    guardrail_service.py# Input validation, PII detection, length limits
  routers/
    check.py            # POST /check
    health.py           # GET /health, GET /ready
    feedback.py         # POST /feedback
    metrics.py          # GET /metrics
  middleware/
    correlation_id.py   # X-Correlation-ID per request
    request_logger.py   # Structured request logging
    rate_limiter.py     # Sliding window rate limiter (20 req/min per IP)
  evals/                # Eval suite (runner, scorer, datasets, HTML reports)
  tests/
    6 test files, 98 tests total
```

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/` | Root info (version, model, status) |
| GET | `/health` | App + Ollama health |
| GET | `/ready` | Readiness probe (503 if Ollama down) |
| POST | `/check` | Check text for spelling/grammar errors |
| GET | `/metrics` | Request stats (count, avg/p95 latency) |
| POST | `/feedback` | Submit rating + comment |

## Environment Variables

All prefixed with `GRAMMARCHECK_`:

| Variable | Default | Description |
|----------|---------|-------------|
| `OLLAMA_URL` | `http://localhost:11434/api/generate` | Ollama API endpoint |
| `OLLAMA_MODEL` | `qwen3.5:9b-mlx` | LLM model name |
| `DATABASE_URL` | `sqlite:///./grammarcheck.db` | Database connection |
| `REDIS_URL` | _(none)_ | Optional Redis for cache |
| `CACHE_TTL_SECONDS` | `3600` | Cache TTL |
| `CACHE_MAX_SIZE` | `256` | Max cache entries |
| `RATE_LIMIT_PER_MINUTE` | `20` | Max requests/IP/minute |
| `API_KEY` | _(none)_ | API key for auth |
| `ENABLE_API_KEY` | `False` | Enable API key auth |
| `LOG_LEVEL` | `INFO` | Logging level |
| `MAX_INPUT_LENGTH` | `5000` | Max input chars |
| `ENABLE_METRICS` | `True` | Enable /metrics endpoint |
| `ENABLE_EVAL` | `True` | Enable eval mode |

## Commands

```bash
make dev       # uvicorn main:app --reload --port 8000
make install   # pip install -r requirements.txt
make test      # pytest -v (98 tests)
make lint      # ruff check + ruff format --check
make eval      # Run eval suite
make clean     # Remove __pycache__ + *.db
make docker-up # docker compose up -d
make docker-down
```

## How Features Work

### Grammar Check (`POST /check`)

1. Text arrives → guardrails validate (length < 5000, no PII, not empty)
2. Cache checked (hash of text + model name) → return cached result if hit
3. System prompt + user text sent to Ollama via `httpx.AsyncClient` with 120s timeout
4. Ollama returns JSON with `corrected_text`, `errors[]`, and `summary`
5. Response parsed, enriched with latency, saved to DB, cached, returned to client

### Health Check (`GET /health`)

- Calls `GET http://localhost:11434/api/tags` with 3s timeout
- Returns `status: "ok"` + model name if reachable, `status: "degraded"` otherwise
- No auth or rate limiting applied

### Feedback (`POST /feedback`)

- Accepts `request_id`, `rating` (1–5), optional `comment`
- Stored in SQLite `feedback` table for future analysis
- No validation beyond schema — intentionally silent on failure

### Caching

- In-memory LRU dict with configurable max size (256) and TTL (3600s)
- Keyed by hash of `(text, model)` tuple
- Skip cache by setting `Cache-Control: no-cache` header
- Falls back to SQLite if Redis is not configured

### Guardrails

- Empty text: rejects with 422
- Length check: `max_input_length` (default 5000 chars)
- PII detection: phone numbers, email addresses, SSNs flagged before model call
- Runs first in the middleware stack before the request reaches the route

### Rate Limiting

- Sliding window per IP address
- Default 20 requests/minute
- Exempt routes: `/health`, `/ready`, `/metrics`
- State stored in memory (or Redis if configured)

### Auth

- Disabled by default. Set `ENABLE_API_KEY=true` + `API_KEY=<key>` to enable
- When enabled, all routes except `/health` and `/ready` require `Authorization: Bearer <key>` header
