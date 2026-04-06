from __future__ import annotations

import re

from .models import RecommendationItem


def validate_response_grounding(text: str, recommendations: list[RecommendationItem]) -> bool:
    if not text.strip():
        return False
    if not recommendations:
        return True
    normalized = text.lower()
    allowed_tokens: set[str] = set()
    for item in recommendations[:3]:
        allowed_tokens.add(item.brand.lower())
        allowed_tokens.add(item.category.value.lower())
        for token in re.findall(r"[a-zа-я0-9]+", item.title.lower()):
            if len(token) >= 4:
                allowed_tokens.add(token)
    matches = [token for token in allowed_tokens if token and token in normalized]
    return len(matches) >= 2
