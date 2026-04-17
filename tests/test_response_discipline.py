from app.models import ConcernType, DialogIntent, IntentAction, IntentDomain, ProductCategory, ProductDomain, PriceSegment, RecommendationItem, RecommendationPlan, SessionState, SkinProfile, SkinType, PhotoAnalysisResult, RecommendationPlan, UserContext
from app.response_service import build_reply_prompt, compose_followup_response, compose_initial_response, compose_smalltalk_response, sanitize_agent_text


def make_item(category: ProductCategory, title: str, domain: ProductDomain = ProductDomain.makeup) -> RecommendationItem:
    return RecommendationItem(
        sku=title,
        title=title,
        brand='Brand',
        category=category,
        domain=domain,
        price_segment=PriceSegment.mid,
        price_value=1000,
        why='ok',
        vector_score=0.5,
        rule_score=0.6,
        final_score=0.7,
    )


def test_followup_response_stays_grounded_to_visible_items() -> None:
    session = SessionState(
        session_id='1',
        photo_analysis=PhotoAnalysisResult(),
        skin_profile=SkinProfile(skin_type=SkinType.normal, primary_concerns=[], confidence_overall=0.8),
        current_plan=RecommendationPlan(required_categories=[ProductCategory.foundation, ProductCategory.concealer]),
        user_preferences=UserContext(),
    )
    recs = [make_item(ProductCategory.foundation, 'Perfect Match Serum Foundation LIGHT_NEUTRAL'), make_item(ProductCategory.concealer, 'Air Touch Concealer LIGHT_NEUTRAL')]
    text = compose_followup_response(session, DialogIntent(intent='general_advice', action=IntentAction.recommend, domain=IntentDomain.makeup), recs, 'сделай это лучше')
    assert 'Perfect Match' in text
    assert 'Air Touch' in text
    assert 'Kiehl' not in text


def test_initial_response_reads_like_a_clear_first_message() -> None:
    profile = SkinProfile(
        skin_type=SkinType.sensitive,
        primary_concerns=[ConcernType.redness, ConcernType.dryness],
        confidence_overall=0.8,
    )
    plan = RecommendationPlan(required_categories=[ProductCategory.cleanser, ProductCategory.moisturizer, ProductCategory.spf])
    recs = [
        make_item(ProductCategory.cleanser, 'Barrier Cloud Cream Cleanser', ProductDomain.skincare),
        make_item(ProductCategory.moisturizer, 'Skin Veil Balancing Emulsion', ProductDomain.skincare),
        make_item(ProductCategory.spf, 'Barrier Shield SPF 50 Cream', ProductDomain.skincare),
    ]
    text = compose_initial_response(profile, recs, plan)
    assert 'Я собрал спокойный базовый уход без лишнего' in text
    assert 'Я бы начал с Barrier Cloud Cream Cleanser' in text
    assert 'И третьим шагом добавил бы Barrier Shield SPF 50 Cream' in text


def test_followup_response_uses_conversational_structure() -> None:
    session = SessionState(
        session_id='2',
        photo_analysis=PhotoAnalysisResult(),
        skin_profile=SkinProfile(skin_type=SkinType.normal, primary_concerns=[], confidence_overall=0.8),
        current_plan=RecommendationPlan(required_categories=[ProductCategory.foundation, ProductCategory.concealer]),
        user_preferences=UserContext(),
    )
    recs = [make_item(ProductCategory.foundation, 'Perfect Match Serum Foundation LIGHT_NEUTRAL'), make_item(ProductCategory.concealer, 'Air Touch Concealer LIGHT_NEUTRAL')]
    text = compose_followup_response(session, DialogIntent(intent='transform_natural', action=IntentAction.refine, domain=IntentDomain.makeup), recs, 'сделай натуральнее')
    assert 'Что это даст образу:' not in text
    assert 'Что я беру в набор:' not in text
    assert 'Если хочешь' in text
    assert 'потому что' in text or 'логика' in text.lower()


def test_followup_response_bundle_copy_sounds_natural() -> None:
    session = SessionState(
        session_id='4',
        photo_analysis=PhotoAnalysisResult(),
        skin_profile=SkinProfile(skin_type=SkinType.normal, primary_concerns=[], confidence_overall=0.8),
        current_plan=RecommendationPlan(required_categories=[ProductCategory.foundation, ProductCategory.concealer]),
        user_preferences=UserContext(),
    )
    recs = [make_item(ProductCategory.foundation, 'Perfect Match Serum Foundation LIGHT_NEUTRAL')]
    text = compose_followup_response(session, DialogIntent(intent='general_advice', action=IntentAction.recommend, domain=IntentDomain.makeup), recs, 'что лучше взять')
    assert 'Perfect Match Serum Foundation' in text
    assert 'делает тон более дорогим' in text
    assert 'потому что' in text
    assert 'хорошо встанет в образ' not in text


