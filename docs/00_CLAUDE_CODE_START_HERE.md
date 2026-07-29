# CLAUDE CODE INSTRUCTIONS
## GrammarCheck — Evaluation System Build

---

## Your Task

Build a complete evaluation system for an existing FastAPI grammar checker backend.
Read ALL spec documents before writing any code.

---

## Step 1: Read These Docs First (in order)

```
docs/00_PROJECT_OVERVIEW.md     — understand the full system
docs/01_EVAL_MASTER_PLAN.md     — eval architecture + CLI + confidence formula
docs/02_EVAL_SCORING_SPEC.md    — every scoring function with signatures + examples
docs/03_EVAL_DATASETS_SPEC.md   — all 170 test cases to build
docs/04_GUARDRAILS_SPEC.md      — input/output guardrail classes
docs/05_EVAL_REPORT_SPEC.md     — JSON + HTML report format
```

---

## Step 2: Understand the Existing Backend

The backend already exists. Do NOT modify any existing files.
Only CREATE new files in `backend/evals/` and `backend/services/guardrail_service.py`.

Existing backend structure (read-only context):
```
backend/
├── main.py           — FastAPI app, mounts all routers
├── config.py         — Settings (OLLAMA_URL, MODEL_NAME, etc.)
├── routers/
│   └── check.py      — POST /check endpoint
├── services/
│   └── grammar_service.py  — calls Ollama, returns parsed JSON
└── requirements.txt
```

The `/check` endpoint:
- Accepts: `POST {"text": "string", "model": "optional string"}`
- Returns:
```json
{
  "corrected_text": "string",
  "errors": [
    {"original": "str", "corrected": "str", "type": "str", "reason": "str"}
  ],
  "summary": "string",
  "latency_ms": 6200,
  "model_used": "gemma4:e4b",
  "cached": false
}
```
- Errors: 400 for invalid input, 503 if Ollama is down, 500 for model errors

---

## Step 3: Build Order

Follow this exact order to avoid dependency issues:

### 3.1 Install dependencies
```bash
pip install jiwer nltk numpy rich jinja2 httpx pytest pytest-asyncio
python -c "import nltk; nltk.download('punkt'); nltk.download('punkt_tab')"
```

### 3.2 Create dataset files
Build all 4 JSON datasets first — the runner depends on them.
- `backend/evals/datasets/core_cases.json` (80 cases — build ALL 80)
- `backend/evals/datasets/edge_cases.json` (30 cases)
- `backend/evals/datasets/guardrail_cases.json` (40 cases)
- `backend/evals/datasets/no_error_cases.json` (20 cases)

### 3.3 Build scorer.py
Pure functions, no I/O. Build + test this first.
```
backend/evals/scorer.py
backend/tests/test_scorer.py
```
Run: `pytest backend/tests/test_scorer.py -v`

### 3.4 Build guardrail_service.py
```
backend/services/guardrail_service.py
backend/tests/test_guardrails.py
```
Run: `pytest backend/tests/test_guardrails.py -v`

### 3.5 Build eval probes
```
backend/evals/guardrail_probe.py
backend/evals/latency_probe.py
```

### 3.6 Build runner.py
```
backend/evals/runner.py
```

### 3.7 Build report generator
```
backend/evals/report_generator.py
backend/evals/templates/report.html.j2   ← Jinja2 template
```

### 3.8 Build regression suite
```
backend/evals/regression_suite.py
```

### 3.9 Integration test
Run the full eval with backend + Ollama running:
```bash
python -m evals.runner --sample 10 --output both
```

---

## Step 4: Key Implementation Rules

### DO:
- Use `httpx.AsyncClient` for all HTTP calls to the backend
- Use `asyncio.Semaphore(3)` to limit concurrent requests to Ollama
- Use `rich.progress` for progress bars
- Use `structlog` for all logging (JSON format)
- Store raw API response in every eval result for debuggability
- Write type hints on every function
- Handle timeouts gracefully — if a case times out (>60s), mark as failed, continue
- Use `pathlib.Path` everywhere, not `os.path`
- Config via environment variables / .env (BACKEND_URL, OLLAMA_MODEL, etc.)

