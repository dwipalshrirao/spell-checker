# Eval Spec: Guardrails
## File: backend/services/guardrail_service.py

---

## Overview

Guardrails are **fast, synchronous checks** that run on every request
BEFORE the text is sent to Ollama. They protect against:
- Prompt injection attacks
- Inputs that could destabilise the model
- PII that shouldn't be logged
- Inputs the model can't meaningfully process

Guardrails must add **< 50ms** to every request. No external API calls.

---

## Architecture

```
POST /check  →  InputGuardrail  →  Ollama  →  OutputGuardrail  →  Response
                     │                               │
                   block                           sanitise
                  (return 400)                (strip/redact)
```

---

## 1. Input Guardrails

### 1.1 Length Validator

```python
class LengthGuardrail:
    MIN_CHARS = 3
    MAX_CHARS = 5000
    MIN_WORDS = 1
    MAX_WORDS = 800

    def check(self, text: str) -> GuardrailResult:
        """
        FAIL conditions:
        - len(text.strip()) < MIN_CHARS  → "Text too short"
        - len(text.strip()) > MAX_CHARS  → "Text exceeds 5000 character limit"
        - word_count < MIN_WORDS         → "No words detected"
        - word_count > MAX_WORDS         → "Text exceeds 800 word limit"

        Returns GuardrailResult(passed=bool, reason=str, severity="low"|"medium"|"high")
        """
```

---

### 1.2 Language Detector

```python
class LanguageGuardrail:
    """
    Detect if input is English. Use lightweight heuristics (no external library):
    - Check ratio of ASCII alphabetic chars to total chars
    - Check for presence of common English stopwords (the, a, an, is, are, was, were, it, in, on, at, to, of, and, or, but)
    - If < 30% ASCII alpha chars AND no English stopwords → likely non-English

    Do NOT block non-English — WARN only. Return a warning flag in the response.
    The model will attempt correction but the result may be poor.

    Returns GuardrailResult(passed=True, warning="Input may not be English. Results may be inaccurate.")
    """
```

---

### 1.3 Prompt Injection Detector

```python
class PromptInjectionGuardrail:
    """
    Detect attempts to hijack the system prompt or override model behaviour.

    BLOCK if input contains ANY of these patterns (case-insensitive):

    HIGH SEVERITY — block immediately:
    - "ignore (all |previous |your )(instructions|prompt|rules|guidelines)"
    - "forget (your|all|previous) (role|instructions|rules)"
    - "you are now" followed by a different role
    - "### END" or "---END" or similar separator patterns
    - "act as (an |a )?(unrestricted|uncensored|jailbreak|DAN)"
    - "developer mode"
    - "bypass (all |safety |content )?(filters|restrictions|guidelines)"
    - "new (system |)prompt:"
    - "override (instructions|guidelines|prompt)"

    MEDIUM SEVERITY — flag, do not block (log warning):
    - "what is your (system |)prompt"
    - "repeat (your |the |)(instructions|prompt) (back|verbatim)"
    - "reveal (your |)(instructions|system prompt|configuration)"

    Returns GuardrailResult with severity level.
    Block only HIGH severity. Medium severity: allow but log.
    """
```

---

### 1.4 PII Detector

```python
class PIIGuardrail:
    """
    Detect Personally Identifiable Information using regex patterns.
    DO NOT block — warn and redact from logs only.
    The grammar check still runs on the original text.

    Patterns to detect:

    # Email addresses
    r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'

    # Phone numbers (international + Indian formats)
    r'(\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}'
    r'\+91[-.\s]?\d{5}[-.\s]?\d{5}'

    # Social Security Numbers (US)
    r'\b\d{3}-\d{2}-\d{4}\b'

    # Aadhaar numbers (India — 12 digits)
    r'\b\d{4}\s\d{4}\s\d{4}\b'

    # Credit card numbers (basic pattern)
    r'\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b'

    # Dates of birth patterns
    r'\b(DOB|date of birth|born on)[:\s]+\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b'

    Returns:
    GuardrailResult(
        passed=True,     # never block
        warning="PII detected: [email, phone]",   # types found, not values
        pii_detected=True,
        pii_types=["email", "phone"],   # for logging; do not log actual values
        log_safe_text=redacted_text     # text with PII replaced by [REDACTED] for logs
    )
    """
```

---

### 1.5 Content Type Validator

```python
class ContentTypeGuardrail:
    """
    Ensure input is meaningful text (not pure numbers, code, emoji, etc.)

    WARN (don't block) if:
    - Input is > 80% digits/symbols → "Input appears to be numeric/code, not prose"
    - Input is > 60% emoji characters → "Input is mostly emoji"
    - Input is > 70% HTML/XML tags → "Input appears to be HTML — tags will be ignored"

    For HTML inputs: strip tags, check if remaining text is meaningful.
    If remaining text after tag stripping is meaningful → proceed with stripped text.
    If not → warn.

    Returns GuardrailResult with cleaned_text if HTML was stripped.
    """
```

---

## 2. Output Guardrails

### 2.1 Response Validator

