import json

import httpx
import pytest

from services.grammar_service import GrammarService


@pytest.mark.asyncio
async def test_check_returns_parsed_json(httpx_mock):
    fake_response = {
        "response": json.dumps({
            "corrected_text": "I have gone to the store.",
            "errors": [
                {"original": "has went", "corrected": "have gone",
                 "type": "grammar", "reason": "Incorrect verb tense"}
            ],
            "summary": "Text has one grammar error."
        })
    }
    httpx_mock.add_response(url="http://localhost:11434/api/generate", json=fake_response)

    svc = GrammarService(client=httpx.AsyncClient())
    result = await svc.check("I has went to teh store.")
    await svc.close()

    assert result["corrected_text"] == "I have gone to the store."
    assert len(result["errors"]) == 1
    assert result["_latency_ms"] > 0


@pytest.mark.asyncio
async def test_check_ollama_running_true(httpx_mock):
    httpx_mock.add_response(url="http://localhost:11434/api/tags", status_code=200)
    svc = GrammarService(client=httpx.AsyncClient())
    ok = await svc.check_ollama_running()
    await svc.close()
    assert ok is True


@pytest.mark.asyncio
async def test_check_ollama_running_false(httpx_mock):
    httpx_mock.add_response(url="http://localhost:11434/api/tags", status_code=503)
    svc = GrammarService(client=httpx.AsyncClient())
    ok = await svc.check_ollama_running()
    await svc.close()
    assert ok is False


@pytest.mark.asyncio
async def test_check_ollama_connection_error(httpx_mock):
    httpx_mock.add_exception(httpx.ConnectError("Connection refused"))
    svc = GrammarService(client=httpx.AsyncClient())
    ok = await svc.check_ollama_running()
    await svc.close()
    assert ok is False
