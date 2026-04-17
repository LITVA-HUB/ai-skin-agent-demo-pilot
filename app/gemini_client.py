from __future__ import annotations

import base64
import json
from typing import Any

import httpx

from .config import settings
from .models import DialogIntent, PhotoAnalysisResult
from .observability import log_error, log_warning


VISION_PROMPT = """
You are a strict vision parser for a Golden Apple beauty advisor.
Return only valid JSON with this exact schema:
{
  "image_check": {
    "face_detected": true,
    "skin_region_detected": true,
    "blur_score": 0.0,
    "lighting_score": 0.0,
    "makeup_possible": false,
    "usable": true
  },
  "signals": {
    "oiliness": 0.0,
    "dryness": 0.0,
    "redness": 0.0,
    "breakouts": 0.0,
    "tone_evenness": 0.0,
    "sensitivity_signs": 0.0
  },
  "complexion": {
    "skin_tone": "fair|light|light_medium|medium|tan|deep|null",
    "undertone": "cool|neutral|warm|olive|null",
    "under_eye_darkness": 0.0,
    "visible_shine": 0.0,
    "texture_visibility": 0.0
  },
  "limitations": ["string"],
  "confidence": 0.0
}
Use normalized values 0..1. Do not give product advice. Treat skin_tone and undertone as approximate only. If image quality is too poor, set usable=false.
""".strip()


MODEL_ALIASES = {
    "gemini-3.1-flash-light": "gemini-3.1-flash-lite",
    "gemini 3.1 flash lite": "gemini-3.1-flash-lite",
    "gemini-3-flash-lite": "gemini-3.1-flash-lite",
}

OPENROUTER_MODEL_ALIASES = {
    "gemini-3.1-flash-lite-preview": "google/gemini-3.1-flash-lite-preview",
    "gemini-3.1-flash-lite": "google/gemini-3.1-flash-lite-preview",
    "gemini 3.1 flash lite preview": "google/gemini-3.1-flash-lite-preview",
    "gemini 3.1 flash lite": "google/gemini-3.1-flash-lite-preview",
    "google/gemini-3.1-flash-lite": "google/gemini-3.1-flash-lite-preview",
}


