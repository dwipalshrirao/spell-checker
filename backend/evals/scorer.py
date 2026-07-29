"""
scorer.py — Pure functions for scoring grammar checker output against ground truth.

All functions are side-effect-free and unit-testable in isolation.
"""

from __future__ import annotations

from collections import Counter
from typing import Any

import jiwer
import numpy as np
from nltk.translate.gleu_score import sentence_gleu


# ─── 1. Token-Level F1 ─────────────────────────────────────────────────────────


def compute_token_f1(
    original_text: str,
    corrected_by_model: str,
    ground_truth_corrected: str,
) -> dict[str, Any]:
    orig_words = original_text.split()
    model_words = corrected_by_model.split()
    gt_words = ground_truth_corrected.split()

    model_changes = _find_changes(orig_words, model_words)
    gt_changes = _find_changes(orig_words, gt_words)

    tp = len(model_changes & gt_changes)
    fp = len(model_changes - gt_changes)
    fn = len(gt_changes - model_changes)

    precision = tp / (tp + fp) if (tp + fp) > 0 else 1.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 1.0
    f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0

    return {
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1": round(f1, 4),
        "tp": tp,
        "fp": fp,
        "fn": fn,
    }


def _find_changes(original: list[str], corrected: list[str]) -> set[tuple[int, str, str]]:
    """Return set of (position, original_word, corrected_word) that differ."""
    from itertools import zip_longest
    changes: set[tuple[int, str, str]] = set()
    for i, (orig, corr) in enumerate(zip_longest(original, corrected, fillvalue="")):
        if orig != corr:
            changes.add((i, orig, corr))
    return changes


# ─── 2. Word Error Rate (WER) ─────────────────────────────────────────────────


def compute_wer(
    model_output: str,
    ground_truth: str,
) -> dict[str, Any]:
    wer = jiwer.wer(reference=ground_truth, hypothesis=model_output)
    # Get detail via jiwer.process_words
    detail = jiwer.process_words(reference=ground_truth, hypothesis=model_output)
    return {
        "wer": round(wer, 4),
        "substitutions": detail.substitutions,
        "deletions": detail.deletions,
        "insertions": detail.insertions,
        "reference_length": detail.references,
    }


def wer_to_score(wer: float) -> float:
    if wer == 0.0:
        return 1.0
    if wer <= 0.05:
        return 0.9
    if wer <= 0.10:
        return 0.75
    if wer <= 0.20:
        return 0.5
    return 0.2


# ─── 3. GLEU Score ────────────────────────────────────────────────────────────


def compute_gleu(
    original_text: str,
    model_output: str,
    ground_truth: str,
) -> dict[str, float]:
    hypothesis_tokens = model_output.split()
    reference_tokens = ground_truth.split()

    if original_text.strip() == ground_truth.strip() and model_output.strip() == original_text.strip():
        return {"gleu": 1.0}

    gleu = sentence_gleu(
        [reference_tokens],
        hypothesis_tokens,
        min_len=1,
        max_len=4,
    )
    return {"gleu": round(gleu, 4)}


# ─── 4. Minimal Edit Score ────────────────────────────────────────────────────


def compute_minimal_edit_score(
    original_text: str,
    model_output: str,
    ground_truth_errors: list[dict],
) -> dict[str, Any]:
    orig_words = original_text.split()
    model_words = model_output.split()
    gt_words = original_text.split()

    # Build ground truth corrected text from errors
    for err in ground_truth_errors:
        orig_frag = err.get("original", "")
        corr_frag = err.get("corrected", "")
        if orig_frag in original_text:
            gt_words = original_text.replace(orig_frag, corr_frag).split()
            break

    model_changes = _find_changes(orig_words, model_words)
    gt_changes = _find_changes(orig_words, gt_words)

    unnecessary = model_changes - gt_changes
    total_words = len(orig_words) or 1
    score = 1.0 - (len(unnecessary) / total_words)

    unnecessary_edit_words = [w[1] for w in unnecessary]

    return {
        "score": round(max(0.0, score), 4),
        "unnecessary_edits": len(unnecessary),
        "unnecessary_edit_words": unnecessary_edit_words,
    }


# ─── 5. Error Type Classification Accuracy ────────────────────────────────────


