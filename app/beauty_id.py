from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from .models import (
    AllergenLibraryItem,
    AllergenLibraryResponse,
    AnalysisHistoryEntry,
    BeautyMetricCard,
    BeautyScanPayload,
    DemoProfileSummary,
    FaceScanZone,
    HalalStatus,
    OrderHistoryEntry,
    ProductCategory,
    RecommendationItem,
    SessionState,
)

METRIC_META = {
    "oiliness": "Жирность",
    "dryness": "Сухость",
    "redness": "Покраснение",
    "breakouts": "Высыпания",
    "tone_evenness": "Ровность тона",
    "sensitivity_signs": "Чувствительность",
    "under_eye_darkness": "Зона под глазами",
    "visible_shine": "Блеск",
    "texture_visibility": "Текстура кожи",
}

ZONE_LABELS = {
    "forehead": "Лоб",
    "left_cheek": "Левая щека",
    "right_cheek": "Правая щека",
    "nose": "Т-зона",
    "under_eyes": "Под глазами",
    "chin": "Подбородок",
}

SKIN_TYPE_LABELS = {
    "dry": "сухая",
    "oily": "жирная",
    "combination": "комбинированная",
    "normal": "нормальная",
    "sensitive": "чувствительная",
}

TONE_LABELS = {
    "fair": "очень светлый",
    "light": "светлый",
    "light_medium": "светло-средний",
    "medium": "средний",
    "tan": "смуглый",
    "deep": "глубокий",
}

UNDERTONE_LABELS = {
    "cool": "холодный",
    "neutral": "нейтральный",
    "warm": "тёплый",
    "olive": "оливковый",
}

CONCERN_LABELS = {
    "redness": "покраснение",
    "breakouts": "высыпания",
    "dryness": "сухость",
    "oiliness": "жирность",
    "maintenance": "поддержание баланса",
    "tone_match": "выравнивание тона",
    "under_eye": "зона под глазами",
}

FINISH_LABELS = {
    "natural": "натуральный",
    "radiant": "сияющий",
    "matte": "матовый",
    "satin": "сатиновый",
}

COVERAGE_LABELS = {
    "sheer": "лёгкое",
    "light": "лёгкое",
    "medium": "среднее",
    "full": "плотное",
}

BUDGET_LABELS = {
    "cheaper": "сделать дешевле",
    "same": "без смещения по цене",
    "premium": "смещение в премиум",
}

ZONE_LAYOUT = {
    "forehead": (0.3, 0.12, 0.4, 0.16, "visible_shine"),
    "left_cheek": (0.12, 0.34, 0.24, 0.2, "redness"),
    "right_cheek": (0.64, 0.34, 0.24, 0.2, "redness"),
    "nose": (0.42, 0.29, 0.16, 0.24, "oiliness"),
    "under_eyes": (0.25, 0.41, 0.5, 0.1, "under_eye_darkness"),
    "chin": (0.34, 0.62, 0.32, 0.16, "texture_visibility"),
}

ZONE_CATEGORIES = {
    "under_eyes": {ProductCategory.concealer},
    "nose": {ProductCategory.powder, ProductCategory.primer},
    "forehead": {ProductCategory.powder, ProductCategory.skin_tint, ProductCategory.foundation},
    "left_cheek": {ProductCategory.foundation, ProductCategory.skin_tint, ProductCategory.serum, ProductCategory.moisturizer},
    "right_cheek": {ProductCategory.foundation, ProductCategory.skin_tint, ProductCategory.serum, ProductCategory.moisturizer},
    "chin": {ProductCategory.serum, ProductCategory.spot_treatment, ProductCategory.foundation, ProductCategory.skin_tint},
}


def severity(score: float) -> str:
    if score >= 0.72:
        return "high"
    if score >= 0.45:
        return "medium"
    return "low"


@lru_cache(maxsize=1)
def allergen_library() -> AllergenLibraryResponse:
    path = Path(__file__).parent / "data" / "allergen_library.json"
    raw = json.loads(path.read_text(encoding="utf-8"))
    return AllergenLibraryResponse(
        common_allergens=[AllergenLibraryItem.model_validate(item) for item in raw.get("common_allergens", [])],
        sensitivity_exclusions=[AllergenLibraryItem.model_validate(item) for item in raw.get("sensitivity_exclusions", [])],
    )


