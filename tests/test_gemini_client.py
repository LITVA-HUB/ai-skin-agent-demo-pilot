import asyncio

import httpx

from app.gemini_client import GeminiClient


class _FakeResponse:
    def __init__(self, data: dict):
        self._data = data
        self.status_code = 200
        self.text = ""
        self.reason_phrase = "OK"

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict:
        return self._data


class _FakeAsyncClient:
    def __init__(self, *args, **kwargs):
        self.calls = kwargs.pop("calls")

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def post(self, url, headers=None, json=None):
        self.calls.append({"url": url, "headers": headers, "json": json})
        return _FakeResponse({
            "choices": [
                {"message": {"content": '{"intent":"general_advice","action":"recommend","domain":"skincare","target_category":null,"target_categories":[],"target_product":null,"target_products":[],"target_domain":null,"preference_updates":{},"constraints_update":{},"confidence":0.9}'}}
            ]
        })


def test_openrouter_parse_intent_uses_chat_completions(monkeypatch) -> None:
    calls = []

    def factory(*args, **kwargs):
        kwargs["calls"] = calls
        return _FakeAsyncClient(*args, **kwargs)

    monkeypatch.setattr(httpx, "AsyncClient", factory)

    client = GeminiClient(
        provider="openrouter",
        api_key="test-openrouter-key",
        model="gemini-3.1-flash-lite-preview",
    )
    intent = asyncio.run(client.parse_intent("сделай вариант дешевле", "budget=mid"))

    assert intent is not None
    assert calls
    request = calls[0]
    assert request["url"] == "https://openrouter.ai/api/v1/chat/completions"
    assert request["headers"]["Authorization"] == "Bearer test-openrouter-key"
    assert request["json"]["model"] == "google/gemini-3.1-flash-lite-preview"
    assert request["json"]["response_format"] == {"type": "json_object"}
    assert request["json"]["messages"][0]["content"][0]["type"] == "text"


def test_openrouter_analyze_photo_sends_data_url(monkeypatch) -> None:
    calls = []

    class _VisionAsyncClient(_FakeAsyncClient):
        async def post(self, url, headers=None, json=None):
            self.calls.append({"url": url, "headers": headers, "json": json})
            return _FakeResponse({
                "choices": [
                    {"message": {"content": '{"image_check":{"face_detected":true,"skin_region_detected":true,"blur_score":0.1,"lighting_score":0.8,"makeup_possible":false,"usable":true},"signals":{"oiliness":0.2,"dryness":0.3,"redness":0.1,"breakouts":0.0,"tone_evenness":0.7,"sensitivity_signs":0.1},"complexion":{"skin_tone":"light","undertone":"neutral","under_eye_darkness":0.2,"visible_shine":0.1,"texture_visibility":0.3},"limitations":[],"confidence":0.9}'}}
                ]
            })

    def factory(*args, **kwargs):
        kwargs["calls"] = calls
        return _VisionAsyncClient(*args, **kwargs)

    monkeypatch.setattr(httpx, "AsyncClient", factory)

    client = GeminiClient(
        provider="openrouter",
        api_key="test-openrouter-key",
        model="google/gemini-3.1-flash-lite-preview",
    )
    result = asyncio.run(client.analyze_photo("data:image/png;base64,ZmFrZQ=="))

    assert result is not None
    assert result.source == "openrouter"
    content = calls[0]["json"]["messages"][0]["content"]
    assert content[1]["type"] == "image_url"
    assert content[1]["image_url"]["url"] == "data:image/png;base64,ZmFrZQ=="
