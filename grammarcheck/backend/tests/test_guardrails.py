import pytest

from services.guardrail_service import GuardrailError, GuardrailService


def test_validate_input_empty():
    svc = GuardrailService()
    with pytest.raises(GuardrailError, match="empty"):
        svc.validate_input("")
    with pytest.raises(GuardrailError, match="empty"):
        svc.validate_input("   ")


def test_validate_input_too_long():
    svc = GuardrailService()
    long_text = "x" * 6000
    with pytest.raises(GuardrailError, match="exceeds maximum"):
        svc.validate_input(long_text)


def test_validate_input_valid():
    svc = GuardrailService()
    svc.validate_input("Hello, world!")  # should not raise


def test_validate_input_with_phone():
    svc = GuardrailService()
    with pytest.raises(GuardrailError, match="personal information"):
        svc.validate_input("Call me at 555-123-4567")


def test_validate_input_with_email():
    svc = GuardrailService()
    with pytest.raises(GuardrailError, match="personal information"):
        svc.validate_input("Email me at test@example.com")


def test_validate_output_too_long():
    svc = GuardrailService()
    long_text = "x" * 15000
    with pytest.raises(GuardrailError, match="exceeds maximum"):
        svc.validate_output(long_text)


def test_contains_code_true():
    svc = GuardrailService()
    assert svc.contains_code("def foo():") is True


def test_contains_code_false():
    svc = GuardrailService()
    assert svc.contains_code("The quick brown fox.") is False
