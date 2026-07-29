"""report_generator.py — Build JSON and HTML evaluation reports."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import jinja2
from rich.console import Console
from rich.table import Table

from evals.scorer import compute_confidence_score

REPORTS_DIR = Path(__file__).parent / "reports"
TEMPLATES_DIR = Path(__file__).parent / "templates"


class ReportGenerator:

    def __init__(self, reports_dir: Path = REPORTS_DIR):
        self.reports_dir = reports_dir
        self.reports_dir.mkdir(exist_ok=True)

    def generate(
        self,
        eval_results: dict[str, Any],
        previous_report: dict[str, Any] | None = None,
    ) -> tuple[Path, Path]:
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        run_id = f"eval_{timestamp}"

        report = self._build_report_dict(eval_results, previous_report, run_id)

        json_path = self.reports_dir / f"report_{timestamp}.json"
        html_path = self.reports_dir / f"report_{timestamp}.html"

        self._write_json(report, json_path)
        self._write_html(report, html_path)

        return json_path, html_path

    def _build_report_dict(
        self,
        eval_results: dict[str, Any],
        previous_report: dict[str, Any] | None,
        run_id: str,
    ) -> dict[str, Any]:
        phases = eval_results.get("phases", {})
        confidence_data = compute_confidence_score(phases)
        confidence_score = confidence_data["confidence_score"]

        total_cases = (
            phases.get("correctness", {}).get("cases_total", 0)
            + phases.get("false_positives", {}).get("cases_total", 0)
            + phases.get("guardrails", {}).get("cases_total", 0)
        )

        recommendations = self._build_recommendations(phases)

        regression_vs_previous = None
        if previous_report is not None:
            from evals.regression_suite import compare_reports
            regression_vs_previous = compare_reports(confidence_data, previous_report)

        return {
            "meta": {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "run_id": run_id,
                "backend_url": eval_results.get("backend_url", "http://localhost:8000"),
                "model": eval_results.get("model", "gemma4:e4b"),
                "ollama_version": eval_results.get("ollama_version", "unknown"),
                "total_cases": total_cases,
                "total_duration_seconds": round(eval_results.get("total_duration_seconds", 0), 1),
                "eval_version": "2.0.0",
            },
            "confidence_score": confidence_score,
            "production_ready": confidence_score >= 85,
            "verdict": confidence_data["verdict"],
            "verdict_detail": self._verdict_detail(phases),
            "phases": phases,
            "recommendations": recommendations,
            "regression_vs_previous": regression_vs_previous,
        }

    def _verdict_detail(self, phases: dict[str, Any]) -> str:
        parts = []
        if phases.get("correctness", {}).get("score", 0) < 0.8:
            parts.append("Correctness below threshold")
        if phases.get("false_positives", {}).get("score", 0) < 0.9:
            parts.append("Too many false positives")
        if phases.get("latency", {}).get("verdict", "") in ("slow", "critical"):
            lat = phases["latency"]["metrics"]
            parts.append(f"Weakest area: latency (p95={lat.get('p95_ms', 0):.0f}ms)")
        return "; ".join(parts) if parts else "All phases passed thresholds."

    def _build_recommendations(self, phases: dict[str, Any]) -> list[dict[str, str]]:
        recs = []
        latency = phases.get("latency", {})
        if latency.get("verdict") in ("slow", "critical"):
            recs.append({
                "priority": "medium",
                "phase": "latency",
                "message": (
                    f"p95 latency is {latency.get('metrics', {}).get('p95_ms', 0):.0f}ms. "
                    "Consider pre-warming the model or using gemma3:4b for faster inference."
                ),
            })
        fp = phases.get("false_positives", {})
        if fp.get("false_positive_rate", 0) > 0.05:
            recs.append({
                "priority": "low",
                "phase": "false_positives",
                "message": "Model flags valid text. Check for British English false positives.",
            })
        guard = phases.get("guardrails", {})
        if guard.get("missed_attacks", 0) > 0:
            recs.append({
                "priority": "high",
                "phase": "guardrails",
                "message": f"{guard['missed_attacks']} high-severity attacks not blocked.",
            })
        return recs

    def _write_json(self, report: dict[str, Any], path: Path) -> None:
        with open(path, "w") as f:
            json.dump(report, f, indent=2, default=str)

    def _write_html(self, report: dict[str, Any], path: Path) -> None:
        env = jinja2.Environment(
            loader=jinja2.FileSystemLoader(str(TEMPLATES_DIR)),
            autoescape=True,
        )
        template = env.get_template("report.html.j2")
        html = template.render(report=report)
        with open(path, "w") as f:
            f.write(html)

    def print_terminal_summary(self, report: dict[str, Any], json_path: Path, html_path: Path) -> None:
        console = Console()
        confidence = report["confidence_score"]
        verdict = report["verdict"]

        if confidence >= 85:
            status_emoji = "✅"
        elif confidence >= 75:
            status_emoji = "⚠️"
        elif confidence >= 60:
            status_emoji = "❌"
        else:
            status_emoji = "🚨"

        table = Table(title=f"GrammarCheck Eval Report — {report['meta']['run_id']}")
        table.add_column("Phase", style="cyan")
        table.add_column("Score", justify="right")
        table.add_column("Status", justify="center")
        table.add_column("Notes", style="dim")

        phases = report["phases"]
        phase_notes = {
            "correctness": f"{phases.get('correctness', {}).get('cases_passed', 0)}/{phases.get('correctness', {}).get('cases_total', 0)} cases passed",
            "false_positives": f"FP rate: {phases.get('false_positives', {}).get('false_positive_rate', 0):.0%}",
            "guardrails": f"{phases.get('guardrails', {}).get('missed_attacks', 0)} missed attacks",
            "latency": f"p95={phases.get('latency', {}).get('metrics', {}).get('p95_ms', 0):.0f}ms",
            "llm_judge": f"{phases.get('llm_judge', {}).get('metrics', {}).get('composite_mean', 0):.2f}/5 avg",
        }

        for phase_name in ("correctness", "false_positives", "guardrails", "latency", "llm_judge"):
            phase = phases.get(phase_name, {})
            score = phase.get("score", 0)
            passed_ = phase.get("passed", False)
            status = "✅" if passed_ else "❌"
            notes = phase_notes.get(phase_name, "")
            table.add_row(phase_name.replace("_", " ").title(), f"{score:.3f}", status, notes)

        console.print()
        console.print(f"[bold]Confidence Score:[/] {confidence:.1f} / 100   {status_emoji} {verdict}")
        console.print(table)
        console.print(f"[dim]Reports saved to:[/]")
        console.print(f"  📄 {json_path}")
        console.print(f"  🌐 {html_path}")
        console.print()
