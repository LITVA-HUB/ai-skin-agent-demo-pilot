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

OLD_SALES_BLOCK_LABELS = (
    "Что это даст образу:",
    "Что я беру в набор:",
    "Что делаем дальше:",
)

FORBIDDEN_STYLE_PATTERNS = [
    r"словно после .*спа",
    r"абсолютн(?:ого|ый) комфорт",
    r"премиальн(?:ого|ый) уход",
    r"наслад",
    r"безупречн",
    r"идеальн(?:ое|ый) покрыти",
    r"уже сегодня вечером",
]

OUTCOME_HINT_PATTERNS = [
    r"лиц",
    r"кож",
    r"тон",
    r"взгляд",
    r"финиш",
    r"текстур",
    r"свеже",
    r"ровн",
    r"спокойн",
    r"сия",
    r"матов",
]

CONVERSATIONAL_REASONING_HINTS = [
    r"потому что",
    r"за сч[её]т этого",
    r"логика простая",
    r"поэтому",
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


def validate_response_quality(text: str, recommendations: list[RecommendationItem]) -> bool:
    normalized = text.strip()
    if not normalized:
        return False

    lower = normalized.lower()
    if any(re.search(pattern, lower) for pattern in FORBIDDEN_STYLE_PATTERNS):
        return False

    if all(label in normalized for label in OLD_SALES_BLOCK_LABELS):
        return False

    if recommendations:
        product_tokens: set[str] = set()
        for item in recommendations[:3]:
            for token in re.findall(r"[a-zа-я0-9]+", item.title.lower()):
                if len(token) >= 4:
                    product_tokens.add(token)
        if product_tokens and not any(token in lower for token in product_tokens):
            return False

    if not any(re.search(pattern, lower) for pattern in OUTCOME_HINT_PATTERNS):
        return False

    if len(normalized.split()) < 10:
        return False

    if re.search(r"\bдобавьте\b", lower):
        return False

    if not any(re.search(pattern, lower) for pattern in CONVERSATIONAL_REASONING_HINTS) and "если хочешь" not in lower and "могу" not in lower:
        return False

    return True
