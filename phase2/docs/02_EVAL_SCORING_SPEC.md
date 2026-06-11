# Eval Spec: Scoring Metrics
## File: backend/evals/scorer.py

---

## Overview

`scorer.py` is a **pure functions module** — no side effects, no API calls.
It takes raw API responses and ground truth, returns numeric scores.
All functions must be unit-testable in isolation.

---

## 1. Token-Level F1 Score

### Purpose
Measures how well the model identifies which tokens (words) need correction.

### How it works
Treat error detection as a binary classification problem per word:
- **TP** — model flagged this word as wrong AND it actually is wrong
- **FP** — model flagged this word as wrong BUT it was correct (over-correction)
- **FN** — model did NOT flag this word BUT it actually was wrong (missed error)

### Formula
```
Precision = TP / (TP + FP)
Recall    = TP / (TP + FN)
F1        = 2 * (Precision * Recall) / (Precision + Recall)
```

### Implementation spec
```python
def compute_token_f1(
    original_text: str,
    corrected_by_model: str,
    ground_truth_corrected: str,
) -> dict:
    """
    Returns:
    {
        "precision": float,   # 0.0 to 1.0
        "recall": float,      # 0.0 to 1.0
        "f1": float,          # 0.0 to 1.0
        "tp": int,
        "fp": int,
        "fn": int,
    }
    """
```

### Worked example
```
Original:         "She dont likes coffee and goed home"
Model output:     "She doesn't like coffee and went home"
Ground truth:     "She doesn't like coffee and went home"

Changed by model:    {dont→doesn't, likes→like, goed→went}
Changed in GT:       {dont→doesn't, likes→like, goed→went}
TP=3, FP=0, FN=0 → F1=1.0
```

```
Original:         "She dont likes coffee"
Model output:     "She doesn't like coffee happily"   ← added word incorrectly
Ground truth:     "She doesn't like coffee"

TP=2, FP=1 (added "happily"), FN=0 → Precision=0.67, Recall=1.0, F1=0.80
```

---

## 2. Word Error Rate (WER)

### Purpose
Measures the edit distance between model output and ground truth.
Captures how "far off" the correction is, not just whether errors were found.

### Formula
```
WER = (S + D + I) / N

S = substitutions (wrong word used)
D = deletions (word removed that shouldn't be)
I = insertions (word added that shouldn't be)
N = total words in ground truth
```

### Implementation spec
```python
def compute_wer(
    model_output: str,
    ground_truth: str,
) -> dict:
    """
    Use the `jiwer` library internally.
    Returns:
    {
        "wer": float,          # 0.0 = perfect, 1.0+ = completely wrong
        "substitutions": int,
        "deletions": int,
        "insertions": int,
        "reference_length": int,
    }
    """
```

### Score mapping for final confidence score
```
WER 0.00       → score 1.0  (perfect)
WER 0.00–0.05  → score 0.9  (excellent, minor word differences)
WER 0.05–0.10  → score 0.75 (good)
WER 0.10–0.20  → score 0.5  (needs improvement)
WER > 0.20     → score 0.2  (poor)
```

---

## 3. GLEU Score

### Purpose
Measures n-gram overlap between model output and ground truth.
More lenient than exact match — partial credit for partially correct corrections.

### Implementation spec
```python
def compute_gleu(
    original_text: str,
    model_output: str,
    ground_truth: str,
) -> dict:
    """
    Use nltk.translate.gleu_score.sentence_gleu internally.
    GLEU is preferred over BLEU for GEC tasks because it penalises
    unnecessary changes to already-correct text.

    Returns:
    {
        "gleu": float,   # 0.0 to 1.0
    }
    """
```

### Notes for Claude Code
- GLEU requires `nltk`. Add `nltk.download('punkt')` to eval setup.
- `reference` = ground_truth tokens, `hypothesis` = model_output tokens
- `source` = original_text tokens (GLEU uses this to penalise over-editing)

---

## 4. Minimal Edit Score

### Purpose
Penalises the model for making unnecessary changes to text that was already correct.
A good grammar checker should be conservative.

### Formula
```
unnecessary_edits = words changed by model that were CORRECT in original
minimal_edit_score = 1 - (unnecessary_edits / total_words_in_original)
```

### Implementation spec
```python
def compute_minimal_edit_score(
    original_text: str,
    model_output: str,
    ground_truth_errors: list[dict],  # list of {original, corrected} from eval case
) -> dict:
    """
    Returns:
    {
        "score": float,            # 0.0 to 1.0 (1.0 = no unnecessary changes)
        "unnecessary_edits": int,
        "unnecessary_edit_words": list[str],   # which words were changed unnecessarily
    }
    """
```

### Worked example
```
Original:    "The cat sat on the mat."   (no errors)
Model output:"The cat sat upon the mat." (changed "on" → "upon" unnecessarily)

unnecessary_edits = 1
minimal_edit_score = 1 - (1/7) = 0.857
```

---

## 5. Error Type Classification Accuracy

### Purpose
Checks whether the model correctly identifies the TYPE of each error.

