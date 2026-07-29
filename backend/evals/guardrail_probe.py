"""guardrail_probe.py — Run adversarial guardrail cases against the live backend."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Any

import httpx
from structlog import get_logger

logger = get_logger("grammarcheck.evals.guardrail_probe")


@dataclass
class GuardrailProbeResult:
    case_id: str
    category: str
    severity: str
    expected_behavior: str
    expected_statuses: list[int]
    actual_status: int
    response_body: dict | None
    passed: bool
    failure_reason: str = ""


async def run_guardrail_probe(
    cases: list[dict],
    backend_url: str,
    concurrency: int = 3,
    timeout: float = 30.0,
) -> dict[str, Any]:
    sem = asyncio.Semaphore(concurrency)
    async with httpx.AsyncClient(base_url=backend_url, timeout=timeout) as client:
        tasks = [_run_single(c, client, sem) for c in cases]
        results = await asyncio.gather(*tasks)

    total = len(results)
    passed = sum(1 for r in results if r.passed)
    correctly_blocked = sum(
        1 for r in results if r.expected_behavior in ("blocked", "blocked_or_sanitised")
        and r.actual_status in (400, 422)
    )
    correctly_passed = sum(
        1 for r in results if r.expected_behavior in ("passed", "warned", "warned_or_blocked")
        and r.actual_status == 200
    )
    incorrectly_blocked = sum(
        1 for r in results if r.expected_behavior in ("passed", "warned")
        and r.actual_status not in (200,)
    )
    missed_attacks = sum(
        1 for r in results if r.expected_behavior in ("blocked", "blocked_or_sanitised")
        and r.actual_status == 200
        and r.severity == "high"
    )
    injection_cases = [r for r in results if r.category == "prompt_injection"]
    injection_detection_rate = (
        sum(1 for r in injection_cases if r.passed) / len(injection_cases)
        if injection_cases else 1.0
    )
    pii_cases = [r for r in results if r.category == "pii"]
    pii_detection_rate = (
        sum(1 for r in pii_cases if r.passed) / len(pii_cases)
        if pii_cases else 1.0
    )

    return {
        "passed": passed == total,
        "score": round(passed / total, 4) if total else 1.0,
        "cases_total": total,
        "correctly_blocked": correctly_blocked,
        "correctly_passed": correctly_passed,
        "incorrectly_blocked": incorrectly_blocked,
        "missed_attacks": missed_attacks,
        "injection_detection_rate": round(injection_detection_rate, 4),
        "pii_detection_rate": round(pii_detection_rate, 4),
        "false_positive_rate": round(incorrectly_blocked / total, 4) if total else 0.0,
        "failed_cases": [
            {
                "id": r.case_id,
                "category": r.category,
                "expected": r.expected_behavior,
                "actual_status": r.actual_status,
                "reason": r.failure_reason,
            }
            for r in results if not r.passed
        ],
    }


async def _run_single(
    case: dict,
    client: httpx.AsyncClient,
    sem: asyncio.Semaphore,
) -> GuardrailProbeResult:
    case_id = case["id"]
    category = case.get("category", "unknown")
    severity = case.get("severity", "low")
    expected = case.get("expected_behavior", "passed")
    expected_statuses = case.get("expected_http_status", [200])
    text_input = case.get("input", "")

    async with sem:
        try:
            resp = await client.post("/check", json={"text": text_input}, timeout=60.0)
            actual_status = resp.status_code
            body: dict | None = None
            try:
                body = resp.json()
            except Exception:
                pass
        except httpx.TimeoutException:
            return GuardrailProbeResult(
                case_id=case_id, category=category, severity=severity,
                expected_behavior=expected, expected_statuses=expected_statuses,
                actual_status=0, response_body=None, passed=False,
                failure_reason="timeout",
            )
        except Exception as e:
            return GuardrailProbeResult(
                case_id=case_id, category=category, severity=severity,
                expected_behavior=expected, expected_statuses=expected_statuses,
                actual_status=0, response_body=None, passed=False,
                failure_reason=str(e),
            )

    passed = actual_status in expected_statuses
    failure_reason = ""
    if not passed:
        failure_reason = (
            f"Expected status {expected_statuses}, got {actual_status}"

        )

    return GuardrailProbeResult(
        case_id=case_id, category=category, severity=severity,
        expected_behavior=expected, expected_statuses=expected_statuses,
        actual_status=actual_status, response_body=body,
        passed=passed, failure_reason=failure_reason,
    )
