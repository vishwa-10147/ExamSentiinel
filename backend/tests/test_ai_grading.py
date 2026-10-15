"""Advisory AI grade suggestions (Gemini REST API, faked here)."""

import json

import httpx

from app.services.ai_grading import AIGradingService


def _service(monkeypatch, handler, key="test-key"):
    monkeypatch.setenv("GEMINI_API_KEY", key)
    return AIGradingService(transport=httpx.MockTransport(handler))


async def test_suggestion_is_parsed_and_clamped(monkeypatch):
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["url"], seen["key"] = str(request.url), request.headers.get("x-goog-api-key")
        seen["prompt"] = json.loads(request.content)["contents"][0]["parts"][0]["text"]
        text = "SCORE: 12\nFEEDBACK: Clear explanation, missing an example."
        return httpx.Response(200, json={"candidates": [{"content": {"parts": [{"text": text}]}}]})

    result = await _service(monkeypatch, handler).suggest_grade("Explain caching", {"clarity": 5}, 10.0, "A cache stores...")
    assert result == {"suggested_marks": 10.0, "feedback": "Clear explanation, missing an example."}  # clamped to max
    assert seen["url"].endswith("/models/gemini-2.0-flash:generateContent")
    assert "key=" not in seen["url"] and seen["key"] == "test-key"  # the key never goes in the URL
    assert "A cache stores..." in seen["prompt"]


async def test_failures_fall_back_to_manual_grading(monkeypatch):
    result = await _service(monkeypatch, lambda request: httpx.Response(500, json={})).suggest_grade("Q", {}, 5.0, "A")
    assert result["suggested_marks"] == 0.0 and "manually" in result["feedback"]


async def test_without_a_key_nothing_is_sent(monkeypatch):
    calls = []
    service = _service(monkeypatch, lambda request: calls.append(request) or httpx.Response(200), key="")
    assert service.model is None
    result = await service.suggest_grade("Q", {}, 5.0, "A")
    assert "not configured" in result["feedback"] and calls == []