def test_followup_response_for_skincare_avoids_generic_copy() -> None:
    session = SessionState(
        session_id='5',
        photo_analysis=PhotoAnalysisResult(),
        skin_profile=SkinProfile(
            skin_type=SkinType.sensitive,
            primary_concerns=[ConcernType.redness, ConcernType.dryness],
            confidence_overall=0.8,
        ),
        current_plan=RecommendationPlan(required_categories=[ProductCategory.cleanser, ProductCategory.moisturizer, ProductCategory.spf]),
        user_preferences=UserContext(),
    )
    recs = [
        make_item(ProductCategory.cleanser, 'Barrier Cloud Cream Cleanser', ProductDomain.skincare),
        make_item(ProductCategory.moisturizer, 'Skin Veil Balancing Emulsion', ProductDomain.skincare),
        make_item(ProductCategory.spf, 'Barrier Shield SPF 50 Cream', ProductDomain.skincare),
    ]
    text = compose_followup_response(session, DialogIntent(intent='general_advice', action=IntentAction.recommend, domain=IntentDomain.skincare), recs, 'собери спокойный уход')
    assert 'Кожа выглядит спокойнее и чище' in text
    assert 'Barrier Cloud Cream Cleanser' in text
    assert 'Skin Veil Balancing Emulsion' in text
    assert 'потому что' in text or 'логика' in text.lower()
    assert 'хорошо встанет в образ' not in text


def test_build_reply_prompt_requests_conversational_human_reply() -> None:
    session = SessionState(
        session_id='3',
        photo_analysis=PhotoAnalysisResult(),
        skin_profile=SkinProfile(skin_type=SkinType.normal, primary_concerns=[], confidence_overall=0.8),
        current_plan=RecommendationPlan(required_categories=[ProductCategory.foundation]),
        user_preferences=UserContext(),
    )
    prompt = build_reply_prompt(
        session,
        DialogIntent(intent='cheaper_alternative', action=IntentAction.cheaper, domain=IntentDomain.makeup),
        [make_item(ProductCategory.foundation, 'Perfect Match Serum Foundation LIGHT_NEUTRAL')],
        'сделай дешевле',
    )
    assert 'не используй жёсткий шаблон из трёх блоков' in prompt
    assert 'как живой консультант' in prompt
    assert 'нельзя писать рекламные клише' in prompt
    assert 'нельзя писать пустые формулы' in prompt


def test_sanitize_agent_text_keeps_plain_text_without_markup_noise() -> None:
    raw = "**привет**\n\nВот что я бы оставил сейчас."
    cleaned = sanitize_agent_text(raw)
    assert cleaned == "Вот что я бы оставил сейчас."


def test_followup_response_evening_feels_more_specific_and_enticing() -> None:
    session = SessionState(
        session_id='6',
        photo_analysis=PhotoAnalysisResult(),
        skin_profile=SkinProfile(skin_type=SkinType.normal, primary_concerns=[], confidence_overall=0.8),
        current_plan=RecommendationPlan(required_categories=[ProductCategory.foundation, ProductCategory.mascara]),
        user_preferences=UserContext(),
    )
    recs = [
        make_item(ProductCategory.foundation, 'Soft Blur Foundation LIGHT_NEUTRAL'),
        make_item(ProductCategory.mascara, 'Lift Lash Mascara BLACK'),
    ]
    text = compose_followup_response(session, DialogIntent(intent='transform_evening', action=IntentAction.refine, domain=IntentDomain.makeup), recs, 'сделай на вечер')
    assert 'взгляд' in text.lower()
    assert 'внимание' in text.lower() or 'в свете' in text.lower() or 'на фото' in text.lower()
    assert 'выразительн' in text.lower() or 'заметн' in text.lower()
    assert 'хорошо встанет в образ' not in text


def test_build_reply_prompt_requests_interesting_specific_copy() -> None:
    session = SessionState(
        session_id='7',
        photo_analysis=PhotoAnalysisResult(),
        skin_profile=SkinProfile(skin_type=SkinType.normal, primary_concerns=[], confidence_overall=0.8),
        current_plan=RecommendationPlan(required_categories=[ProductCategory.foundation]),
        user_preferences=UserContext(),
    )
    prompt = build_reply_prompt(
        session,
        DialogIntent(intent='transform_evening', action=IntentAction.refine, domain=IntentDomain.makeup),
        [make_item(ProductCategory.foundation, 'Soft Blur Foundation LIGHT_NEUTRAL')],
        'сделай на вечер',
    )
    assert 'интересно и живо' in prompt
    assert 'без рекламной жижи' in prompt
    assert 'не используй жёсткий шаблон из трёх блоков' in prompt


