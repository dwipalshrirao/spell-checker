"""runner.py — Main eval orchestrator. Entry point: python -m evals.runner"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import httpx
import structlog
from rich.console import Console
from rich.progress import (
    BarColumn,
    Progress,
    SpinnerColumn,
    TextColumn,
    TimeElapsedColumn,
    TimeRemainingColumn,
)
from rich.table import Table

from evals.guardrail_probe import run_guardrail_probe
from evals.latency_probe import run_latency_probe
from evals.report_generator import ReportGenerator
from evals.scorer import (
    compute_false_positive_score,
    compute_gleu,
    compute_minimal_edit_score,
    compute_token_f1,
    compute_type_accuracy,
    compute_wer,
)

structlog.configure(
    processors=[
        structlog.stdlib.add_log_level,
        structlog.dev.ConsoleRenderer(),
    ],
    wrapper_class=structlog.stdlib.BoundLogger,
    context_class=dict,
    logger_factory=structlog.PrintLoggerFactory(),
    cache_logger_on_first_use=True,
)
logger = structlog.get_logger("grammarcheck.evals.runner")

PYTHON = sys.executable
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen3.5:9b-mlx")
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
DATASET_DIR = Path(__file__).parent / "datasets"

PHASE_WEIGHTS = {
    "correctness": 0.30,
    "recall": 0.20,
    "false_positives": 0.15,
    "guardrails": 0.15,
    "latency": 0.10,
    "llm_judge": 0.10,
}


@dataclass
class CaseResult:
    case_id: str
    category: str
    difficulty: str
    input: str
    expected_corrected: str
    expected_errors: list[dict]
    expected_error_count: int
    response: dict | None = None
    error: str | None = None
    latency_ms: float = 0.0


def load_dataset(filename: str) -> list[dict]:
    path = DATASET_DIR / filename
    with open(path) as f:
        return json.load(f)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="GrammarCheck Evaluation Runner",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  python -m evals.runner\n"
            "  python -m evals.runner --phases correctness guardrails\n"
            "  python -m evals.runner --sample 10 --output both\n"
            "  python -m evals.runner --compare reports/report_20240101_120000.json\n"
        ),
    )
    p.add_argument("--phases", nargs="+", default=None,
                    choices=["health", "correctness", "false_positives", "guardrails",
                             "latency", "llm_judge", "report"],
                    help="Phases to run (default: all)")
    p.add_argument("--backend-url", default=BACKEND_URL, help="Backend base URL")
    p.add_argument("--ollama-url", default=OLLAMA_URL, help="Ollama API URL")
    p.add_argument("--model", default=OLLAMA_MODEL, help="Ollama model name")
    p.add_argument("--sample", type=int, default=0,
                    help="Run only N cases per dataset (quick smoke test)")
    p.add_argument("--compare", type=str, default=None,
                    help="Path to previous JSON report for regression comparison")
    p.add_argument("--output", choices=["json", "html", "both"], default="both",
                    help="Report output format")
    p.add_argument("--verbose", action="store_true", help="Print per-case results")
    p.add_argument("--concurrency", type=int, default=3,
                    help="Max concurrent requests (default: 3)")
    return p.parse_args(argv)


async def phase_health_check(args: argparse.Namespace,
                              progress: Progress | None = None,
                              parent_task: int | None = None) -> dict[str, Any]:
    logger.info("phase_start", phase="health_check")
    async with httpx.AsyncClient(base_url=args.backend_url, timeout=10.0) as client:
        try:
            resp = await client.get("/health")
            body = resp.json()
            logger.info("backend_healthy", status=resp.status_code, body=body)
            ready = False
            try:
                ready_resp = await client.get("/ready")
                ready = ready_resp.status_code == 200
            except Exception:
                pass
            return {
                "passed": resp.status_code == 200 and ready,
                "status": resp.status_code,
                "body": body,
                "ready": ready,
            }
        except httpx.ConnectError:
            msg = (
                f"Cannot connect to backend at {args.backend_url}. "
                "Start the server with: make dev  (or  uvicorn main:app --reload --port 8000)"
            )
            logger.error("backend_unhealthy", error=msg)
            return {"passed": False, "error": msg}
        except Exception as e:
            logger.error("backend_unhealthy", error=str(e))
            return {"passed": False, "error": str(e)}


async def phase_correctness(args: argparse.Namespace,
                             progress: Progress | None = None,
                             parent_task: int | None = None) -> dict[str, Any]:
    logger.info("phase_start", phase="correctness")
    core_cases = load_dataset("core_cases.json")
    edge_cases = load_dataset("edge_cases.json")
    all_cases = core_cases + edge_cases

    if args.sample:
        all_cases = all_cases[:args.sample]

    results = await _run_cases(all_cases, args, progress, parent_task)

    f1_scores = []
    wer_scores = []
    gleu_scores = []
    edit_scores = []
    type_accuracies = []
    failed_cases = []

    for r in results:
        if r.error or r.response is None:
            failed_cases.append({
                "id": r.case_id, "input": r.input[:200],
                "expected": r.expected_corrected[:200], "got": None,
                "f1": 0.0, "failure_reason": r.error or "no_response",
            })
            continue

        model_corrected = r.response.get("corrected_text", "")
        model_errors = r.response.get("errors", [])

        f1 = compute_token_f1(r.input, model_corrected, r.expected_corrected)
        wer = compute_wer(model_corrected, r.expected_corrected)
        gleu = compute_gleu(r.input, model_corrected, r.expected_corrected)
        edit = compute_minimal_edit_score(r.input, model_corrected, r.expected_errors)
        ta = compute_type_accuracy(model_errors, r.expected_errors)

        f1_scores.append(f1["f1"])
        wer_scores.append(wer["wer"])
        gleu_scores.append(gleu["gleu"])
        edit_scores.append(edit["score"])
        type_accuracies.append(ta["type_accuracy"])

        is_failed = f1["f1"] < 0.5 or wer["wer"] > 0.2
        if is_failed:
            failed_cases.append({
                "id": r.case_id, "input": r.input[:200],
                "expected": r.expected_corrected[:200],
                "got": model_corrected[:200],
                "f1": f1["f1"],
                "failure_reason": f"f1={f1['f1']:.2f}, wer={wer['wer']:.2f}",
            })

    import numpy as np
    f1_mean = float(np.mean(f1_scores)) if f1_scores else 0.0
    f1_std = float(np.std(f1_scores)) if f1_scores else 0.0
    wer_mean = float(np.mean(wer_scores)) if wer_scores else 1.0
    gleu_mean = float(np.mean(gleu_scores)) if gleu_scores else 0.0

    passed = len(failed_cases) == 0
    score = f1_mean * 0.5 + (1.0 - wer_mean) * 0.3 + gleu_mean * 0.2

    return {
        "passed": passed,
        "score": round(score, 4),
        "cases_total": len(results),
        "cases_passed": len(results) - len(failed_cases),
        "cases_failed": len(failed_cases),
        "metrics": {
            "f1_mean": round(f1_mean, 4),
            "f1_std": round(f1_std, 4),
            "wer_mean": round(wer_mean, 4),
            "gleu_mean": round(gleu_mean, 4),
            "minimal_edit_score_mean": round(float(np.mean(edit_scores)), 4) if edit_scores else 1.0,
            "type_accuracy": round(float(np.mean(type_accuracies)), 4) if type_accuracies else 1.0,
        },
        "failed_cases": failed_cases,
    }


async def phase_false_positives(args: argparse.Namespace,
                                 progress: Progress | None = None,
                                 parent_task: int | None = None) -> dict[str, Any]:
    logger.info("phase_start", phase="false_positives")
    no_error_cases = load_dataset("no_error_cases.json")
    if args.sample:
        no_error_cases = no_error_cases[:args.sample]

    results = await _run_cases(no_error_cases, args, progress, parent_task)

    fp_inputs = []
    for r in results:
        fp_inputs.append({
            "input": r.input,
            "response": r.response or {"errors": [], "corrected_text": r.input},
        })

    fp_score = compute_false_positive_score(fp_inputs)
    passed = fp_score["false_positive_rate"] <= 0.10

    return {
        "passed": passed,
        "score": fp_score["score"],
        "cases_total": len(results),
        "false_positives": len(fp_score["fp_cases"]),
        "false_positive_rate": fp_score["false_positive_rate"],
        "fp_cases": fp_score["fp_cases"],
    }


async def phase_guardrails(args: argparse.Namespace,
                            progress: Progress | None = None,
                            parent_task: int | None = None) -> dict[str, Any]:
    logger.info("phase_start", phase="guardrails")
    guardrail_cases = load_dataset("guardrail_cases.json")
    if args.sample:
        guardrail_cases = guardrail_cases[:args.sample]

    result = await run_guardrail_probe(
        cases=guardrail_cases,
        backend_url=args.backend_url,
        concurrency=args.concurrency,
    )
    result["passed"] = result["score"] >= 0.85
    return result


async def phase_latency(args: argparse.Namespace,
                         progress: Progress | None = None,
                         parent_task: int | None = None) -> dict[str, Any]:
    logger.info("phase_start", phase="latency")
    n_requests = max(5, args.sample) if args.sample else 20
    result = await run_latency_probe(
        backend_url=args.backend_url,
        n_requests=n_requests,
    )
    return result


async def phase_llm_judge(args: argparse.Namespace,
                           progress: Progress | None = None,
                           parent_task: int | None = None) -> dict[str, Any]:
    logger.info("phase_start", phase="llm_judge")
    core_cases = load_dataset("core_cases.json")
    sample_cases = core_cases[:20]
    if args.sample and args.sample < 20:
        sample_cases = sample_cases[:args.sample]

    results = await _run_cases(sample_cases, args, progress, parent_task)

    faithfulness_scores = []
    completeness_scores = []
    explanation_scores = []
    conservatism_scores = []

    for r in results:
        if r.error or r.response is None:
            continue

        judge_result = await _llm_judge_single(r, args.ollama_url, args.model)
        if judge_result:
            faithfulness_scores.append(judge_result["faithfulness"])
            completeness_scores.append(judge_result["completeness"])
            explanation_scores.append(judge_result["explanation_quality"])
            conservatism_scores.append(judge_result["conservatism"])

    import numpy as np
    f_mean = float(np.mean(faithfulness_scores)) if faithfulness_scores else 0.0
    c_mean = float(np.mean(completeness_scores)) if completeness_scores else 0.0
    e_mean = float(np.mean(explanation_scores)) if explanation_scores else 0.0
    co_mean = float(np.mean(conservatism_scores)) if conservatism_scores else 0.0
    composite_mean = (f_mean * 0.3 + c_mean * 0.35 + e_mean * 0.2 + co_mean * 0.15) / 5

    score = composite_mean
    passed = score >= 0.7

    from evals.scorer import llm_judge_composite
    return {
        "passed": passed,
        "score": round(score, 4),
        "cases_evaluated": len(results),
        "metrics": {
            "faithfulness_mean": round(f_mean, 2),
            "completeness_mean": round(c_mean, 2),
            "explanation_quality_mean": round(e_mean, 2),
            "conservatism_mean": round(co_mean, 2),
            "composite_mean": round(composite_mean, 2),
        },
    }


async def _llm_judge_single(
    result: CaseResult,
    ollama_url: str,
    model: str,
) -> dict[str, float] | None:
    prompt = (
        "You are an expert evaluator of grammar correction systems.\n"
        "Score the CORRECTED text on these dimensions (1-5 each):\n\n"
        "FAITHFULNESS: Does the corrected text preserve the original meaning?\n"
        "COMPLETENESS: Were all errors caught and fixed?\n"
        "EXPLANATION_QUALITY: Are the error explanations accurate and useful?\n"
        "CONSERVATISM: Did it avoid changing text that was already correct?\n\n"
        "Return ONLY valid JSON:\n"
        '{"faithfulness": N, "completeness": N, "explanation_quality": N, "conservatism": N, "reasoning": "one sentence"}\n\n'
        f"ORIGINAL: {result.input}\n"
        f"CORRECTED: {(result.response or {}).get('corrected_text', '')}\n"
        f"EXPECTED: {result.expected_corrected}\n"
        f"ERRORS_GIVEN: {json.dumps((result.response or {}).get('errors', []))}"
    )
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "format": "json",
        "options": {"temperature": 0.0},
    }
    logger.info("llm_judge_calling", case_id=result.case_id,
                ollama_url=ollama_url, model=model)
    try:
        async with httpx.AsyncClient(base_url=ollama_url, timeout=120.0) as client:
            resp = await client.post("/api/generate", json=payload)
            resp.raise_for_status()
            body = resp.json()
            raw = body.get("response", "{}")
            parsed = json.loads(raw)
            return {
                "faithfulness": float(parsed.get("faithfulness", 3)),
                "completeness": float(parsed.get("completeness", 3)),
                "explanation_quality": float(parsed.get("explanation_quality", 3)),
                "conservatism": float(parsed.get("conservatism", 3)),
            }
    except Exception as e:
        logger.warning("llm_judge_failed", case_id=result.case_id,
                       ollama_url=ollama_url, model=model, error=str(e))
        return None


async def _run_cases(cases: list[dict], args: argparse.Namespace,
                     progress: Progress | None = None,
                     parent_task: int | None = None) -> list[CaseResult]:
    sem = asyncio.Semaphore(args.concurrency)
    case_task: int | None = None
    if progress is not None and parent_task is not None:
        case_task = progress.add_task("  Cases...", total=len(cases))

    results: list[CaseResult] = []
    async with httpx.AsyncClient(base_url=args.backend_url, timeout=120.0) as client:
        sem_local = sem
        async def run_one(c):
            r = await _run_single_case(c, client, sem_local)
            logger.info("case_complete", case_id=r.case_id,
                        status="ok" if not r.error else "fail",
                        latency_ms=f"{r.latency_ms:.0f}")
            if progress is not None and case_task is not None:
                progress.advance(case_task)
            return r
        tasks = [run_one(c) for c in cases]
        results = await asyncio.gather(*tasks)

    if args.verbose:
        console = Console()
        table = Table(title="Per-Case Results")
        table.add_column("ID", style="dim")
        table.add_column("Status")
        table.add_column("Latency")
        table.add_column("Errors Found")
        for r in results:
            status = "✅" if not r.error else "❌"
            n_errors = len((r.response or {}).get("errors", [])) if r.response else 0
            latency = f"{r.latency_ms:.0f}ms" if r.latency_ms else "-"
            table.add_row(r.case_id, status, latency, str(n_errors))
        console.print(table)

    return results


async def _run_single_case(
    case: dict,
    client: httpx.AsyncClient,
    sem: asyncio.Semaphore,
) -> CaseResult:
    case_id = case["id"]
    text = case["input"]
    expected_corrected = case.get("expected_corrected", text)
    expected_errors = case.get("expected_errors", [])
    expected_error_count = case.get("expected_error_count", len(expected_errors))

    async with sem:
        start = time.monotonic()
        try:
            resp = await client.post("/check", json={"text": text})
            resp.raise_for_status()
            body = resp.json()
            latency = (time.monotonic() - start) * 1000
            return CaseResult(
                case_id=case_id,
                category=case.get("category", "unknown"),
                difficulty=case.get("difficulty", "medium"),
                input=text,
                expected_corrected=expected_corrected,
                expected_errors=expected_errors,
                expected_error_count=expected_error_count,
                response=body,
                error=None,
                latency_ms=latency,
            )
        except httpx.TimeoutException:
            return CaseResult(
                case_id=case_id, category=case.get("category", "unknown"),
                difficulty=case.get("difficulty", "medium"),
                input=text, expected_corrected=expected_corrected,
                expected_errors=expected_errors,
                expected_error_count=expected_error_count,
                error="timeout", latency_ms=(time.monotonic() - start) * 1000,
            )
        except httpx.HTTPStatusError as e:
            return CaseResult(
                case_id=case_id, category=case.get("category", "unknown"),
                difficulty=case.get("difficulty", "medium"),
                input=text, expected_corrected=expected_corrected,
                expected_errors=expected_errors,
                expected_error_count=expected_error_count,
                error=f"http_{e.response.status_code}",
                latency_ms=(time.monotonic() - start) * 1000,
            )
        except Exception as e:
            return CaseResult(
                case_id=case_id, category=case.get("category", "unknown"),
                difficulty=case.get("difficulty", "medium"),
                input=text, expected_corrected=expected_corrected,
                expected_errors=expected_errors,
                expected_error_count=expected_error_count,
                error=str(e), latency_ms=(time.monotonic() - start) * 1000,
            )


async def main(argv: list[str] | None = None) -> dict[str, Any]:
    args = parse_args(argv)
    total_start = time.monotonic()
    phases = ["health", "correctness", "false_positives", "guardrails", "latency", "llm_judge", "report"]

    if args.phases:
        phases = args.phases

    results: dict[str, Any] = {
        "backend_url": args.backend_url,
        "model": args.model,
        "ollama_version": "unknown",
        "total_duration_seconds": 0,
        "phases": {},
    }

    console = Console()
    progress = Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        TimeElapsedColumn(),
        TimeRemainingColumn(),
        console=console,
    )

    with progress:
        phase_names = [p for p in phases if p != "report"]
        task = progress.add_task("Running eval phases...", total=len(phase_names))

        phase_map: dict[str, Any] = {
            "health": lambda a: phase_health_check(a),
            "correctness": lambda a: phase_correctness(a, progress, task),
            "false_positives": lambda a: phase_false_positives(a, progress, task),
            "guardrails": lambda a: phase_guardrails(a, progress, task),
            "latency": lambda a: phase_latency(a, progress, task),
            "llm_judge": lambda a: phase_llm_judge(a, progress, task),
        }

        backend_available = True

        for phase_name in phase_names:
            progress.update(task, description=f"Phase: {phase_name}")
            logger.info("running_phase", phase=phase_name)
            handler = phase_map.get(phase_name)
            if handler:
                if not backend_available and phase_name not in ("health", "report"):
                    phase_result = {
                        "passed": False, "score": 0.0,
                        "error": "skipped: backend unavailable",
                        "cases_total": 0, "cases_passed": 0, "cases_failed": 0,
                        "failed_cases": [], "fp_cases": [],
                        "metrics": {},
                    }
                else:
                    try:
                        phase_result = await handler(args)
                    except Exception as e:
                        logger.error("phase_failed", phase=phase_name, error=str(e))
                        phase_result = {"passed": False, "score": 0.0, "error": str(e)}

                if phase_name == "health":
                    backend_available = phase_result.get("passed", False)
                    if not backend_available:
                        console.print("[red]✗ Backend is not reachable. Skipping remaining phases.[/]")
                        logger.error("backend_unreachable", url=args.backend_url)

                results["phases"][phase_name] = phase_result
            progress.advance(task)

    results["total_duration_seconds"] = time.monotonic() - total_start

    if "report" in phases:
        prev_report = None
        if args.compare:
            try:
                with open(args.compare) as f:
                    prev_report = json.load(f)
                logger.info("loaded_previous_report", path=args.compare)
            except Exception as e:
                logger.warning("could_not_load_previous_report", error=str(e))

        gen = ReportGenerator()
        json_path, html_path = gen.generate(results, previous_report=prev_report)
        gen.print_terminal_summary(
            json.loads(json_path.read_text()),
            json_path,
            html_path,
        )

        if args.output == "html":
            json_path.unlink(missing_ok=True)
        elif args.output == "json":
            html_path.unlink(missing_ok=True)
    else:
        console.print("[yellow]Report phase skipped — no reports generated.[/]")

    return results


if __name__ == "__main__":
    asyncio.run(main())
