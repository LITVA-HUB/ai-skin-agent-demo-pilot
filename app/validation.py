from __future__ import annotations

import re

from .models import RecommendationItem

MEDICAL_CLAIM_PATTERNS = [
    r"лечит",
    r"вылеч",
    r"диагноз",
    r"терап",
    r"гормон",
    r"acne cure",
    r"prescription",
]


def validate_response_grounding(text: str, recommendations: list[RecommendationItem]) -> bool:
    if not text.strip():
        return False
    if not recommendations:
        return True
    normalized = text.lower()
    if any(re.search(pattern, normalized) for pattern in MEDICAL_CLAIM_PATTERNS):
        return False
    if re.search(r"\b\d{2,}\s?(?:₽|руб|rub)\b", normalized):
        allowed_prices = {str(item.price_value) for item in recommendations}
        mentioned = set(re.findall(r"\b(\d{2,})\s?(?:₽|руб|rub)\b", normalized))
        if any(price not in allowed_prices for price in mentioned):
            return False
    allowed_tokens: set[str] = set()
    for item in recommendations[:3]:
        allowed_tokens.add(item.brand.lower())
        allowed_tokens.add(item.category.value.lower())
        allowed_tokens.add(str(item.price_value))
        for token in re.findall(r"[a-zа-я0-9]+", item.title.lower()):
            if len(token) >= 4:
                allowed_tokens.add(token)
    matches = [token for token in allowed_tokens if token and token in normalized]
    return len(matches) >= 2