### DO NOT:
- Mock the `/check` endpoint in the eval runner — call the real backend
- Modify any existing backend files
- Use `requests` (sync) — use `httpx` (async)
- Hard-code URLs — read from config
- Print raw JSON to terminal — use `rich` tables
- Skip writing the datasets — all 170 cases must be real, not placeholder

### Error handling pattern:
```python
async def run_case(case: dict, client: httpx.AsyncClient) -> CaseResult:
    try:
        response = await client.post("/check", json={"text": case["input"]}, timeout=60.0)
        response.raise_for_status()
        return CaseResult(case_id=case["id"], response=response.json(), error=None)
    except httpx.TimeoutException:
        return CaseResult(case_id=case["id"], response=None, error="timeout")
    except httpx.HTTPStatusError as e:
        return CaseResult(case_id=case["id"], response=None, error=f"http_{e.response.status_code}")
    except Exception as e:
        return CaseResult(case_id=case["id"], response=None, error=str(e))
```

---

## Step 5: Verification Checklist

Before marking the task complete, verify:

- [ ] `pytest backend/tests/ -v` — all unit tests pass
- [ ] `python -m evals.runner --sample 10` — runs without errors
- [ ] JSON report is valid JSON with all required fields
- [ ] HTML report opens in browser and is readable
- [ ] `python -m evals.runner --help` — shows all CLI options
- [ ] Guardrail blocks prompt injection inputs
- [ ] Guardrail does NOT block legitimate text
- [ ] Empty input returns 400
- [ ] Input over 5000 chars returns 400
- [ ] Progress bar shows during run
- [ ] Terminal summary table displays after run

---

## Step 6: Files to Create (complete list)

```
backend/
├── services/
│   └── guardrail_service.py          ← NEW
├── evals/
│   ├── __init__.py                   ← NEW
│   ├── runner.py                     ← NEW
│   ├── scorer.py                     ← NEW
│   ├── guardrail_probe.py            ← NEW
│   ├── latency_probe.py              ← NEW
│   ├── regression_suite.py           ← NEW
│   ├── report_generator.py           ← NEW
│   ├── templates/
│   │   └── report.html.j2            ← NEW
│   ├── datasets/
│   │   ├── core_cases.json           ← NEW (80 cases)
│   │   ├── edge_cases.json           ← NEW (30 cases)
│   │   ├── guardrail_cases.json      ← NEW (40 cases)
│   │   └── no_error_cases.json       ← NEW (20 cases)
│   └── reports/
│       └── .gitkeep                  ← NEW
└── tests/
    ├── test_scorer.py                ← NEW
    └── test_guardrails.py            ← NEW
```

**Total: ~15 new files. Do not create any others unless needed.**

---

## Common Pitfalls to Avoid

1. **NLTK punkt tokenizer** — must be downloaded before running. Add a setup check in runner.py that downloads it if missing.

2. **WER library (jiwer)** — API changed in v3.0. Use `jiwer.wer(reference, hypothesis)` not the old `process_words` API.

3. **GLEU with empty reference** — if ground truth has no errors (empty expected_errors), skip GLEU calculation and return 1.0 if model also returned no errors.

4. **Ollama concurrency** — Ollama processes requests sequentially. The semaphore of 3 is to allow batching, but in practice Ollama queues them. Don't increase above 3.

5. **British English false positives** — the no_error_cases include British spellings (organised, colour). The false positive score should be lenient: if a case has `"allow_british_english": true`, a single error about spelling variant is a warning, not a failure.

6. **LLM judge temperature** — set to 0.0 for the judge call, not 0.1. You want deterministic scores.

7. **HTML report file size** — don't embed base64 images. Use SVG inline. Keep the HTML under 500KB.