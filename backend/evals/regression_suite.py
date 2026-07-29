"""regression_suite.py — Compare current eval results against a previous report."""

from __future__ import annotations

from typing import Any


def compare_reports(
    current: dict[str, Any],
    previous: dict[str, Any],
) -> dict[str, Any]:
    deltas: dict[str, Any] = {
        "confidence_change": None,
        "phase_deltas": {},
        "regressions": [],
        "improvements": [],
    }

    cur_confidence = current.get("confidence_score", 0)
    prev_confidence = previous.get("confidence_score", 0)
    deltas["confidence_change"] = round(cur_confidence - prev_confidence, 1)

    phase_keys = ["correctness", "false_positives", "guardrails", "latency", "llm_judge"]
    for key in phase_keys:
        cur_phase = current.get("phases", {}).get(key, {})
        prev_phase = previous.get("phases", {}).get(key, {})
        cur_score = cur_phase.get("score", 0)
        prev_score = prev_phase.get("score", 0)
        change = round(cur_score - prev_score, 4)
        deltas["phase_deltas"][key] = {
            "previous": prev_score,
            "current": cur_score,
            "change": change,
        }
        if change < -0.02:
            deltas["regressions"].append({
                "phase": key,
                "metric": "score",
                "previous": prev_score,
                "current": cur_score,
                "change": change,
                "severity": "high" if change < -0.05 else "medium",
            })
        elif change > 0.02:
            deltas["improvements"].append({
                "phase": key,
                "metric": "score",
                "previous": prev_score,
                "current": cur_score,
                "change": change,
            })

    cur_latency = current.get("phases", {}).get("latency", {}).get("metrics", {})
    prev_latency = previous.get("phases", {}).get("latency", {}).get("metrics", {})
    for p in ("p50_ms", "p95_ms", "p99_ms"):
        cur_val = cur_latency.get(p, 0)
        prev_val = prev_latency.get(p, 0)
        diff = cur_val - prev_val
        if diff > 1000:
            deltas["regressions"].append({
                "phase": "latency",
                "metric": p,
                "previous": prev_val,
                "current": cur_val,
                "change": round(diff, 1),
                "severity": "high" if diff > 5000 else "medium",
            })

    return deltas
