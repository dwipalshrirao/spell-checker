# Eval Spec: Report Generation
## File: backend/evals/report_generator.py

---

## Overview

After all eval phases complete, the report generator produces:
1. `reports/report_{timestamp}.json` — machine-readable, used for regression comparisons
2. `reports/report_{timestamp}.html` — human-readable, open in browser

Both files are saved locally. The HTML report is the primary artifact a developer
looks at to decide "is this ready for production?"

---

## JSON Report Schema

```json
{
  "meta": {
    "timestamp": "2024-01-15T14:30:00Z",
    "run_id": "eval_20240115_143000",
    "backend_url": "http://localhost:8000",
    "model": "gemma4:e4b",
    "ollama_version": "0.3.x",
    "total_cases": 170,
    "total_duration_seconds": 284,
    "eval_version": "1.0.0"
  },
  "confidence_score": 87.4,
  "production_ready": true,
  "verdict": "PRODUCTION READY",
  "verdict_detail": "All phases passed thresholds. Weakest area: latency (p95=12.3s).",

  "phases": {
    "correctness": {
      "passed": true,
      "score": 0.91,
      "weight": 0.30,
      "cases_total": 80,
      "cases_passed": 73,
      "cases_failed": 7,
      "metrics": {
        "f1_mean": 0.89,
        "f1_std": 0.08,
        "wer_mean": 0.06,
        "gleu_mean": 0.88,
        "minimal_edit_score_mean": 0.94,
        "type_accuracy": 0.82
      },
      "failed_cases": [
        {
          "id": "core_022",
          "input": "...",
          "expected": "...",
          "got": "...",
          "f1": 0.33,
          "failure_reason": "model missed 2 of 3 errors"
        }
      ]
    },
    "false_positives": {
      "passed": true,
      "score": 0.95,
      "weight": 0.15,
      "cases_total": 20,
      "false_positives": 1,
      "false_positive_rate": 0.05,
      "fp_cases": [
        {
          "id": "clean_008",
          "input": "She organised the event...",
          "model_errors_returned": ["organised → organized"],
          "note": "British English flagged as error"
        }
      ]
    },
    "guardrails": {
      "passed": true,
      "score": 0.975,
      "weight": 0.15,
      "cases_total": 40,
      "correctly_blocked": 15,
      "correctly_passed": 22,
      "incorrectly_blocked": 1,
      "missed_attacks": 2,
      "injection_detection_rate": 0.90,
      "pii_detection_rate": 1.0,
      "false_positive_rate": 0.04,
      "failed_cases": []
    },
    "latency": {
      "passed": true,
      "score": 0.75,
      "weight": 0.10,
      "verdict": "acceptable",
      "requests_measured": 20,
      "metrics": {
        "p50_ms": 6200,
        "p95_ms": 12300,
        "p99_ms": 18400,
        "mean_ms": 7100,
        "min_ms": 4800,
        "max_ms": 19200
      },
      "threshold_breaches": []
    },
    "llm_judge": {
      "passed": true,
      "score": 0.84,
      "weight": 0.10,
      "cases_evaluated": 20,
      "metrics": {
        "faithfulness_mean": 4.7,
        "completeness_mean": 4.1,
        "explanation_quality_mean": 4.3,
        "conservatism_mean": 4.6,
        "composite_mean": 4.35
      }
    },
    "edge_cases": {
      "passed": true,
      "score": 0.83,
      "cases_total": 30,
      "cases_passed": 25,
      "notable_failures": []
    }
  },

  "recommendations": [
    {
      "priority": "medium",
      "phase": "latency",
      "message": "p95 latency is 12.3s. Consider pre-warming the model or using gemma3:4b for faster inference."
    },
    {
      "priority": "low",
      "phase": "false_positives",
      "message": "Model flags British English spellings. Add a note in the UI or adjust the system prompt."
    }
  ],

  "regression_vs_previous": null
}
```

---

## HTML Report Spec

Claude Code must generate a self-contained HTML file (no external CDN dependencies)
with inline CSS. The design should be clean and developer-friendly.

### Sections to include:

#### 1. Header
```
GrammarCheck Eval Report
Run ID: eval_20240115_143000
Model: gemma4:e4b | Backend: localhost:8000
Generated: 2024-01-15 14:30:00
```

#### 2. Confidence Score Card (prominent, top of page)
```
┌─────────────────────────────────┐
│                                 │
│        87.4 / 100               │
│   ✅ PRODUCTION READY           │
│                                 │
│  All phases passed thresholds   │
│  Weakest: latency (p95=12.3s)   │
│                                 │
└─────────────────────────────────┘
```
Color coding:
- ≥ 85: green background
- 75–84: yellow background
- < 75: red background