```python
class ResponseValidator:
    """
    Validate that the model's JSON response is well-formed and sensible.
    Run AFTER getting Ollama response, BEFORE returning to client.

    Checks:
    1. corrected_text is not empty
    2. corrected_text is not wildly different from input (WER > 0.8 → suspicious)
    3. errors list is actually a list
    4. each error has required fields: original, corrected, type, reason
    5. error `type` is one of: spelling, grammar, punctuation, style, word_choice
    6. corrected_text does not contain prompt injection artifacts
       (e.g. starts with "SYSTEM:" or contains "ignore previous instructions")
    7. corrected_text length is within 50%–200% of input length
       (a correction shouldn't double the text or halve it)

    On validation failure: return a safe fallback response with error details logged.
    Never return a malformed response to the client.
    """
```

### 2.2 Hallucination Detector

```python
class HallucinationDetector:
    """
    Detect obvious hallucinations in model output.

    Flag if:
    - Model claims to have fixed errors that don't appear in the original text
      (error.original not found in original_text as substring)
    - corrected_text contains URLs, code blocks, or markdown that weren't in input
    - Model adds sentences not present in original (length increase > 50%)
    - Model removes sentences (length decrease > 50%)

    Returns:
    {
        "hallucinations_detected": bool,
        "hallucination_types": list[str],
        "confidence_penalty": float   # 0.0-0.3, subtract from response confidence
    }
    """
```

---

## 3. GuardrailResult Model

```python
from dataclasses import dataclass
from typing import Optional

@dataclass
class GuardrailResult:
    passed: bool
    severity: str = "low"          # "low" | "medium" | "high"
    reason: Optional[str] = None   # shown to user if blocked
    warning: Optional[str] = None  # shown to user as info
    log_message: str = ""          # internal logging only
    pii_detected: bool = False
    pii_types: list = None
    log_safe_text: Optional[str] = None  # text with PII redacted, for logs
    cleaned_text: Optional[str] = None  # if input was cleaned (e.g. HTML stripped)
```

---

## 4. Guardrail Pipeline

```python
class GuardrailPipeline:
    """
    Run all input guardrails in order. Stop on first HIGH severity failure.
    Collect all warnings and pass through.
    """

    INPUT_GUARDRAILS = [
        LengthGuardrail(),           # fastest — run first
        ContentTypeGuardrail(),      # fast
        PromptInjectionGuardrail(),  # regex — fast
        PIIGuardrail(),              # regex — fast
        LanguageGuardrail(),         # heuristic — fast
    ]

    def run_input_checks(self, text: str) -> PipelineResult:
        """
        Returns PipelineResult:
        {
            "blocked": bool,
            "block_reason": str | None,
            "warnings": list[str],
            "cleaned_text": str,     # original or cleaned (HTML stripped, etc.)
            "pii_detected": bool,
            "pii_types": list[str],
            "log_safe_text": str,
        }
        """

    def run_output_checks(self, input_text: str, model_response: dict) -> PipelineResult:
        """Run ResponseValidator + HallucinationDetector on model output."""
```

---

## 5. Integration in FastAPI Route

```python
# backend/routers/check.py

@router.post("/check")
async def check_grammar(request: CheckRequest, ...):

    # 1. Run input guardrails
    pipeline_result = guardrail_pipeline.run_input_checks(request.text)

    if pipeline_result.blocked:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "input_rejected",
                "reason": pipeline_result.block_reason,
                "request_id": request_id,
            }
        )

    # Use cleaned text if guardrails modified it (e.g. HTML stripped)
    text_to_check = pipeline_result.cleaned_text or request.text

    # 2. Call Ollama
    model_response = await grammar_service.check(text_to_check)

    # 3. Run output guardrails
    output_result = guardrail_pipeline.run_output_checks(text_to_check, model_response)

    # 4. Build response including any warnings
    return CheckResponse(
        ...model_response,
        warnings=pipeline_result.warnings + output_result.warnings,
        request_id=request_id,
    )
```

---

## 6. Guardrail Tests Required

```python
# backend/tests/test_guardrails.py

# Length tests
test_empty_input_blocked()
test_whitespace_only_blocked()
test_too_long_blocked()
test_at_limit_passes()
test_minimum_length_passes()

# Injection tests
test_ignore_instructions_blocked()
test_developer_mode_blocked()
test_legitimate_text_with_injection_keywords_blocked()  # "ignore the noise" — tricky
test_medium_severity_logged_not_blocked()

# PII tests
test_email_detected()
test_phone_detected()
test_aadhaar_detected()
test_pii_not_blocked_only_flagged()
test_no_pii_passes_clean()

# Language tests
test_french_input_warned_not_blocked()
test_mixed_language_warned()
test_english_passes_clean()

# Output validation tests
test_valid_response_passes()
test_empty_corrected_text_caught()
test_wer_too_high_flagged()
test_invalid_error_type_caught()
test_hallucinated_error_not_in_original_caught()
```

---

## Performance Requirements

All guardrail checks combined must complete in < 50ms for any input up to 5000 chars.
Run `pytest --benchmark` to verify. If any single guardrail exceeds 20ms, optimise it.