class GeminiClient:
    def __init__(self, api_key: str | None = None, model: str | None = None, provider: str | None = None) -> None:
        self.provider = (provider or settings.llm_provider or "gemini").strip().lower()
        if self.provider == "openrouter":
            self.api_key = api_key or settings.openrouter_api_key
            self.model = model or settings.openrouter_model
        else:
            self.provider = "gemini"
            self.api_key = api_key or settings.gemini_api_key
            self.model = model or settings.gemini_model
        self.active_provider = self.provider
        self.active_model = self.model
        self.last_error: str | None = None

    def _normalize_model(self, value: str | None) -> str | None:
        raw = (value or "").strip()
        if not raw:
            return None
        key = raw.lower().replace("_", "-")
        return MODEL_ALIASES.get(key, raw)

    def _normalize_openrouter_model(self, value: str | None) -> str | None:
        raw = (value or "").strip()
        if not raw:
            return None
        key = raw.lower().replace("_", "-")
        return OPENROUTER_MODEL_ALIASES.get(key, raw)

    def _candidate_models(self) -> list[str]:
        if self.provider == "openrouter":
            normalized = self._normalize_openrouter_model(self.model)
            models = [
                normalized,
                self.model,
                "google/gemini-3.1-flash-lite-preview",
                "google/gemini-2.5-flash-lite",
            ]
            deduped: list[str] = []
            for item in models:
                if item and item not in deduped:
                    deduped.append(item)
            return deduped

        normalized = self._normalize_model(self.model)
        preview_variant = None
        if normalized == "gemini-3.1-flash-lite" or self.model == "gemini-3.1-flash-lite":
            preview_variant = "gemini-3.1-flash-lite-preview"
        models = [
            self.model,
            normalized,
            preview_variant,
            "gemini-2.5-flash-lite",
            "gemini-2.5-flash",
        ]
        deduped: list[str] = []
        for item in models:
            if item and item not in deduped:
                deduped.append(item)
        return deduped

    def _openrouter_content(self, parts: list[dict[str, Any]]) -> list[dict[str, Any]]:
        content: list[dict[str, Any]] = []
        for part in parts:
            text = part.get("text")
            if isinstance(text, str):
                content.append({"type": "text", "text": text})
                continue
            inline = part.get("inline_data")
            if isinstance(inline, dict):
                mime_type = str(inline.get("mime_type") or "image/jpeg")
                data = str(inline.get("data") or "")
                if data:
                    content.append({
                        "type": "image_url",
                        "image_url": {"url": f"data:{mime_type};base64,{data}"},
                    })
        return content

    def _extract_openrouter_text(self, data: dict[str, Any]) -> str:
        message = data["choices"][0]["message"]["content"]
        if isinstance(message, str):
            return message
        if isinstance(message, list):
            chunks: list[str] = []
            for item in message:
                if isinstance(item, dict) and item.get("type") == "text" and isinstance(item.get("text"), str):
                    chunks.append(item["text"])
            if chunks:
                return "\n".join(chunks)
        raise KeyError("OpenRouter response did not include message content.")

    async def _generate_openrouter(self, parts: list[dict[str, Any]], response_mime_type: str = "application/json") -> str | None:
        if not self.api_key:
            self.last_error = "OPENROUTER_API_KEY is not configured."
            return None

        errors: list[str] = []
        alias_model = self._normalize_openrouter_model(self.model)
        last_attempted_model = alias_model or self.model
        base_headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        if settings.openrouter_site_url:
            base_headers["HTTP-Referer"] = settings.openrouter_site_url
        if settings.openrouter_app_name:
            base_headers["X-Title"] = settings.openrouter_app_name

        for candidate_model in self._candidate_models():
            last_attempted_model = candidate_model
            payload: dict[str, Any] = {
                "model": candidate_model,
                "messages": [{"role": "user", "content": self._openrouter_content(parts)}],
                "temperature": 0.2,
            }
            if response_mime_type == "application/json":
                payload["response_format"] = {"type": "json_object"}
            try:
                async with httpx.AsyncClient(timeout=45) as client:
                    response = await client.post("https://openrouter.ai/api/v1/chat/completions", headers=base_headers, json=payload)
                    response.raise_for_status()
                data = response.json()
                text = self._extract_openrouter_text(data)
                self.active_provider = "openrouter"
                self.active_model = candidate_model
                self.last_error = None
                if alias_model and alias_model != self.model and candidate_model == alias_model:
                    log_warning(
                        "openrouter_model_alias_used",
                        requested_model=self.model,
                        active_model=candidate_model,
                    )
                if candidate_model != self.model:
                    log_warning(
                        "openrouter_model_fallback_used",
                        requested_model=self.model,
                        active_model=candidate_model,
                    )
                return text
            except httpx.HTTPStatusError as exc:
                detail = ""
                try:
                    detail = exc.response.json().get("error", {}).get("message", "") or exc.response.text
                except Exception:
                    detail = exc.response.text
                detail = " ".join(detail.split())
                errors.append(f"{candidate_model}: {detail or exc.response.reason_phrase}")
                log_error(
                    "openrouter_http_error",
                    model=candidate_model,
                    status_code=exc.response.status_code,
                    detail=detail[:400],
                )
            except (httpx.HTTPError, KeyError, ValueError, json.JSONDecodeError) as exc:
                errors.append(f"{candidate_model}: {exc}")
                log_error("openrouter_request_failed", model=candidate_model, detail=str(exc)[:400])

        self.active_provider = "openrouter"
        self.active_model = last_attempted_model
        self.last_error = errors[0] if errors else "OpenRouter request failed."
        return None

    async def _generate(self, parts: list[dict[str, Any]], response_mime_type: str = "application/json") -> str | None:
        if self.provider == "openrouter":
            return await self._generate_openrouter(parts, response_mime_type=response_mime_type)

        if not self.api_key:
            self.last_error = "GEMINI_API_KEY is not configured."
            return None

        payload: dict[str, Any] = {
            "generationConfig": {"temperature": 0.2, "responseMimeType": response_mime_type},
            "contents": [{"parts": parts}],
        }
        errors: list[str] = []
        alias_model = self._normalize_model(self.model)
        last_attempted_model = alias_model or self.model

        for candidate_model in self._candidate_models():
            last_attempted_model = candidate_model
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{candidate_model}:generateContent?key={self.api_key}"
            try:
                async with httpx.AsyncClient(timeout=45) as client:
                    response = await client.post(url, json=payload)
                    response.raise_for_status()
                data = response.json()
                text = data["candidates"][0]["content"]["parts"][0]["text"]
                self.active_provider = "gemini"
                self.active_model = candidate_model
                self.last_error = None
                if alias_model and alias_model != self.model and candidate_model == alias_model:
                    log_warning(
                        "gemini_model_alias_used",
                        requested_model=self.model,
                        active_model=candidate_model,
                    )
                if candidate_model != self.model:
                    log_warning(
                        "gemini_model_fallback_used",
                        requested_model=self.model,
                        active_model=candidate_model,
                    )
                return text
            except httpx.HTTPStatusError as exc:
                detail = ""
                try:
                    detail = exc.response.json().get("error", {}).get("message", "") or exc.response.text
                except Exception:
                    detail = exc.response.text
                detail = " ".join(detail.split())
                errors.append(f"{candidate_model}: {detail or exc.response.reason_phrase}")
                log_error(
                    "gemini_http_error",
                    model=candidate_model,
                    status_code=exc.response.status_code,
                    detail=detail[:400],
                )
                if "User location is not supported" in detail:
                    break
            except (httpx.HTTPError, KeyError, ValueError, json.JSONDecodeError) as exc:
                errors.append(f"{candidate_model}: {exc}")
                log_error("gemini_request_failed", model=candidate_model, detail=str(exc)[:400])

        self.active_provider = "gemini"
        self.active_model = last_attempted_model
        if errors:
            preferred_error = next((item for item in errors if "User location is not supported" in item), None)
            preferred_error = preferred_error or next((item for item in errors if "Quota exceeded" in item), None)
            self.last_error = preferred_error or errors[0]
            if self.last_error and ":" in self.last_error:
                model_name = self.last_error.split(":", 1)[0].strip()
                if model_name:
                    self.active_model = model_name
        else:
            self.last_error = "Gemini request failed."
        return None

    async def ping(self) -> bool:
        text = await self._generate(
            [{"text": "Reply with exactly: OK"}],
            response_mime_type="text/plain",
        )
        return bool(text and text.strip().upper() == "OK")

    async def analyze_photo(self, photo_b64: str) -> PhotoAnalysisResult | None:
        mime_type = "image/jpeg"
        if photo_b64.startswith("data:"):
            header, encoded = photo_b64.split(",", 1)
            photo_b64 = encoded
            if ";base64" in header:
                mime_type = header.split(";")[0].split(":", 1)[1]
        text = await self._generate([
            {"text": VISION_PROMPT},
            {"inline_data": {"mime_type": mime_type, "data": photo_b64}},
        ])
        if not text:
            return None
        try:
            parsed = json.loads(text)
            parsed["source"] = self.active_provider
            return PhotoAnalysisResult.model_validate(parsed)
        except (ValueError, json.JSONDecodeError):
            return None

    async def parse_intent(self, user_message: str, session_summary: str) -> DialogIntent | None:
        prompt = f"""
You are an intent parser for a Golden Apple beauty advisor.
Return only valid JSON with schema:
{{
  "intent": "general_advice|replace_product|cheaper_alternative|exclude_ingredient|change_brand|simplify_routine|expand_routine|explain_product|compare_products",
  "action": "recommend|replace|compare|explain|simplify|cheaper|refine",
  "domain": "skincare|makeup|hybrid",
  "target_category": "serum|moisturizer|cleanser|spf|toner|foundation|skin_tint|concealer|powder|null",
  "target_categories": ["string"],
  "target_product": null,
  "target_products": ["string"],
  "target_domain": "skincare|makeup|null",
  "preference_updates": {{
    "preferred_finish": ["natural|radiant|matte|satin"],
    "preferred_coverage": ["sheer|light|medium|full"],
    "preferred_brands": ["string"],
    "budget_direction": "cheaper|same|premium",
    "accepted_products": ["string"],
    "rejected_products": ["string"],
    "routine_size": "minimal|standard|extended"
  }},
  "constraints_update": {{
    "budget_segment": "budget|mid|premium",
    "routine_size": "minimal|standard|extended",
    "excluded_ingredients": ["string"],
    "preferred_brands": ["string"],
    "goal": "string",
    "preferred_finish": ["natural|radiant|matte|satin"],
    "preferred_coverage": ["sheer|light|medium|full"],
    "skin_tone": "fair|light|light_medium|medium|tan|deep",
    "undertone": "cool|neutral|warm|olive",
    "skin_type": "dry|oily|combination|normal|sensitive"
  }},
  "confidence": 0.0
}}
Context: {session_summary}
User message: {user_message}
Use compare_products for side-by-side requests, explain_product for "why/explain" asks, and hybrid when the user mixes skincare + complexion makeup.
Only output JSON.
""".strip()
        text = await self._generate([{"text": prompt}])
        if not text:
            return None
        try:
            return DialogIntent.model_validate(json.loads(text))
        except (ValueError, json.JSONDecodeError):
            return None

    async def generate_agent_reply(self, prompt: str) -> str | None:
        text = await self._generate([{"text": prompt}], response_mime_type="text/plain")
        return text.strip() if text else None



def is_probably_base64_image(value: str | None) -> bool:
    if not value:
        return False
    try:
        base64.b64decode(value.split(",")[-1], validate=False)
        return True
    except Exception:
        return False