def compute_type_accuracy(
    model_errors: list[dict],
    ground_truth_errors: list[dict],
) -> dict[str, Any]:
    type_confusion: dict[str, Counter] = {}
    matched = 0
    correct_type = 0

    for gt_err in ground_truth_errors:
        gt_orig = gt_err.get("original", "").lower().strip()
        gt_type = gt_err.get("type", "").lower()

        best_match = None
        for m_err in model_errors:
            m_orig = m_err.get("original", "").lower().strip()
            if m_orig == gt_orig or m_orig in gt_orig or gt_orig in m_orig:
                best_match = m_err
                break

        if best_match is not None:
            matched += 1
            m_type = best_match.get("type", "").lower()
            if m_type == gt_type:
                correct_type += 1
            if gt_type not in type_confusion:
                type_confusion[gt_type] = Counter()
            type_confusion[gt_type][m_type] += 1

    type_accuracy = correct_type / matched if matched > 0 else 1.0
    confusion_serializable = {k: dict(v) for k, v in type_confusion.items()}

    return {
        "type_accuracy": round(type_accuracy, 4),
        "matched_count": matched,
        "type_confusion": confusion_serializable,
    }


# ─── 6. False Positive Score ──────────────────────────────────────────────────


def compute_false_positive_score(
    results: list[dict],
) -> dict[str, Any]:
    fp_cases = []
    total = len(results)
    false_positives = 0

    for result in results:
        case_input = result.get("input", "")
        errors = result.get("response", {}).get("errors", [])
        corrected = result.get("response", {}).get("corrected_text", "")

        if len(errors) > 0:
            false_positives += 1
            fp_cases.append({
                "input": case_input,
                "model_errors_returned": [f"{e.get('original', '')} -> {e.get('corrected', '')}" for e in errors],
            })

    fp_rate = false_positives / total if total > 0 else 0.0
    tn_rate = 1.0 - fp_rate

    return {
        "false_positive_rate": round(fp_rate, 4),
        "true_negative_rate": round(tn_rate, 4),
        "fp_cases": fp_cases,
        "score": round(tn_rate, 4),
    }


# ─── 7. Latency Score ─────────────────────────────────────────────────────────


def compute_latency_score(
    latencies_ms: list[float],
) -> dict[str, Any]:
    if not latencies_ms:
        return {
            "p50_ms": 0.0,
            "p95_ms": 0.0,
            "p99_ms": 0.0,
            "mean_ms": 0.0,
            "min_ms": 0.0,
            "max_ms": 0.0,
            "score": 0.0,
            "verdict": "unknown",
        }

    arr = sorted(latencies_ms)
    n = len(arr)

    p50 = arr[int(n * 0.5)]
    p95 = arr[int(n * 0.95)]
    p99 = arr[int(n * 0.99)]

    if p95 < 8000:
        score, verdict = 1.0, "excellent"
    elif p95 < 15000:
        score, verdict = 0.75, "acceptable"
    elif p95 < 25000:
        score, verdict = 0.5, "slow"
    else:
        score, verdict = 0.2, "critical"

    return {
        "p50_ms": round(p50, 1),
        "p95_ms": round(p95, 1),
        "p99_ms": round(p99, 1),
        "mean_ms": round(float(np.mean(arr)), 1),
        "min_ms": round(float(np.min(arr)), 1),
        "max_ms": round(float(np.max(arr)), 1),
        "score": score,
        "verdict": verdict,
    }


# ─── 8. Compute overall confidence score ──────────────────────────────────────


def compute_confidence_score(phases: dict[str, Any]) -> dict[str, Any]:
    weights = {
        "correctness": 0.30,
        "recall": 0.20,
        "false_positives": 0.15,
        "guardrails": 0.15,
        "latency": 0.10,
        "llm_judge": 0.10,
    }

    weighted_sum = 0.0
    for phase, weight in weights.items():
        score = phases.get(phase, {}).get("score", 0.0)
        weighted_sum += score * weight

    confidence = weighted_sum * 100
    if confidence >= 85:
        verdict = "PRODUCTION READY"
    elif confidence >= 75:
        verdict = "NEEDS IMPROVEMENT"
    elif confidence >= 60:
        verdict = "NOT READY"
    else:
        verdict = "CRITICAL ISSUES"

    return {
        "confidence_score": round(confidence, 1),
        "production_ready": confidence >= 85,
        "verdict": verdict,
    }


# ─── 9. Compute composite judge score from LLM judge dimensions ────────────────


def llm_judge_composite(faithfulness: float, completeness: float,
                        explanation_quality: float, conservatism: float) -> float:
    composite = (faithfulness * 0.3 + completeness * 0.35 + explanation_quality * 0.2 + conservatism * 0.15) / 5
    return round(composite, 4)
