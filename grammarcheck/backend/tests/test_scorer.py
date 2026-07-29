from evals.scorer import (
    compute_confidence_score,
    compute_false_positive_score,
    compute_gleu,
    compute_latency_score,
    compute_minimal_edit_score,
    compute_token_f1,
    compute_type_accuracy,
    compute_wer,
    llm_judge_composite,
    wer_to_score,
)


def test_f1_perfect_correction():
    result = compute_token_f1(
        "She dont likes coffee and goed home",
        "She doesn't like coffee and went home",
        "She doesn't like coffee and went home",
    )
    assert result["f1"] == 1.0
    assert result["tp"] == 3
    assert result["fp"] == 0
    assert result["fn"] == 0


def test_f1_partial_correction():
    result = compute_token_f1(
        "She dont likes coffee and goed home",
        "She doesn't like coffee and goed home",
        "She doesn't like coffee and went home",
    )
    assert result["f1"] < 1.0
    assert result["fn"] > 0


def test_f1_overcorrection():
    result = compute_token_f1(
        "She dont likes coffee",
        "She doesn't like coffee happily",
        "She doesn't like coffee",
    )
    assert result["fp"] > 0
    assert result["precision"] < 1.0


def test_f1_no_errors_in_input():
    result = compute_token_f1(
        "The quick brown fox",
        "The quick brown fox",
        "The quick brown fox",
    )
    assert result["f1"] == 1.0
    assert result["tp"] == 0
    assert result["fp"] == 0
    assert result["fn"] == 0


def test_wer_perfect():
    result = compute_wer("Hello world", "Hello world")
    assert result["wer"] == 0.0


def test_wer_partial():
    result = compute_wer("Hello world foo", "Hello world bar")
    assert result["wer"] > 0.0


def test_wer_to_score_mapping():
    assert wer_to_score(0.0) == 1.0
    assert wer_to_score(0.03) == 0.9
    assert wer_to_score(0.08) == 0.75
    assert wer_to_score(0.15) == 0.5
    assert wer_to_score(0.3) == 0.2


def test_gleu_perfect():
    result = compute_gleu("Hello world", "Hello world", "Hello world")
    assert result["gleu"] == 1.0


def test_gleu_partial():
    result = compute_gleu("She dont like", "She doesn't like", "She doesn't like")
    assert result["gleu"] > 0.0


def test_gleu_no_errors():
    result = compute_gleu("Hello world", "Hello world", "Hello world")
    assert result["gleu"] == 1.0


def test_minimal_edit_no_changes():
    result = compute_minimal_edit_score(
        "Hello world", "Hello world", []
    )
    assert result["score"] == 1.0
    assert result["unnecessary_edits"] == 0


def test_minimal_edit_over_edits():
    result = compute_minimal_edit_score(
        "The cat sat on the mat",
        "The cat sat upon the mat",
        [{"original": "on", "corrected": "on"}],
    )
    assert result["unnecessary_edits"] > 0
    assert result["score"] < 1.0


def test_false_positive_clean_text():
    results = [
        {"input": "Hello world", "response": {"errors": [], "corrected_text": "Hello world"}},
        {"input": "Good day", "response": {"errors": [{"original": "day", "corrected": "day"}], "corrected_text": "Good day"}},
    ]
    result = compute_false_positive_score(results)
    assert result["false_positive_rate"] == 0.5
    assert len(result["fp_cases"]) == 1


def test_latency_score_thresholds():
    assert compute_latency_score([5000, 6000, 7000])["verdict"] == "excellent"
    assert compute_latency_score([10000, 12000, 14000])["verdict"] == "acceptable"
    assert compute_latency_score([18000, 20000, 22000])["verdict"] == "slow"
    assert compute_latency_score([26000, 30000, 35000])["verdict"] == "critical"


def test_latency_score_empty():
    result = compute_latency_score([])
    assert result["verdict"] == "unknown"
    assert result["score"] == 0.0


def test_type_accuracy_perfect():
    model_errors = [{"original": "recieved", "corrected": "received", "type": "spelling", "reason": "misspelling"}]
    gt_errors = [{"original": "recieved", "corrected": "received", "type": "spelling", "reason": "misspelling"}]
    result = compute_type_accuracy(model_errors, gt_errors)
    assert result["type_accuracy"] == 1.0
    assert result["matched_count"] == 1


def test_type_accuracy_mismatch():
    model_errors = [{"original": "recieved", "corrected": "received", "type": "grammar", "reason": "wrong"}]
    gt_errors = [{"original": "recieved", "corrected": "received", "type": "spelling", "reason": "misspelling"}]
    result = compute_type_accuracy(model_errors, gt_errors)
    assert result["type_accuracy"] == 0.0


def test_llm_judge_composite():
    score = llm_judge_composite(5.0, 5.0, 5.0, 5.0)
    assert score == 1.0


def test_llm_judge_composite_mid():
    score = llm_judge_composite(4.0, 3.0, 5.0, 4.0)
    assert 0.5 < score < 1.0


def test_confidence_score_calculation():
    phases = {
        "correctness": {"score": 0.9},
        "recall": {"score": 0.85},
        "false_positives": {"score": 0.95},
        "guardrails": {"score": 0.9},
        "latency": {"score": 0.75},
        "llm_judge": {"score": 0.8},
    }
    result = compute_confidence_score(phases)
    assert 75 <= result["confidence_score"] <= 95
    assert "verdict" in result
