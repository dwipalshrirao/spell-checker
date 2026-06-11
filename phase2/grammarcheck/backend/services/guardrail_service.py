import re

from config import settings

PII_PATTERNS = [
    r"\b\d{3}[-.]?\d{3}[-.]?\d{4}\b",
    r"\b[\w.-]+@[\w.-]+\.\w+\b",
    r"\b\d{3}-\d{2}-\d{4}\b",
]


class GuardrailError(Exception):
    pass


class GuardrailService:
    def validate_input(self, text: str):
        if not text or not text.strip():
            raise GuardrailError("Input text is empty.")

        if len(text) > settings.max_input_length:
            raise GuardrailError(
                f"Input exceeds maximum length of {settings.max_input_length} characters "
                f"({len(text)} given)."
            )

        for pattern in PII_PATTERNS:
            if re.search(pattern, text):
                raise GuardrailError(
                    "Input appears to contain personal information "
                    "(phone number, email, or SSN). This tool is privacy-first "
                    "and does not process such data."
                )

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