def build_scan_payload(session: SessionState, recommendations: list[RecommendationItem]) -> BeautyScanPayload:
    analysis = session.photo_analysis
    metrics = [
        BeautyMetricCard(key="oiliness", label=METRIC_META["oiliness"], score=analysis.signals.oiliness, severity=severity(analysis.signals.oiliness)),
        BeautyMetricCard(key="dryness", label=METRIC_META["dryness"], score=analysis.signals.dryness, severity=severity(analysis.signals.dryness)),
        BeautyMetricCard(key="redness", label=METRIC_META["redness"], score=analysis.signals.redness, severity=severity(analysis.signals.redness)),
        BeautyMetricCard(key="breakouts", label=METRIC_META["breakouts"], score=analysis.signals.breakouts, severity=severity(analysis.signals.breakouts)),
        BeautyMetricCard(key="tone_evenness", label=METRIC_META["tone_evenness"], score=analysis.signals.tone_evenness, severity=severity(1 - analysis.signals.tone_evenness)),
        BeautyMetricCard(key="sensitivity_signs", label=METRIC_META["sensitivity_signs"], score=analysis.signals.sensitivity_signs, severity=severity(analysis.signals.sensitivity_signs)),
        BeautyMetricCard(key="under_eye_darkness", label=METRIC_META["under_eye_darkness"], score=analysis.complexion.under_eye_darkness, severity=severity(analysis.complexion.under_eye_darkness)),
        BeautyMetricCard(key="visible_shine", label=METRIC_META["visible_shine"], score=analysis.complexion.visible_shine, severity=severity(analysis.complexion.visible_shine)),
        BeautyMetricCard(key="texture_visibility", label=METRIC_META["texture_visibility"], score=analysis.complexion.texture_visibility, severity=severity(analysis.complexion.texture_visibility)),
    ]
    metric_map = {item.key: item.score for item in metrics}
    zones = [
        FaceScanZone(zone=zone, label=ZONE_LABELS.get(zone, zone.replace("_", " ").title()), x=x, y=y, width=w, height=h, intensity=metric_map.get(metric_key, 0.3), metric_key=metric_key)
        for zone, (x, y, w, h, metric_key) in ZONE_LAYOUT.items()
    ]

    hotspots = []
    used = set()
    for zone, cats in ZONE_CATEGORIES.items():
        match = next((item for item in recommendations if item.category in cats and item.sku not in used), None)
        if not match:
            continue
        x, y, _, _, _ = ZONE_LAYOUT[zone]
        hotspots.append({
            "zone": zone,
            "label": ZONE_LABELS.get(zone, zone.replace("_", " ").title()),
            "x": x + 0.05,
            "y": y + 0.04,
            "sku": match.sku,
            "category": match.category,
            "title": match.title,
            "why": match.why,
        })
        used.add(match.sku)

    summary_lines = []
    if analysis.signals.redness >= 0.45:
        summary_lines.append("Есть заметные сигналы покраснения, поэтому лучше работают более спокойные и мягкие текстуры.")
    if analysis.complexion.visible_shine >= 0.55:
        summary_lines.append("В Т-зоне заметен блеск, поэтому подборка смещена в сторону более сбалансированных и мягко фиксирующих текстур.")
    if analysis.complexion.under_eye_darkness >= 0.45:
        summary_lines.append("Зоне под глазами подойдёт более выравнивающая и освежающая поддержка.")
    if not summary_lines:
        summary_lines.append("Скан выглядит достаточно ровно, поэтому корзина собрана вокруг понятного ежедневного набора без перегруза.")

    return BeautyScanPayload(
        title="Сканирование завершено",
        subtitle="Видимые косметические сигналы собраны в понятный skincare и complexion набор.",
        metrics=metrics,
        zones=zones,
        product_hotspots=hotspots,
        summary_lines=summary_lines,
    )


def build_profile_summary(session: SessionState) -> DemoProfileSummary:
    prefs = session.user_preferences
    profile = session.skin_profile
    concerns = [CONCERN_LABELS.get(item.value, item.value.replace("_", " ")) for item in profile.primary_concerns]
    beauty_summary = (
        f"{SKIN_TYPE_LABELS.get(profile.skin_type.value, profile.skin_type.value)} кожа"
        f" с фокусом на {', '.join(concerns) or 'ежедневный баланс'} и на понятный guided-набор."
    )
    exclusions = list(dict.fromkeys([*prefs.excluded_ingredients, *prefs.excluded_common_allergens, *prefs.excluded_sensitivity_triggers]))
    return DemoProfileSummary(
        user_id=session.demo_user_id,
        name=prefs.profile_name,
        beauty_summary=beauty_summary,
        skin_snapshot=[
            f"Тип кожи: {SKIN_TYPE_LABELS.get(profile.skin_type.value, profile.skin_type.value)}",
            f"Тон: {TONE_LABELS.get(profile.complexion.skin_tone.value, profile.complexion.skin_tone.value) if profile.complexion.skin_tone else 'приблизительно'}",
            f"Подтон: {UNDERTONE_LABELS.get(profile.complexion.undertone.value, profile.complexion.undertone.value) if profile.complexion.undertone else 'приблизительно'}",
        ],
        sensitivity_exclusions=exclusions,
        halal_preference="только halal-friendly" if prefs.halal_only else "не зафиксировано",
        preferred_finish=[FINISH_LABELS.get(item.value, item.value) for item in prefs.preferred_finish],
        preferred_coverage=[COVERAGE_LABELS.get(item.value, item.value) for item in prefs.preferred_coverage],
        budget_direction=BUDGET_LABELS.get(prefs.budget_direction.value, prefs.budget_direction.value),
        future_features=[
            "Расширенный try-on — позже в premium-подписке",
            "Ежемесячная Beauty ID история — позже в premium-подписке",
            "Сезонные pro-рекомендации — позже в premium-подписке",
        ],
    )


def build_cabinet(profile: DemoProfileSummary, analysis_history: list[AnalysisHistoryEntry], order_history: list[OrderHistoryEntry]):
    from .models import CabinetResponse

    return CabinetResponse(profile=profile, analysis_history=analysis_history, order_history=order_history)


def halal_badge(status: HalalStatus) -> str | None:
    if status == HalalStatus.certified:
        return "Подтверждён halal"
    if status == HalalStatus.friendly:
        return "Halal-friendly"
    return None
