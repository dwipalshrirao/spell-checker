"""
guardrail_service.py — Fast, synchronous input/output guardrails.

All checks complete in < 50ms. No external API calls.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Optional

import jiwer

from config import settings


# ─── Data Models ──────────────────────────────────────────────────────────────


@dataclass
class GuardrailResult:
    passed: bool
    severity: str = "low"
    reason: Optional[str] = None
    warning: Optional[str] = None
    log_message: str = ""
    pii_detected: bool = False
    pii_types: list[str] = field(default_factory=list)
    log_safe_text: Optional[str] = None
    cleaned_text: Optional[str] = None


class GuardrailError(Exception):
    pass


# ─── 1.1 Length Guardrail ─────────────────────────────────────────────────────


class LengthGuardrail:
    MIN_CHARS = 3
    MAX_CHARS = 5000
    MIN_WORDS = 1
    MAX_WORDS = 800

    def check(self, text: str) -> GuardrailResult:
        stripped = text.strip()
        char_count = len(stripped)
        word_count = len(stripped.split()) if stripped else 0

        if char_count < self.MIN_CHARS:
            return GuardrailResult(
                passed=False, severity="low",
                reason=f"Text too short ({char_count} chars, minimum {self.MIN_CHARS}).",
                log_message=f"length_fail: too_short ({char_count}c)",
            )
        if char_count > self.MAX_CHARS:
            return GuardrailResult(
                passed=False, severity="low",
                reason=f"Text exceeds {self.MAX_CHARS} character limit ({char_count} given).",
                log_message=f"length_fail: too_long ({char_count}c)",
            )
        if word_count < self.MIN_WORDS:
            return GuardrailResult(
                passed=False, severity="low",
                reason="No words detected in input.",
                log_message=f"length_fail: no_words",
            )
        if word_count > self.MAX_WORDS:
            return GuardrailResult(
                passed=False, severity="low",
                reason=f"Text exceeds {self.MAX_WORDS} word limit ({word_count} words).",
                log_message=f"length_fail: too_many_words ({word_count}w)",
            )

        return GuardrailResult(passed=True)


# ─── 1.2 Language Guardrail ───────────────────────────────────────────────────


ENGLISH_STOPWORDS = {
    "the", "a", "an", "is", "are", "was", "were", "it", "in", "on",
    "at", "to", "of", "and", "or", "but", "be", "been", "being",
    "have", "has", "had", "do", "does", "did", "will", "would",
    "can", "could", "shall", "should", "may", "might", "not",
    "no", "nor", "for", "with", "by", "from", "as", "into",
    "through", "during", "before", "after", "above", "below",
    "between", "out", "off", "over", "under", "again", "further",
    "then", "once", "here", "there", "when", "where", "why", "how",
    "all", "each", "every", "both", "few", "more", "most", "other",
    "some", "such", "only", "own", "same", "so", "than", "too",
    "very", "just", "because", "if", "while", "although", "though",
}


class LanguageGuardrail:
    def check(self, text: str) -> GuardrailResult:
        stripped = text.strip()
        if not stripped:
            return GuardrailResult(passed=True)

        alpha_chars = sum(1 for c in stripped if c.isascii() and c.isalpha())
        total_chars = len(stripped)
        alpha_ratio = alpha_chars / total_chars if total_chars > 0 else 0

        words = stripped.lower().split()
        stopword_count = sum(1 for w in words if w in ENGLISH_STOPWORDS)
        stopword_ratio = stopword_count / len(words) if words else 0

        if alpha_ratio < 0.3 and stopword_ratio < 0.1:
            return GuardrailResult(
                passed=True,
                severity="low",
                warning="Input may not be English. Results may be inaccurate.",
                log_message=f"language_warn: likely_non_english (alpha={alpha_ratio:.2f}, stopwords={stopword_ratio:.2f})",
            )

        return GuardrailResult(passed=True)


# ─── 1.3 Prompt Injection Guardrail ───────────────────────────────────────────


class PromptInjectionGuardrail:
    HIGH_PATTERNS = [
        r"ignore\s+(all\s+|previous\s+)?(instructions|prompt|rules|guidelines)",
        r"forget\s+(your|all|previous)\s+(role|instructions|rules)",
        r"you\s+are\s+now\s+(an\s+|a\s+)?(unrestricted|uncensored|jailbreak|DAN|developer\s+mode)",
        r"bypass\s+(all\s+|safety\s+|content\s+)?(filters|restrictions|guidelines)",
        r"(new\s+)?(system\s+)?prompt:",
        r"override\s+(instructions|guidelines|prompt)",
        r"#{3,}\s*(END|end)",
        r"-{3,}(END|end)",
        r"act\s+as\s+(an\s+|a\s+)?(unrestricted|uncensored|jailbreak|DAN)",
    ]

    MEDIUM_PATTERNS = [
        r"what\s+is\s+your\s+(system\s+)?prompt",
        r"repeat\s+(your\s+|the\s+)?(instructions|prompt)\s+(back|verbatim)",
        r"reveal\s+(your\s+)?(instructions|system\s+prompt|configuration)",
    ]

    def check(self, text: str) -> GuardrailResult:
        lower = text.lower()

        for pattern in self.HIGH_PATTERNS:
            if re.search(pattern, lower):
                return GuardrailResult(
                    passed=False,
                    severity="high",
                    reason="Input contains potential prompt injection. Request blocked for safety.",
                    log_message=f"injection_blocked: matched high-severity pattern '{pattern}'",
                )

        for pattern in self.MEDIUM_PATTERNS:
            if re.search(pattern, lower):
                return GuardrailResult(
                    passed=True,
                    severity="medium",
                    warning="Input attempted to probe system configuration. Proceeding with caution.",
                    log_message=f"injection_warn: matched medium-severity pattern '{pattern}'",
                )

        return GuardrailResult(passed=True)


# ─── 1.4 PII Guardrail ────────────────────────────────────────────────────────


PII_PATTERNS: list[tuple[str, str]] = [
    ("email", r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'),
    ("phone", r'(\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}'),
    ("phone_india", r'\+91[-.\s]?\d{5}[-.\s]?\d{5}'),
    ("ssn", r'\b\d{3}-\d{2}-\d{4}\b'),
    ("aadhaar", r'\b\d{4}\s\d{4}\s\d{4}\b'),
    ("credit_card", r'\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b'),
    ("dob", r'\b(DOB|date of birth|born on)[:\s]+\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b'),
]


class PIIGuardrail:
    def check(self, text: str) -> GuardrailResult:
        detected_types: list[str] = []
        log_safe = text

        for pii_type, pattern in PII_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                detected_types.append(pii_type)
                log_safe = re.sub(pattern, f"[REDACTED-{pii_type.upper()}]", log_safe, flags=re.IGNORECASE)

        if detected_types:
            return GuardrailResult(
                passed=True,
                severity="low",
                warning=f"PII detected: {', '.join(detected_types)}",
                log_message=f"pii_detected: {','.join(detected_types)}",
                pii_detected=True,
                pii_types=detected_types,
                log_safe_text=log_safe,
            )

        return GuardrailResult(passed=True)


# ─── 1.5 Content Type Guardrail ───────────────────────────────────────────────


class ContentTypeGuardrail:
    def check(self, text: str) -> GuardrailResult:
        stripped = text.strip()
        if not stripped:
            return GuardrailResult(passed=True)

        # Check for HTML tags
        html_pattern = re.compile(r'<[^>]+>')
        has_html = bool(html_pattern.search(stripped))

        cleaned = stripped
        if has_html:
            cleaned = html_pattern.sub('', stripped).strip()
            if len(cleaned) >= 10:
                return GuardrailResult(
                    passed=True,
                    severity="low",
                    warning="Input appears to contain HTML. Tags have been stripped for processing.",
                    log_message="content_warn: html_stripped",
                    cleaned_text=cleaned,
                )

        # Check for high digit/symbol ratio
        alpha_count = sum(1 for c in stripped if c.isalpha())
        digit_symbol_count = sum(1 for c in stripped if not c.isalpha() and not c.isspace())
        total_meaningful = alpha_count + digit_symbol_count
        if total_meaningful > 0 and (digit_symbol_count / total_meaningful) > 0.8:
            return GuardrailResult(
                passed=True,
                severity="low",
                warning="Input appears to be numeric/code, not prose.",
                log_message=f"content_warn: high_digit_ratio ({digit_symbol_count / total_meaningful:.2f})",
            )

        # Check emoji ratio
        emoji_pattern = re.compile(
            r'[\U0001F600-\U0001F64F\U0001F300-\U0001F5FF\U0001F680-\U0001F6FF'
            r'\U0001F1E0-\U0001F1FF\U00002702-\U000027B0\U000024C2-\U0001F251]+'
        )
        emoji_matches = emoji_pattern.findall(stripped)
        emoji_chars = sum(len(m) for m in emoji_matches)
        if total_meaningful > 0 and (emoji_chars / total_meaningful) > 0.6:
            return GuardrailResult(
                passed=True,
                severity="low",
                warning="Input is mostly emoji. Results may be poor.",
                log_message=f"content_warn: high_emoji_ratio ({emoji_chars / total_meaningful:.2f})",
            )

        return GuardrailResult(passed=True)


# ─── 2.1 Response Validator ───────────────────────────────────────────────────


VALID_ERROR_TYPES = {"spelling", "grammar", "punctuation", "style", "word_choice"}


class ResponseValidator:
    def check(self, input_text: str, model_response: dict) -> GuardrailResult:
        corrected = model_response.get("corrected_text", "")
        errors = model_response.get("errors", [])

        # 1. corrected_text not empty
        if not corrected or not corrected.strip():
            return GuardrailResult(
                passed=False,
                severity="high",
                reason="Model returned empty corrected text.",
                log_message="output_fail: empty_corrected_text",
            )

        # 2. corrected_text not wildly different
        wer = jiwer.wer(reference=input_text, hypothesis=corrected)
        if wer > 0.8:
            return GuardrailResult(
                passed=False,
                severity="medium",
                reason="Model output is suspiciously different from input.",
                log_message=f"output_fail: wer_too_high ({wer:.2f})",
            )

        # 3. errors is a list
        if not isinstance(errors, list):
            return GuardrailResult(
                passed=False,
                severity="medium",
                reason="Model returned non-list errors field.",
                log_message="output_fail: errors_not_list",
            )

        # 4. Each error has required fields
        for err in errors:
            if not all(k in err for k in ("original", "corrected", "type", "reason")):
                return GuardrailResult(
                    passed=False,
                    severity="medium",
                    reason="Model returned error with missing fields.",
                    log_message="output_fail: error_missing_fields",
                )
            if err.get("type", "").lower() not in VALID_ERROR_TYPES:
                return GuardrailResult(
                    passed=False,
                    severity="medium",
                    reason=f"Model returned invalid error type: {err.get('type')}",
                    log_message="output_fail: invalid_error_type",
                )

        # 5. No prompt injection artifacts in output
        lower_corrected = corrected.lower()
        injection_markers = ["ignore previous instructions", "system:", "bypass filters",
                             "you are now", "developer mode"]
        for marker in injection_markers:
            if marker in lower_corrected:
                return GuardrailResult(
                    passed=False,
                    severity="high",
                    reason="Model output contains prompt injection artifacts.",
                    log_message=f"output_fail: injection_artifact '{marker}'",
                )

        # 6. Length sanity check (50%–200% of input)
        input_len = len(input_text)
        output_len = len(corrected)
        if input_len > 0:
            ratio = output_len / input_len
            if ratio < 0.5 or ratio > 2.0:
                return GuardrailResult(
                    passed=False,
                    severity="medium",
                    reason=f"Output length ({output_len}) is out of expected range vs input ({input_len}).",
                    log_message=f"output_fail: length_ratio_out_of_range ({ratio:.2f})",
                )

        return GuardrailResult(passed=True)


# ─── 2.2 Hallucination Detector ───────────────────────────────────────────────


class HallucinationDetector:
    def check(self, input_text: str, model_response: dict) -> dict[str, Any]:
        errors = model_response.get("errors", [])
        corrected = model_response.get("corrected_text", "")
        hallucination_types: list[str] = []

        for err in errors:
            original_frag = err.get("original", "")
            if original_frag and original_frag not in input_text:
                hallucination_types.append("phantom_error")
                break

        # Check for URLs or code blocks not in input
        url_pattern = re.compile(r'https?://\S+')
        code_pattern = re.compile(r'```')
        if url_pattern.search(corrected) and not url_pattern.search(input_text):
            hallucination_types.append("added_urls")
        if code_pattern.search(corrected) and not code_pattern.search(input_text):
            hallucination_types.append("added_code_blocks")

        # Length change check
        input_words = len(input_text.split())
        output_words = len(corrected.split())
        if input_words > 0:
            length_ratio = output_words / input_words
            if length_ratio > 1.5:
                hallucination_types.append("excessive_length_increase")
            elif length_ratio < 0.5:
                hallucination_types.append("excessive_length_decrease")

        penalty = 0.0
        if "phantom_error" in hallucination_types:
            penalty = 0.15
        if hallucination_types:
            penalty = min(penalty + 0.05 * len(hallucination_types), 0.3)

        return {
            "hallucinations_detected": len(hallucination_types) > 0,
            "hallucination_types": hallucination_types,
            "confidence_penalty": round(penalty, 2),
        }


# ─── 3. Guardrail Pipeline ────────────────────────────────────────────────────


class GuardrailPipeline:
    INPUT_GUARDRAILS = [
        LengthGuardrail(),
        ContentTypeGuardrail(),
        PromptInjectionGuardrail(),
        PIIGuardrail(),
        LanguageGuardrail(),
    ]

    def run_input_checks(self, text: str) -> dict[str, Any]:
        warnings: list[str] = []
        cleaned_text = text
        log_safe_text = text
        pii_detected = False
        pii_types: list[str] = []

        for guardrail in self.INPUT_GUARDRAILS:
            result = guardrail.check(cleaned_text)

            if not result.passed and result.severity == "high":
                return {
                    "blocked": True,
                    "block_reason": result.reason,
                    "warnings": warnings,
                    "cleaned_text": cleaned_text,
                    "pii_detected": pii_detected,
                    "pii_types": pii_types,
                    "log_safe_text": log_safe_text,
                }

            if result.warning:
                warnings.append(result.warning)
            if result.cleaned_text:
                cleaned_text = result.cleaned_text
            if result.log_safe_text:
                log_safe_text = result.log_safe_text
            if result.pii_detected:
                pii_detected = True
                pii_types.extend(result.pii_types)

            if not result.passed:
                return {
                    "blocked": True,
                    "block_reason": result.reason,
                    "warnings": warnings,
                    "cleaned_text": cleaned_text,
                    "pii_detected": pii_detected,
                    "pii_types": pii_types,
                    "log_safe_text": log_safe_text,
                }

        return {
            "blocked": False,
            "block_reason": None,
            "warnings": warnings,
            "cleaned_text": cleaned_text,
            "pii_detected": pii_detected,
            "pii_types": pii_types,
            "log_safe_text": log_safe_text,
        }

    def run_output_checks(self, input_text: str, model_response: dict) -> dict[str, Any]:
        validator = ResponseValidator()
        hallucination = HallucinationDetector()

        val_result = validator.check(input_text, model_response)
        hall_result = hallucination.check(input_text, model_response)

        warnings: list[str] = []
        if val_result.warning:
            warnings.append(val_result.warning)
        if hall_result["hallucinations_detected"]:
            warnings.append(f"Hallucinations detected: {', '.join(hall_result['hallucination_types'])}")

        return {
            "passed": val_result.passed,
            "warnings": warnings,
            "hallucinations": hall_result,
        }


# ─── Backward-Compatible GuardrailService ─────────────────────────────────────


class GuardrailService:
    """Backward-compatible wrapper used by the existing router."""

    def __init__(self):
        self.pipeline = GuardrailPipeline()
        self.last_pipeline_result: dict | None = None

    def validate_input(self, text: str):
        result = self.pipeline.run_input_checks(text)
        self.last_pipeline_result = result
        if result["blocked"]:
            raise GuardrailError(result["block_reason"] or "Input rejected.")

    def validate_output(self, text: str):
        if len(text) > settings.max_output_length:
            raise GuardrailError(
                f"Output exceeds maximum length of {settings.max_output_length} characters."
            )

    def contains_code(self, text: str) -> bool:
        code_indicators = [
            r"def\s+\w+\s*\(", r"class\s+\w+", r"import\s+\w+",
            r"function\s+\w+\s*\(", r"<[a-z]+>", r"\{|\}",
            r"SELECT\s+.*\s+FROM", r"console\.log",
        ]
        for pat in code_indicators:
            if re.search(pat, text):
                return True
        return False