#### 3. Phase Summary Table
| Phase | Score | Status | Cases | Pass Rate |
|-------|-------|--------|-------|-----------|
| Correctness | 0.91 | ✅ | 80 | 91.25% |
| False Positives | 0.95 | ✅ | 20 | 95% |
| Guardrails | 0.975 | ✅ | 40 | 97.5% |
| Latency | 0.75 | ⚠️ | 20 req | p95=12.3s |
| LLM Judge | 0.84 | ✅ | 20 | 4.35/5 |
| Edge Cases | 0.83 | ✅ | 30 | 83.3% |

#### 4. Correctness Metrics Detail
Show bar charts (pure CSS, no JS) for:
- F1 Score distribution (histogram)
- Per-category F1 scores (spelling, grammar, punctuation, etc.)
- WER distribution

#### 5. Failed Cases (collapsible)
For each failed case, show:
```
▶ core_022 [FAILED] — F1: 0.33
  Input:    "She dont likes coffee and goed home."
  Expected: "She doesn't like coffee and went home."
  Got:      "She doesn't like coffee and went home."  ← wait, this matches?
  Reason:   Model missed error in 'goed' — returned it as 'gone' not 'went'
```

#### 6. Guardrail Results
- Injection attack table: which were caught, which weren't
- PII detection results
- False positive guardrail cases (legitimate text that was blocked)

#### 7. Latency Chart
Pure CSS horizontal bar chart:
```
p50  ██████░░░░░░░░░░░  6.2s
p95  ████████████░░░░░  12.3s  ← threshold line at 15s
p99  ████████████████░  18.4s
```

#### 8. LLM Judge Scores
Radar/spider chart using SVG (inline) showing:
- Faithfulness
- Completeness
- Explanation Quality
- Conservatism

#### 9. Recommendations
Color-coded cards:
- 🔴 High priority
- 🟡 Medium priority
- 🟢 Low priority / informational

#### 10. Regression Comparison (if --compare flag used)
Show delta table:
| Metric | Previous | Current | Change |
|--------|----------|---------|--------|
| F1 Mean | 0.86 | 0.89 | ▲ +0.03 |
| WER Mean | 0.08 | 0.06 | ▼ -0.02 ✅ |
| p95 Latency | 11.2s | 12.3s | ▲ +1.1s ⚠️ |

---

## Report Generator Implementation

```python
# backend/evals/report_generator.py

class ReportGenerator:

    def __init__(self, reports_dir: Path):
        self.reports_dir = reports_dir
        self.reports_dir.mkdir(exist_ok=True)

    def generate(
        self,
        eval_results: dict,        # aggregated results from all phases
        previous_report: dict | None = None,   # for regression comparison
    ) -> tuple[Path, Path]:
        """
        Returns: (json_path, html_path)
        """
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        run_id = f"eval_{timestamp}"

        report = self._build_report_dict(eval_results, previous_report, run_id)

        json_path = self.reports_dir / f"report_{timestamp}.json"
        html_path = self.reports_dir / f"report_{timestamp}.html"

        self._write_json(report, json_path)
        self._write_html(report, html_path)

        return json_path, html_path

    def _compute_confidence_score(self, phases: dict) -> float:
        """Apply the weighted formula from 01_EVAL_MASTER_PLAN.md"""

    def _build_regression_delta(self, current: dict, previous: dict) -> dict:
        """Compute deltas for key metrics. Flag regressions (negative deltas)."""

    def _write_html(self, report: dict, path: Path):
        """
        Use Jinja2 template. Template must be self-contained HTML
        with all CSS inline in <style> tags. No external dependencies.
        No JavaScript required (use CSS-only charts where possible).
        Light JS is OK for collapsible sections only.
        """
```

---

## Terminal Output (Rich)

When the runner finishes, print a summary to terminal using `rich`:

```
╭─────────────────────────────────────────────────────────────╮
│           GrammarCheck Eval Report — eval_20240115          │
├─────────────────────────────────────────────────────────────┤
│  Confidence Score:  87.4 / 100   ✅ PRODUCTION READY        │
├──────────────────┬──────────┬────────┬──────────────────────┤
│ Phase            │ Score    │ Status │ Notes                │
├──────────────────┼──────────┼────────┼──────────────────────┤
│ Correctness      │ 0.91     │ ✅     │ 73/80 cases passed   │
│ False Positives  │ 0.95     │ ✅     │ 1 FP (British EN)    │
│ Guardrails       │ 0.975    │ ✅     │ 2 injections missed  │
│ Latency          │ 0.75     │ ⚠️     │ p95=12.3s            │
│ LLM Judge        │ 0.84     │ ✅     │ 4.35/5 avg           │
│ Edge Cases       │ 0.83     │ ✅     │ 25/30 passed         │
├──────────────────┴──────────┴────────┴──────────────────────┤
│  Reports saved to:                                          │
│  📄 reports/report_20240115_143000.json                     │
│  🌐 reports/report_20240115_143000.html                     │
╰─────────────────────────────────────────────────────────────╯
```