### Implementation spec
```python
def compute_type_accuracy(
    model_errors: list[dict],      # errors returned by /check
    ground_truth_errors: list[dict],  # expected errors from eval case
) -> dict:
    """
    Match model errors to ground truth errors by (original_fragment).
    For matched pairs, check if `type` field matches.

    Returns:
    {
        "type_accuracy": float,    # % of matched errors with correct type
        "matched_count": int,
        "type_confusion": dict,    # {"spelling": {"spelling": 5, "grammar": 1}, ...}
    }
    """
```

---

## 6. LLM-as-Judge Scorer

### Purpose
Use a second call to the same Ollama model to score output quality holistically.
This catches things rule-based metrics miss (e.g. awkward but technically correct fixes).

### Judge prompt (Claude Code must use this exactly)

```
SYSTEM:
You are an expert evaluator of grammar correction systems.
You will be given:
1. ORIGINAL: the text before correction
2. CORRECTED: the grammar checker's output
3. EXPECTED: the ideal correction (ground truth)

Score the CORRECTED text on these dimensions (1-5 each):

FAITHFULNESS: Does the corrected text preserve the original meaning?
  5 = meaning perfectly preserved
  3 = minor meaning shift
  1 = meaning substantially changed

COMPLETENESS: Were all errors caught and fixed?
  5 = all errors fixed, nothing missed
  3 = most errors fixed, 1-2 missed
  1 = major errors missed

EXPLANATION_QUALITY: Are the error explanations accurate and useful?
  5 = all explanations are accurate and clearly explain why
  3 = most explanations correct, some vague
  1 = explanations are wrong or missing

CONSERVATISM: Did it avoid changing text that was already correct?
  5 = only changed what needed changing
  3 = 1-2 unnecessary changes
  1 = many unnecessary rewrites

Return ONLY valid JSON, no other text:
{"faithfulness": N, "completeness": N, "explanation_quality": N, "conservatism": N, "reasoning": "one sentence"}

USER:
ORIGINAL: {original}
CORRECTED: {model_corrected}
EXPECTED: {ground_truth_corrected}
ERRORS_GIVEN: {model_errors_json}
```

### Implementation spec
```python
async def llm_judge_score(
    original: str,
    model_output: dict,      # full /check response
    ground_truth: dict,      # eval case ground truth
    ollama_url: str,
    model_name: str,
) -> dict:
    """
    Returns:
    {
        "faithfulness": float,          # 1-5
        "completeness": float,          # 1-5
        "explanation_quality": float,   # 1-5
        "conservatism": float,          # 1-5
        "composite_judge_score": float, # weighted average, normalised 0-1
        "reasoning": str,
        "judge_latency_ms": int,
    }
    """
    # composite = (faith*0.3 + complete*0.35 + explain*0.2 + conserve*0.15) / 5
```

---

## 7. False Positive Score

### Purpose
Tests model on CORRECT text — it should return zero errors.
Critical metric: a grammar checker that flags correct text is worse than no checker.

### Implementation spec
```python
def compute_false_positive_score(
    results: list[dict],  # list of /check responses for clean inputs
) -> dict:
    """
    For each result on a no-error input:
    - If model returned 0 errors AND corrected_text ≈ original → TRUE NEGATIVE (good)
    - If model returned errors OR changed text → FALSE POSITIVE (bad)

    Returns:
    {
        "false_positive_rate": float,    # 0.0 = perfect, 1.0 = flags everything
        "true_negative_rate": float,     # 1 - false_positive_rate
        "fp_cases": list[dict],          # which clean cases were wrongly flagged
        "score": float,                  # 1 - false_positive_rate (for confidence calc)
    }
    """
    # Use fuzzy match for corrected_text ≈ original (allow punctuation normalisation)
    # Threshold: if edit distance < 3 chars, treat as "no change"
```

---

## 8. Latency Score

### Purpose
Convert raw latency percentiles into a normalised score.

### Implementation spec
```python
def compute_latency_score(
    latencies_ms: list[float],
) -> dict:
    """
    Returns:
    {
        "p50_ms": float,
        "p95_ms": float,
        "p99_ms": float,
        "mean_ms": float,
        "min_ms": float,
        "max_ms": float,
        "score": float,      # 0.0 to 1.0
        "verdict": str,      # "excellent" | "acceptable" | "slow" | "critical"
    }
    """
```

### Scoring thresholds
```
p95 < 8s    → score 1.0, verdict "excellent"
p95 < 15s   → score 0.75, verdict "acceptable"
p95 < 25s   → score 0.5,  verdict "slow"
p95 >= 25s  → score 0.2,  verdict "critical"
```

---

## Unit Tests Required

Claude Code must write tests in `backend/tests/test_scorer.py`:

```python
# Test cases to cover:
test_f1_perfect_correction()         # model matches ground truth exactly
test_f1_partial_correction()         # model fixes some but not all errors
test_f1_overcorrection()             # model changes correct words
test_f1_no_errors_in_input()         # clean text, model returns nothing
test_wer_perfect()                   # WER = 0
test_wer_partial()                   # some words wrong
test_minimal_edit_no_changes()       # model makes no unnecessary edits
test_minimal_edit_over_edits()       # model rewrites unnecessarily
test_false_positive_clean_text()     # correct text returns no errors
test_latency_score_thresholds()      # each verdict bucket
```