def test_followup_response_general_advice_feels_more_alluring_than_neutral() -> None:
    session = SessionState(
        session_id='8',
        photo_analysis=PhotoAnalysisResult(),
        skin_profile=SkinProfile(skin_type=SkinType.normal, primary_concerns=[], confidence_overall=0.8),
        current_plan=RecommendationPlan(required_categories=[ProductCategory.foundation, ProductCategory.concealer]),
        user_preferences=UserContext(),
    )
    recs = [
        make_item(ProductCategory.foundation, 'Soft Blur Foundation LIGHT_NEUTRAL'),
        make_item(ProductCategory.concealer, 'Air Touch Concealer LIGHT_NEUTRAL'),
    ]
    text = compose_followup_response(session, DialogIntent(intent='general_advice', action=IntentAction.recommend, domain=IntentDomain.makeup), recs, 'собери мне вариант')
    lower = text.lower()
    assert 'вблизи' in lower or 'на фото' in lower or 'взгляд' in lower
    assert 'держит внимание' in lower or 'цепля' in lower or 'комплимент' in lower or 'собранн' in lower


def test_build_reply_prompt_demands_richer_luxury_retail_voice() -> None:
    session = SessionState(
        session_id='9',
        photo_analysis=PhotoAnalysisResult(),
        skin_profile=SkinProfile(skin_type=SkinType.normal, primary_concerns=[], confidence_overall=0.8),
        current_plan=RecommendationPlan(required_categories=[ProductCategory.foundation]),
        user_preferences=UserContext(),
    )
    prompt = build_reply_prompt(
        session,
        DialogIntent(intent='general_advice', action=IntentAction.recommend, domain=IntentDomain.makeup),
        [make_item(ProductCategory.foundation, 'Soft Blur Foundation LIGHT_NEUTRAL')],
        'что посоветуешь',
    )
    assert 'хочется продолжить разговор' in prompt
    assert 'визуальный выигрыш' in prompt or 'что именно визуально выигрывает' in prompt


def test_smalltalk_response_reads_like_a_person_not_a_template() -> None:
    session = SessionState(
        session_id='10',
        photo_analysis=PhotoAnalysisResult(),
        skin_profile=SkinProfile(skin_type=SkinType.normal, primary_concerns=[], confidence_overall=0.8),
        current_plan=RecommendationPlan(required_categories=[ProductCategory.cleanser, ProductCategory.moisturizer]),
        user_preferences=UserContext(),
    )
    recs = [
        make_item(ProductCategory.cleanser, 'Barrier Cloud Cream Cleanser', ProductDomain.skincare),
        make_item(ProductCategory.moisturizer, 'Skin Veil Balancing Emulsion', ProductDomain.skincare),
    ]
    text = compose_smalltalk_response(session, recs, 'привет')
    lower = text.lower()
    assert 'привет' in lower
    assert ('куда' in lower or 'что' in lower) and '?' in text
    assert 'что это даст образу' not in lower


def test_followup_response_is_conversational_not_three_rigid_blocks() -> None:
    session = SessionState(
        session_id='11',
        photo_analysis=PhotoAnalysisResult(),
        skin_profile=SkinProfile(skin_type=SkinType.normal, primary_concerns=[], confidence_overall=0.8),
        current_plan=RecommendationPlan(required_categories=[ProductCategory.foundation, ProductCategory.concealer]),
        user_preferences=UserContext(),
    )
    recs = [
        make_item(ProductCategory.foundation, 'Soft Blur Foundation LIGHT_NEUTRAL'),
        make_item(ProductCategory.concealer, 'Air Touch Concealer LIGHT_NEUTRAL'),
    ]
    text = compose_followup_response(session, DialogIntent(intent='general_advice', action=IntentAction.recommend, domain=IntentDomain.makeup), recs, 'что лучше взять')
    lower = text.lower()
    assert 'что это даст образу:' not in lower
    assert 'что я беру в набор:' not in lower
    assert 'что делаем дальше:' not in lower
    assert 'потому что' in lower or 'логика простая' in lower


def test_build_reply_prompt_requests_conversational_human_reply() -> None:
    session = SessionState(
        session_id='12',
        photo_analysis=PhotoAnalysisResult(),
        skin_profile=SkinProfile(skin_type=SkinType.normal, primary_concerns=[], confidence_overall=0.8),
        current_plan=RecommendationPlan(required_categories=[ProductCategory.foundation]),
        user_preferences=UserContext(),
    )
    prompt = build_reply_prompt(
        session,
        DialogIntent(intent='general_advice', action=IntentAction.recommend, domain=IntentDomain.makeup),
        [make_item(ProductCategory.foundation, 'Soft Blur Foundation LIGHT_NEUTRAL')],
        'что посоветуешь',
    )
    assert 'не используй жёсткий шаблон из трёх блоков' in prompt
    assert 'как живой консультант' in prompt
