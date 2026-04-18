from __future__ import annotations

import json
import sys
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.config import reload_settings


def build_request(settings) -> tuple[str, dict[str, str], dict[str, object]]:
    prompt = 'Return only {"ok": true} as valid JSON.'

    if settings.llm_provider == "openrouter":
        headers = {
            "Authorization": f"Bearer {settings.openrouter_api_key or ''}",
            "Content-Type": "application/json",
        }
        if settings.openrouter_site_url:
            headers["HTTP-Referer"] = settings.openrouter_site_url
        if settings.openrouter_app_name:
            headers["X-Title"] = settings.openrouter_app_name
        payload = {
            "model": settings.openrouter_model,
            "messages": [{"role": "user", "content": [{"type": "text", "text": prompt}]}],
            "response_format": {"type": "json_object"},
            "temperature": 0,
        }
        return "https://openrouter.ai/api/v1/chat/completions", headers, payload

    headers = {"Content-Type": "application/json"}
    payload = {
        "generationConfig": {"temperature": 0, "responseMimeType": "application/json"},
        "contents": [{"parts": [{"text": prompt}]}],
    }
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{settings.gemini_model}:generateContent?key={settings.gemini_api_key or ''}"
    return url, headers, payload


def main() -> int:
    settings = reload_settings()
    url, headers, payload = build_request(settings)
    with httpx.Client(timeout=30, trust_env=False) as client:
        response = client.post(url, headers=headers, json=payload)
    print("provider=", settings.llm_provider)
    print("model=", settings.openrouter_model if settings.llm_provider == "openrouter" else settings.gemini_model)
    print("status=", response.status_code)
    try:
        print(json.dumps(response.json(), ensure_ascii=False, indent=2)[:2000])
    except Exception:
        print(response.text[:2000])
    return 0 if response.is_success else 1


if __name__ == "__main__":
    raise SystemExit(main())
