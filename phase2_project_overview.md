GrammarCheck — Phase 2: Production-Ready Web Application
Master Project Overview

What We Are Building
A self-hosted, privacy-first grammar and spelling correction web application powered by a locally running Gemma LLM via Ollama. The user opens a browser, pastes or types English text, clicks "Check Grammar", and receives:
	•	The corrected version of their text
	•	A list of every error with type and plain-English reason
	•	A visual inline diff showing exactly what changed
Everything runs on the user's own machine. No text ever leaves the device.

High-Level Architecture
┌─────────────────────────────────────────────────────────────┐
│                        User's Browser                        │
│                    React Frontend (Vite)                     │
│         Text Input → Submit → Display Results + Diff         │
└──────────────────────────┬──────────────────────────────────┘
                           │ HTTP/REST (localhost:8000)
┌──────────────────────────▼──────────────────────────────────┐
│                   FastAPI Backend (Python)                    │
│                                                              │
│  ┌─────────────┐  ┌──────────────┐  ┌───────────────────┐  │
│  │  API Routes  │  │  Middleware   │  │  Background Tasks │  │
│  │  /check      │  │  Rate Limit   │  │  Async inference  │  │
│  │  /health     │  │  Auth (key)   │  │  Result caching   │  │
│  │  /feedback   │  │  Logging      │  │                   │  │
│  │  /metrics    │  │  Guardrails   │  │                   │  │
│  └──────┬───────┘  └──────────────┘  └───────────────────┘  │
│         │                                                     │
│  ┌──────▼──────────────────────────────────────────────────┐ │
│  │              Core Services Layer                         │ │
│  │  GrammarService │ CacheService │ EvalService │ LogService│ │
│  └──────┬──────────────────────────────────────────────────┘ │
└─────────┼───────────────────────────────────────────────────┘
          │ HTTP (localhost:11434)
┌─────────▼───────────────────────────────────────────────────┐
│                    Ollama (local daemon)                      │
│                  Model: gemma4:e4b (or gemma3:4b)            │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│                    Data Layer (local)                         │
│   SQLite DB        Redis (optional)     Log files            │
│   - requests       - response cache     - structured JSON    │
│   - feedback       - rate limit state   - error logs         │
│   - eval results                                             │
└─────────────────────────────────────────────────────────────┘

Technology Stack
Backend
Component
Technology
Reason
API Framework
FastAPI (Python 3.12)
Async, fast, auto-docs, Pydantic built-in
LLM Runtime
Ollama (local)
Local model serving, Metal GPU on Apple Silicon
Database
SQLite via SQLAlchemy
Zero-config, file-based, perfect for local app
Cache
Redis (optional) / in-memory LRU
Avoid re-running model on identical inputs
Task Queue
asyncio (built-in)
Async inference without Celery overhead for local app
Config
Pydantic Settings (.env)
Type-safe config, easy override
Frontend
Component
Technology
Reason
Framework
React 18 + TypeScript
Component model fits the diff/error UI well
Build tool
Vite
Fast HMR, simple config
Styling
Tailwind CSS
Utility-first, no CSS files to maintain
State
Zustand
Lightweight, no Redux boilerplate
HTTP client
Axios + React Query
Caching, loading states, error handling
Diff rendering
Custom component (word-level)
Inline highlights like Grammarly
Observability
Component
Technology
Structured logs
Python structlog → JSON files
Metrics endpoint
/metrics returning JSON (Prometheus-compatible)
Request tracing
Correlation IDs on every request
Eval dashboard
Simple HTML table at /eval/report

Directory Structure
grammarcheck/
├── backend/
│   ├── main.py                  # FastAPI app entry point
│   ├── config.py                # Pydantic Settings
│   ├── dependencies.py          # FastAPI dependency injection
│   ├── routers/
│   │   ├── check.py             # POST /check
│   │   ├── feedback.py          # POST /feedback
│   │   ├── health.py            # GET /health, /ready
│   │   └── metrics.py           # GET /metrics
│   ├── services/
│   │   ├── grammar_service.py   # Core LLM call logic (from Phase 1)
│   │   ├── cache_service.py     # LRU + Redis cache
│   │   ├── eval_service.py      # Evaluation runner
│   │   └── guardrail_service.py # Input/output safety checks
│   ├── models/
│   │   ├── request_models.py    # Pydantic request schemas
│   │   └── db_models.py         # SQLAlchemy ORM models
│   ├── middleware/
│   │   ├── rate_limiter.py      # Sliding window rate limiting
│   │   ├── request_logger.py    # Log every request/response
│   │   └── correlation_id.py    # Attach trace ID to each request
│   ├── database.py              # SQLAlchemy engine + session
│   ├── evals/
│   │   ├── eval_runner.py       # Run eval suite against model
│   │   ├── eval_cases.json      # Ground truth test cases
│   │   └── eval_report.py       # Generate HTML report
│   └── tests/
│       ├── test_grammar_service.py
│       ├── test_guardrails.py
│       ├── test_cache.py
│       └── test_api_routes.py
├── frontend/
│   ├── src/
│   │   ├── App.tsx
│   │   ├── components/
│   │   │   ├── TextEditor.tsx       # Input textarea with char count
│   │   │   ├── ResultPanel.tsx      # Corrected text + diff
│   │   │   ├── ErrorList.tsx        # Accordion list of errors
│   │   │   ├── DiffView.tsx         # Word-level diff renderer
│   │   │   ├── FeedbackBar.tsx      # 👍 👎 feedback buttons
│   │   │   └── StatusBar.tsx        # Model status, latency display
│   │   ├── hooks/
│   │   │   ├── useGrammarCheck.ts   # React Query mutation
│   │   │   └── useHealth.ts         # Poll /health
│   │   ├── store/
│   │   │   └── appStore.ts          # Zustand global state
│   │   ├── types/
│   │   │   └── api.ts               # TypeScript types matching backend
│   │   └── utils/
│   │       └── diff.ts              # Word diff utility
│   ├── index.html
│   ├── vite.config.ts
│   ├── tailwind.config.ts
│   └── tsconfig.json
├── docker-compose.yml           # One-command local setup
├── Makefile                     # Dev shortcuts
├── .env.example                 # All config variables documented
└── README.md

Key Design Decisions
	1	SQLite over Postgres — This is a local app. SQLite needs zero setup, stores data in a single file, and handles the expected concurrency (one user) perfectly. Can be swapped for Postgres later by changing the DB URL.
	2	Redis is optional — Cache falls back to an in-memory LRU dict if Redis isn't running. This keeps setup frictionless.
	3	No authentication in v1 — Since this runs on localhost, API key auth is scaffolded but disabled by default. Enable via .env when exposing over a network.
	4	Streaming not implemented in v1 — Grammarly-style streaming adds significant frontend complexity. v1 shows a loading spinner, v2 can add streaming.
	5	Guardrails are lightweight — No external moderation API. Guardrails use fast local heuristics (length limits, injection patterns, PII detection regex). Heavy moderation would defeat the privacy-first goal.

Non-Goals (Phase 2)
	•	Multi-user / multi-tenant support
	•	Authentication / user accounts
	•	Cloud deployment
	•	Support for languages other than English
	•	Real-time per-keystroke checking (Phase 3)
	•	Browser extension (Phase 3)
	•	Fine-tuned model (future)


