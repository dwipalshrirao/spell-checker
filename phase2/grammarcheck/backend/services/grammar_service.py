import json
import time

import httpx

from config import settings

SYSTEM_PROMPT = """\
You are an expert English grammar and spelling checker.
Your job is to analyse text submitted by the user, find ALL errors, and return a JSON response.

Return ONLY valid JSON — no markdown, no code fences, no extra text.

The JSON must follow this exact schema:
{
  "corrected_text": "<full corrected version of the text>",
  "errors": [
    {
      "original": "<exact wrong word/phrase from input>",
      "corrected": "<correct word/phrase>",
      "type": "<one of: spelling | grammar | punctuation | style | word_choice>",
      "reason": "<clear, concise explanation of why this is wrong and what the fix does>"
    }
  ],
  "summary": "<one-sentence overall assessment of the text quality>"
}

Rules:
- If the text has no errors, return an empty list for "errors" and say so in summary.
- Preserve the original meaning — do not rewrite sentences unnecessarily.
- Be specific in reasons, e.g. "misteks → mistakes: phonetic misspelling" not just "wrong spelling".
- Identify overlapping errors as separate items when the error type differs.
"""


class GrammarService:
    def __init__(self, client: httpx.AsyncClient | None = None):
        self.client = client or httpx.AsyncClient(timeout=120.0)

    async def check(self, text: str, model: str | None = None) -> dict:
        payload = {
            "model": model or settings.ollama_model,
            "system": SYSTEM_PROMPT,
            "prompt": text,
            "stream": False,
            "format": "json",
            "options": {
                "temperature": 0.1,
                "top_p": 0.9,
            },
        }

        start = time.monotonic()
        response = await self.client.post(settings.ollama_url, json=payload)
        elapsed = time.monotonic() - start

        response.raise_for_status()
        raw = response.json().get("response", "")
        raw = raw.strip().lstrip("```json").lstrip("```").rstrip("```").strip()

        result = json.loads(raw)
        result["_latency_ms"] = round(elapsed * 1000, 1)
        return result

    async def check_ollama_running(self) -> bool:
        try:
            r = await self.client.get(
                "http://localhost:11434/api/tags", timeout=3.0
            )
            return r.status_code == 200
        except (httpx.ConnectError, httpx.TimeoutException):
            return False

    async def close(self):
        await self.client.aclose()
