# GrammarCheck Backend — Evaluation Master Plan
## Document for Claude Code / OpenCode

---

## Context

The backend is already built (FastAPI + Ollama + Gemma). This document instructs
Claude Code to build a **complete evaluation system** that runs against the existing
backend and produces a confidence report before the frontend is developed.

The existing backend exposes:
- `POST /check` — main grammar check endpoint
- `GET /health` — Ollama + model status
- `GET /metrics` — basic system metrics

The eval system will be a **separate Python module** that:
1. Calls the live backend (no mocking)
2. Scores responses against ground truth
3. Runs guardrail probes
4. Measures latency and system health
5. Produces a machine-readable JSON report + human-readable HTML report

---

## What Claude Code Must Build

### New files to create (do NOT touch existing backend code):

```
backend/
└── evals/
    ├── __init__.py
    ├── runner.py              # Main eval orchestrator — entry point
    ├── scorer.py              # All scoring functions (F1, WER, GLEU, LLM-judge)
    ├── guardrail_probe.py     # Adversarial input tests
    ├── latency_probe.py       # Performance / stress tests
    ├── regression_suite.py    # Regression detection across runs
    ├── report_generator.py    # JSON + HTML report builder
    ├── datasets/
    │   ├── core_cases.json         # 80 hand-crafted test cases (build these)
    │   ├── edge_cases.json         # 30 tricky / boundary cases
    │   ├── guardrail_cases.json    # 40 adversarial inputs
    │   └── no_error_cases.json     # 20 clean texts (false positive tests)
    └── reports/                    # Auto-created, gitignored
        └── .gitkeep
```

---

## Eval Runner Architecture

```
runner.py (CLI entry point)
    │
    ├── Phase 1: Health Check
    │   └── Verify backend + Ollama are running before wasting time
    │
    ├── Phase 2: Correctness Eval
    │   ├── Load core_cases.json + edge_cases.json
    │   ├── POST each to /check
    │   ├── Score with scorer.py
    │   └── Store per-case results
    │
    ├── Phase 3: False Positive Eval
    │   ├── Load no_error_cases.json
    │   ├── POST each to /check
    │   └── Flag any case where model changed correct text
    │
    ├── Phase 4: Guardrail Eval
    │   ├── Load guardrail_cases.json
    │   ├── POST each to /check
    │   └── Check if backend blocked / sanitised correctly
    │
    ├── Phase 5: Latency Eval
    │   ├── Run 20 requests, measure p50/p95/p99
    │   └── Flag if any breach thresholds
    │
    ├── Phase 6: LLM-as-Judge
    │   ├── Sample 20 random results from Phase 2
    │   ├── Call /check again with judge prompt
    │   └── Score Faithfulness + Completeness + Explanation Quality
    │
    └── Phase 7: Report Generation
        ├── Aggregate all phase results
        ├── Compute overall confidence score
        ├── Write reports/report_{timestamp}.json
        └── Write reports/report_{timestamp}.html
```

---

## CLI Interface Claude Code Must Implement

```bash
# Run full eval suite
python -m evals.runner

# Run specific phases only
python -m evals.runner --phases correctness guardrails latency

# Run and compare against previous report (regression mode)
python -m evals.runner --compare reports/report_2024-01-10.json

# Run with a different backend URL (e.g. staging)
python -m evals.runner --backend-url http://localhost:8001

# Run with verbose per-case output
python -m evals.runner --verbose

# Run only N cases (quick smoke test)
python -m evals.runner --sample 10

# Output format
python -m evals.runner --output json   # default
python -m evals.runner --output html
python -m evals.runner --output both
```

---

## Overall Confidence Score Formula

The runner must compute a single **Production Confidence Score (0–100)**:

```
confidence_score = (
    correctness_f1          * 0.30   +   # Core quality
    recall_score            * 0.20   +   # Not missing errors
    false_positive_score    * 0.15   +   # Not over-correcting
    guardrail_score         * 0.15   +   # Safety
    latency_score           * 0.10   +   # Performance
    llm_judge_score         * 0.10       # Holistic quality
) * 100
```

**Thresholds for production readiness:**
```
≥ 85   → ✅ PRODUCTION READY
75–84  → ⚠️  NEEDS IMPROVEMENT (show which phase is failing)
60–74  → ❌ NOT READY (significant issues found)
< 60   → 🚨 CRITICAL ISSUES
```

---

## Dependencies to Add

Add to `backend/requirements.txt` or `pyproject.toml`:
```
# Eval-specific (not needed for running the app)
jiwer>=3.0.0          # WER calculation
nltk>=3.8             # BLEU/GLEU scoring
numpy>=1.26           # Score aggregation
rich>=13.0            # Beautiful terminal output
jinja2>=3.1           # HTML report templating
httpx>=0.27           # Async HTTP client for eval runner
pytest>=8.0           # Test runner
pytest-asyncio>=0.23  # Async test support
```

---

## Important Implementation Notes for Claude Code

1. **Call the real backend** — do not mock `/check`. Evals must run against live Ollama.
2. **Each eval case is independent** — no shared state between cases.
3. **Store raw responses** — save the full API response for every case in the JSON report so failures can be debugged.
4. **Graceful failure** — if one case fails (timeout, 500 error), log it and continue. Don't abort the whole suite.
5. **Determinism** — set `temperature: 0` or `temperature: 0.1` in the `/check` call during evals for reproducibility.
6. **Concurrency** — run eval cases with `asyncio.gather` with a semaphore of max 3 concurrent requests (Ollama can handle limited concurrency).
7. **Progress display** — use `rich` progress bar showing current phase, cases done/total, running score.
8. **Idempotent reports** — each run writes a new timestamped report. Never overwrite old reports (they're your regression baseline).