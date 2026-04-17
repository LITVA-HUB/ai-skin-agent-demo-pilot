from app.models import ProductCategory, ProductDomain, PriceSegment, RecommendationItem
from app.validation import validate_response_grounding, validate_response_quality


def test_validate_response_grounding_accepts_known_product() -> None:
    item = RecommendationItem(
        sku='1', title='Air Touch Concealer LIGHT_NEUTRAL', brand='Shade Atelier', category=ProductCategory.concealer,
        domain=ProductDomain.makeup, price_segment=PriceSegment.mid, price_value=1000, why='ok', vector_score=0.1, rule_score=0.2, final_score=0.3,
    )
    assert validate_response_grounding('Air Touch Concealer here works very well', [item]) is True


def test_validate_response_grounding_rejects_unknown_text() -> None:
    item = RecommendationItem(
        sku='1', title='Air Touch Concealer LIGHT_NEUTRAL', brand='Shade Atelier', category=ProductCategory.concealer,
        domain=ProductDomain.makeup, price_segment=PriceSegment.mid, price_value=1000, why='ok', vector_score=0.1, rule_score=0.2, final_score=0.3,
    )
    assert validate_response_grounding('Kiehls serum is better here', [item]) is False


def test_validate_response_grounding_rejects_unknown_price_claim() -> None:
    item = RecommendationItem(
        sku='1', title='Air Touch Concealer LIGHT_NEUTRAL', brand='Shade Atelier', category=ProductCategory.concealer,
        domain=ProductDomain.makeup, price_segment=PriceSegment.mid, price_value=1000, why='ok', vector_score=0.1, rule_score=0.2, final_score=0.3,
    )
    assert validate_response_grounding('Этот вариант стоит 790 ₽ и лучше', [item]) is False


def test_validate_response_grounding_rejects_medical_claims() -> None:
    item = RecommendationItem(
        sku='1', title='Air Touch Concealer LIGHT_NEUTRAL', brand='Shade Atelier', category=ProductCategory.concealer,
        domain=ProductDomain.makeup, price_segment=PriceSegment.mid, price_value=1000, why='ok', vector_score=0.1, rule_score=0.2, final_score=0.3,
    )
    assert validate_response_grounding('Этот продукт лечит акне за неделю', [item]) is False


def test_validate_response_quality_rejects_over_marketing_copy() -> None:
    item = RecommendationItem(
        sku='1', title='Barrier Cloud Cream Cleanser', brand='Skin Logic', category=ProductCategory.cleanser,
        domain=ProductDomain.skincare, price_segment=PriceSegment.mid, price_value=1290, why='ok', vector_score=0.1, rule_score=0.2, final_score=0.3,
    )
    text = (
        "Что это даст образу: Ваша кожа будет выглядеть безупречно свежей, словно после полноценного отдыха в спа.\n"
        "Что я беру в набор: Barrier Cloud Cream Cleanser бережно удалит загрязнения.\n"
        "Что делаем дальше: Добавьте эти средства в корзину уже сегодня вечером."
    )
    assert validate_response_quality(text, [item]) is False


def test_validate_response_quality_rejects_old_plain_advisor_template() -> None:
    item = RecommendationItem(
        sku='1', title='Barrier Cloud Cream Cleanser', brand='Skin Logic', category=ProductCategory.cleanser,
        domain=ProductDomain.skincare, price_segment=PriceSegment.mid, price_value=1290, why='ok', vector_score=0.1, rule_score=0.2, final_score=0.3,
    )
    text = (
        "Что это даст образу: Кожа будет выглядеть спокойнее и чище, а общий тон — свежее.\n"
        "Что я беру в набор: Barrier Cloud Cream Cleanser нужен как мягкий старт, чтобы убрать лишний визуальный шум с кожи.\n"
        "Что делаем дальше: Если хочешь, я могу сразу собрать к нему ещё один спокойный вечерний шаг."
    )
    assert validate_response_quality(text, [item]) is False


def test_validate_response_quality_accepts_conversational_reply() -> None:
    item = RecommendationItem(
        sku='1', title='Soft Blur Foundation LIGHT_NEUTRAL', brand='Shade Atelier', category=ProductCategory.foundation,
        domain=ProductDomain.makeup, price_segment=PriceSegment.mid, price_value=1000, why='ok', vector_score=0.1, rule_score=0.2, final_score=0.3,
    )
    text = (
        'Я бы оставил Soft Blur Foundation как основу, потому что он сразу собирает тон и делает лицо чище по впечатлению. '
        'Если хочется чуть больше свежести, следом можно добавить лёгкий консилер — и на этом остановиться.'
    )
    assert validate_response_quality(text, [item]) is True


def test_validate_response_quality_rejects_old_three_block_template() -> None:
    item = RecommendationItem(
        sku='1', title='Soft Blur Foundation LIGHT_NEUTRAL', brand='Shade Atelier', category=ProductCategory.foundation,
        domain=ProductDomain.makeup, price_segment=PriceSegment.mid, price_value=1000, why='ok', vector_score=0.1, rule_score=0.2, final_score=0.3,
    )
    text = (
        'Что это даст образу: Лицо станет лучше.\n'
        'Что я беру в набор: Беру Soft Blur Foundation.\n'
        'Что делаем дальше: Если хочешь, я продолжу.'
    )
    assert validate_response_quality(text, [item]) is False
