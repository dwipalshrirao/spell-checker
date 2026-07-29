"""latency_probe.py — Measure backend response latency percentiles."""

from __future__ import annotations

import asyncio
import time
from typing import Any

import httpx
from structlog import get_logger

from evals.scorer import compute_latency_score

logger = get_logger("grammarcheck.evals.latency_probe")


LATENCY_TEXT = (
    "The quick brown fox jumps over the lazy dog. "
    "She has been working at the company for five years. "
    "Despite the rain, the match continued as planned."
)


async def run_latency_probe(
    backend_url: str,
    n_requests: int = 20,
    timeout: float = 120.0,
) -> dict[str, Any]:
    latencies: list[float] = []

    async with httpx.AsyncClient(base_url=backend_url, timeout=timeout) as client:
        for i in range(n_requests):
            start = time.monotonic()
            try:
                resp = await client.post("/check", json={"text": LATENCY_TEXT})
                resp.raise_for_status()
                elapsed = (time.monotonic() - start) * 1000
                latencies.append(elapsed)
            except Exception as e:
                logger.warning("latency_request_failed", attempt=i, error=str(e))
                elapsed = (time.monotonic() - start) * 1000
                latencies.append(elapsed)

    score_result = compute_latency_score(latencies)
    threshold_breaches = []
    if score_result["p95_ms"] >= 15000:
        threshold_breaches.append(f"p95={score_result['p95_ms']:.0f}ms exceeds 15s threshold")
    if score_result["p99_ms"] >= 30000:
        threshold_breaches.append(f"p99={score_result['p99_ms']:.0f}ms exceeds 30s threshold")

    return {
        "passed": len(threshold_breaches) == 0,
        "score": score_result["score"],
        "verdict": score_result["verdict"],
        "requests_measured": n_requests,
        "metrics": {
            "p50_ms": score_result["p50_ms"],
            "p95_ms": score_result["p95_ms"],
            "p99_ms": score_result["p99_ms"],
            "mean_ms": score_result["mean_ms"],
            "min_ms": score_result["min_ms"],
            "max_ms": score_result["max_ms"],
        },
        "threshold_breaches": threshold_breaches,
    }
