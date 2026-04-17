from __future__ import annotations

import re

from .catalog import load_catalog
from .merchandising import bundle_story
from .models import DialogIntent, IntentAction, IntentDomain, ProductCategory, ProductDomain, RecommendationItem, RecommendationPlan, SessionState, SkinProfile
from .retrieval import retrieve_products

CATEGORY_LABELS = {
    ProductCategory.cleanser: "очищение",
    ProductCategory.serum: "сыворотка",
    ProductCategory.moisturizer: "крем",
    ProductCategory.spf: "SPF",
    ProductCategory.toner: "тонер",
    ProductCategory.mask: "маска",
    ProductCategory.spot_treatment: "точечный уход",
    ProductCategory.foundation: "тон",
    ProductCategory.skin_tint: "скин тинт",
    ProductCategory.concealer: "консилер",
    ProductCategory.powder: "пудра",
    ProductCategory.lipstick: "помада",
    ProductCategory.lip_tint: "тинт для губ",
    ProductCategory.lip_gloss: "блеск для губ",
    ProductCategory.lip_liner: "карандаш для губ",
    ProductCategory.lip_balm: "бальзам для губ",
    ProductCategory.mascara: "тушь",
    ProductCategory.eyeliner: "подводка",
    ProductCategory.eyeshadow_palette: "палетка теней",
    ProductCategory.brow_pencil: "карандаш для бровей",
    ProductCategory.brow_gel: "гель для бровей",
    ProductCategory.blush: "румяна",
    ProductCategory.bronzer: "бронзер",
    ProductCategory.highlighter: "хайлайтер",
    ProductCategory.contour: "контур",
    ProductCategory.primer: "праймер",
    ProductCategory.setting_spray: "фиксирующий спрей",
    ProductCategory.makeup_remover: "снятие макияжа",
}
CONCERN_LABELS = {
    "redness": "покраснение",
    "breakouts": "высыпания",
    "dryness": "сухость",
    "oiliness": "жирность",
    "maintenance": "поддержание кожи",
    "tone_match": "подбор оттенка",
    "under_eye": "зона под глазами",
}
SKIN_TYPE_LABELS = {
    "dry": "сухой",
    "oily": "жирной",
    "combination": "комбинированной",
    "normal": "нормальной",
    "sensitive": "чувствительной",
}
COVERAGE_LABELS = {
    "sheer": "очень легкое покрытие",
    "light": "легкое покрытие",
    "medium": "среднее покрытие",
    "full": "плотное покрытие",
}
FINISH_LABELS = {
    "radiant": "сияющий финиш",
    "matte": "матовый финиш",
    "natural": "естественный финиш",
    "satin": "сатиновый финиш",
}
COLOR_LABELS = {
    "nude": "нюдовой гамме",
    "pink": "розовой гамме",
    "rose": "розово-нюдовой гамме",
    "coral": "коралловой гамме",
    "berry": "ягодной гамме",
    "red": "красной гамме",
    "brown": "коричневой гамме",
    "peach": "персиковой гамме",
    "bronze": "бронзовой гамме",
    "plum": "сливовой гамме",
    "neutral": "нейтральной гамме",
}


TONE_CTA = {
    "soft_luxury": "Если хочешь, я сделаю версию ещё тише и дороже: меньше шума, больше ощущения ухоженного лица без слоя косметики.",
    "sexy": "Если хочешь, я сразу уведу это в более цепляющий сценарий: сильнее взгляд, чётче контур и заметнее впечатление вечером.",
    "clean_girl": "Если хочешь, я облегчу набор ещё сильнее, чтобы осталось ощущение «своя кожа, только заметно лучше».",
    "glam": "Если хочешь, я дожму это в более вечерний вариант, который увереннее держится в свете, на фото и вживую.",
    "default": "Если хочешь, я за один ход соберу один из трёх вариантов: тише и натуральнее, заметнее и вечернее или легче по бюджету — без потери впечатления.",
}

SHORT_REASON_TEMPLATES = {
    ProductCategory.cleanser: "сразу убирает лишний визуальный шум и даёт коже более чистый, спокойный старт",
    ProductCategory.serum: "делает кожу более ровной, напитанной и ухоженной на вид",
    ProductCategory.moisturizer: "смягчает рельеф и даёт коже более спокойный, дорогой финиш",
    ProductCategory.spf: "закрывает дневной слой так, чтобы лицо выглядело аккуратно и без перегруза",
    ProductCategory.toner: "успокаивает кожу и подготавливает её так, чтобы остальной уход лёг чище",
    ProductCategory.mask: "быстро возвращает коже живость и комфорт, когда нужен заметный refresh-эффект",
    ProductCategory.spot_treatment: "точечно убирает лишние акценты, не перегружая всё лицо",
    ProductCategory.makeup_remover: "снимает макияж мягко, чтобы кожа не выглядела уставшей и раздражённой",
    ProductCategory.primer: "сразу делает тон визуально ровнее и аккуратнее",
    ProductCategory.foundation: "сразу делает тон более дорогим, ровным и собранным",
    ProductCategory.skin_tint: "освежает лицо без ощущения тяжёлого слоя",
    ProductCategory.concealer: "быстро собирает зону под глазами и убирает лишнюю усталость с лица",
    ProductCategory.powder: "держит финиш чище и аккуратнее в течение дня",
    ProductCategory.blush: "возвращает лицу живость, свежесть и лёгкий комплиментарный цвет",
    ProductCategory.mascara: "раскрывает взгляд за пару движений и делает лицо выразительнее",
    ProductCategory.lipstick: "добавляет образу завершённость, статус и понятное настроение",
    ProductCategory.lip_tint: "делает лицо свежее и моложе по ощущению без тяжёлой помады",
    ProductCategory.lip_gloss: "добавляет образу сочность и более притягательный финиш",
    ProductCategory.eyeshadow_palette: "позволяет быстро усилить образ и сделать его вечернее",
    ProductCategory.eyeliner: "добавляет взгляду остроту и более собранный характер",
    ProductCategory.brow_gel: "собирает лицо и делает весь макияж заметно аккуратнее",
    ProductCategory.highlighter: "добавляет коже дорогого свечения без эффекта жирного блеска",
    ProductCategory.setting_spray: "помогает образу дольше выглядеть свежо и дорого на расстоянии",
}

CONCERN_EFFECT_TEMPLATES = {
    "redness": "кожа выглядит спокойнее и чище",
    "breakouts": "рельеф читается мягче и аккуратнее",
    "dryness": "кожа выглядит более гладкой и напитанной",
    "oiliness": "Т-зона выглядит собраннее и чище",
    "maintenance": "лицо выглядит ухоженнее и стабильнее",
    "tone_match": "тон лица выглядит ровнее и дороже",
    "under_eye": "взгляд выглядит более отдохнувшим",
}

STYLE_EFFECT_ENDINGS = {
    "soft_luxury": "В итоге образ ощущается тише, дороже и очень ухоженно даже вблизи.",
    "sexy": "В итоге лицо цепляет сильнее и держит внимание заметно дольше.",
    "clean_girl": "В итоге всё выглядит чисто, легко и будто это просто ваша хорошая кожа.",
    "glam": "В итоге образ лучше работает на фото, в вечернем свете и в живом общении.",
    "default": "В итоге лицо выглядит собранно, свежо и заметно дороже без перегруза.",
}

OLD_SALES_BLOCK_LABELS = (
    "Что это даст образу",
    "Что я беру в набор",
    "Что делаем дальше",
)


def humanize_shade_token(value: str) -> str:
    parts = value.replace("-", "_").split("_")
    mapping = {
        "fair": "очень светлый",
        "light": "светлый",
        "medium": "средний",
        "tan": "загорелый",
        "deep": "глубокий",
        "neutral": "нейтральный",
        "warm": "тёплый",
        "cool": "холодный",
        "olive": "оливковый",
        "rose": "розовый",
        "nude": "нюдовый",
        "coral": "коралловый",
        "plum": "сливовый",
        "bronze": "бронзовый",
        "pink": "розовый",
        "champagne": "шампань",
        "taupe": "тауповый",
        "peach": "персиковый",
    }
    human = [mapping.get(part.lower(), part.lower()) for part in parts if part]
    return " ".join(human).strip()


def pretty_product_title(title: str) -> str:
    match = re.search(r"\b([A-Z]+(?:_[A-Z]+)+)\b", title)
    if not match:
        return title
    shade = match.group(1)
    human_shade = humanize_shade_token(shade)
    return title.replace(shade, human_shade)


def sanitize_agent_text(text: str) -> str:
    cleaned = text.replace("**", "").replace("__", "")
    cleaned = re.sub(r"(?m)^\s*#{1,6}\s*", "", cleaned)
    cleaned = re.sub(r"`+", "", cleaned)
    cleaned = re.sub(r"^(?:привет|здравствуй|здравствуйте|рада тебя видеть снова|рада тебя видеть|рада, что ты заглянула|рада, что ты вернулась)[!, .\s]*", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"^\s+", "", cleaned)
    return cleaned.strip()


def _normalize_sales_blocks(text: str) -> str:
    lines = [line.strip() for line in str(text or "").splitlines() if line.strip()]
    if not lines:
        return text

    normalized: dict[str, str] = {}
    for line in lines:
        plain = re.sub(r"^\s*(?:[-*]\s*|\d+[.)]\s*)", "", line).strip()
        match = re.match(rf"^({'|'.join(re.escape(label) for label in OLD_SALES_BLOCK_LABELS)})\s*[:\-—]\s*(.+)$", plain)
        if match:
            normalized[match.group(1)] = match.group(2).strip()

    if len(normalized) >= 2:
        ordered = [f"{label}: {normalized[label]}" for label in OLD_SALES_BLOCK_LABELS if normalized.get(label)]
        return "\n".join(ordered)

    return text


def _style_mode(session_or_profile) -> str:
    styles = []
    if hasattr(session_or_profile, 'makeup_profile'):
        styles = getattr(session_or_profile.makeup_profile, 'preferred_styles', []) or []
    elif hasattr(session_or_profile, 'skin_profile'):
        styles = getattr(session_or_profile.skin_profile.makeup_profile, 'preferred_styles', []) or []
    values = [style.value if hasattr(style, 'value') else str(style) for style in styles]
    if 'sexy' in values:
        return 'sexy'
    if 'soft_luxury' in values:
        return 'soft_luxury'
    if 'glam' in values or 'evening' in values:
        return 'glam'
    if 'clean_girl' in values:
        return 'clean_girl'
    return 'default'


def _opening_line(profile) -> str:
    mode = _style_mode(profile)
    if mode == 'soft_luxury':
        return 'Тон выглядит чище, кожа — спокойнее, а всё лицо собирается в тихий дорогой вид без лишнего слоя.'
    if mode == 'sexy':
        return 'Черты становятся выразительнее, взгляд цепляет сильнее, а лицо в целом выглядит заметно собраннее.'
    if mode == 'glam':
        return 'Лицо станет ярче и контрастнее: взгляд сильнее, тон чище, а результат увереннее держится в свете и на фото.'
    if mode == 'clean_girl':
        return 'Кожа выглядит как своя, только лучше: ровнее, свежее и светлее, без ощущения плотного слоя.'
    return 'Лицо выглядит ровнее, свежее и собраннее; вблизи кожа кажется ухоженной, а на фото результат читается чище и дороже.'


def _profile_for_effects(session_or_profile: SessionState | SkinProfile) -> SkinProfile:
    return session_or_profile.skin_profile if hasattr(session_or_profile, "skin_profile") else session_or_profile


def _concern_effects(session_or_profile: SessionState | SkinProfile) -> list[str]:
    profile = _profile_for_effects(session_or_profile)
    concerns = [*getattr(profile, "primary_concerns", []), *getattr(profile, "secondary_concerns", [])]
    values: list[str] = []
    for concern in concerns:
        key = concern.value if hasattr(concern, "value") else str(concern)
        phrase = CONCERN_EFFECT_TEMPLATES.get(key)
        if phrase and phrase not in values:
            values.append(phrase)
    return values[:2]


def _default_effect_line(session_or_profile: SessionState | SkinProfile) -> str:
    details = _concern_effects(session_or_profile)
    ending = STYLE_EFFECT_ENDINGS.get(_style_mode(session_or_profile), STYLE_EFFECT_ENDINGS["default"])
    if len(details) >= 2:
        if details[0].startswith("кожа выглядит ") and details[1].startswith("кожа выглядит "):
            first = details[0].replace("кожа выглядит ", "", 1)
            second = details[1].replace("кожа выглядит ", "", 1)
            return f"Кожа выглядит {first}, а по текстуре — {second}. {ending}"
        return f"{details[0].capitalize()}, а {details[1]}. {ending}"
    if details:
        return f"{details[0].capitalize()}. {ending}"
    return _opening_line(session_or_profile)


def _sales_effect_line(session_or_profile, plan: RecommendationPlan | None = None, intent_name: str | None = None) -> str:
    intent_map = {
        "cheaper_alternative": "Сохраняем тот же собранный эффект, но режем всё лишнее: лицо всё равно выглядит чище, ровнее и дороже, просто без переплаты за второстепенные шаги.",
        "premium_alternative": "Финиш станет мягче, чище и статуснее. Это уже не просто аккуратный результат, а ощущение действительно дорогой, очень продуманной сборки.",
        "transform_radiant": "Кожа будет выглядеть живее и светлее по впечатлению: лицо сразу кажется бодрее, а тон — свежее и комплиментарнее.",
        "transform_matte": "Финиш станет чище и собраннее, поэтому лицо будет выглядеть аккуратно не только сразу после нанесения, но и позже, когда обычно всё начинает плыть.",
        "transform_natural": "Эффект будет такой, будто у тебя просто хороший тон кожи и более отдохнувшее лицо. Всё выглядит легче, чище и заметно дороже вблизи.",
        "transform_evening": "Черты станут заметнее, взгляд — глубже, а лицо лучше держит внимание в вечернем свете и на фото. Это уже не просто аккуратно, а по-настоящему выразительно.",
        "halal_filter": "Сохраняем аккуратный, цельный результат, но делаем набор строже по составу. Визуально лицо всё равно выглядит чисто, спокойно и собранно.",
        "simplify_routine": "Убираем лишнее и оставляем только шаги, которые сразу читаются на лице: чище тон, спокойнее кожа, свежее общее впечатление.",
        "replace_product": "Меняем слабое место на шаг, который даст более современный и выигрышный результат. Лицо сразу выглядит увереннее и лучше собрано.",
        "exclude_ingredient": "Сохраняем видимый эффект, но делаем набор комфортнее по составу. То есть кожа остаётся спокойной, а лицо — всё так же собранным и выигрышным.",
    }
    if intent_name in intent_map:
        return intent_map[intent_name]
    if intent_name == "general_advice":
        domain = getattr(session_or_profile.current_plan, "primary_domain", None) if hasattr(session_or_profile, "current_plan") else None
        if domain == ProductDomain.makeup:
            return "Лицо будет выглядеть ровнее и дороже по впечатлению: вблизи кожа кажется аккуратнее, а на фото всё читается чище и собраннее."
    return _default_effect_line(session_or_profile)


def _product_phrase(item: RecommendationItem, lead: str) -> str:
    title = pretty_product_title(item.title)
    reason = SHORT_REASON_TEMPLATES.get(item.category, "усиливает образ и делает его аккуратнее без лишнего шума")
    return f"{lead} {title}: он {reason}."


def _bundle_line(recommendations: list[RecommendationItem]) -> str:
    hero, support = bundle_story(recommendations[:3])
    phrases: list[str] = []
    if hero:
        phrases.append(_product_phrase(hero, "Главным шагом ставлю"))
    support_leads = ("Следом добавляю", "И закрываю набор")
    for index, item in enumerate(support[:2]):
        lead = support_leads[index] if index < len(support_leads) else "Дальше добавляю"
        phrases.append(_product_phrase(item, lead))
    if not phrases and recommendations:
        phrases.append(_product_phrase(recommendations[0], "Главным шагом ставлю"))
    return " ".join(phrases)


def _conversation_opening(session: SessionState | SkinProfile, intent: DialogIntent | None = None) -> str:
    intent_name = intent.intent if intent else ""
    by_intent = {
        "transform_evening": "Если увести это в вечер, лицо станет заметнее: взгляд глубже, тон чище, и всё вместе сильнее держит внимание.",
        "transform_natural": "Если сделать это натуральнее, эффект будет ближе к «своя кожа, только заметно лучше» — без чувства, что на лице много продукта.",
        "transform_radiant": "Если увести это в более сияющий вариант, лицо будет выглядеть живее и бодрее, а кожа — светлее по впечатлению.",
        "cheaper_alternative": "Здесь можно спокойно облегчить чек и не убить впечатление: лицо всё равно будет выглядеть собранно и аккуратно.",
        "premium_alternative": "Если собрать более дорогую версию, выигрыш будет не в количестве шагов, а в том, насколько чище и статуснее выглядит результат.",
    }
    if intent_name in by_intent:
        return by_intent[intent_name]
    return _sales_effect_line(session, getattr(session, "current_plan", None), intent_name)


def _conversation_logic_line(recommendations: list[RecommendationItem]) -> str:
    if not recommendations:
        return "Сейчас я бы не усложнял и сначала уточнил, в какую сторону ты хочешь увести результат."
    hero = recommendations[0]
    title = pretty_product_title(hero.title)
    reason = SHORT_REASON_TEMPLATES.get(hero.category, "даёт более понятный и собранный результат")
    if len(recommendations) == 1:
        return f"Я бы начал с {title}, потому что он {reason} и уже сам по себе задаёт правильное направление."
    support = recommendations[1]
    support_title = pretty_product_title(support.title)
    support_reason = SHORT_REASON_TEMPLATES.get(support.category, "докручивает результат и убирает ощущение недосборки")
    if len(recommendations) >= 3:
        third = recommendations[2]
        third_title = pretty_product_title(third.title)
        third_reason = SHORT_REASON_TEMPLATES.get(third.category, "закрывает последний важный шаг и собирает результат до конца")
        return (
            f"Я бы начал с {title}, потому что он {reason}. "
            f"Следом оставил бы {support_title}, чтобы он {support_reason}. "
            f"И третьим шагом добавил бы {third_title}, потому что он {third_reason}."
        )
    return f"Я бы начал с {title}, потому что он {reason}. Следом добавил бы {support_title}, чтобы он {support_reason}."


def _initial_intro(profile: SkinProfile, recommendations: list[RecommendationItem], plan: RecommendationPlan) -> str:
    primary_domain = getattr(plan, "primary_domain", None)
    if primary_domain is None and recommendations:
        primary_domain = recommendations[0].domain
    if primary_domain == ProductDomain.skincare:
        if len(recommendations) >= 3:
            return "Я собрал спокойный базовый уход без лишнего: мягко очистить кожу, выровнять ощущение по текстуре и закрыть день нормальной защитой."
        return "Я собрал спокойную базу без лишних шагов, чтобы кожа выглядела ровнее и ухоженнее уже с первого цикла."
    if primary_domain == ProductDomain.makeup:
        return "Я собрал понятный макияжный старт без перегруза, чтобы лицо выглядело ровнее, свежее и сразу более собранно."
    return _sales_effect_line(profile, plan)


def _next_step_line(session: SessionState | SkinProfile, intent: DialogIntent | None = None) -> str:
    intent_name = intent.intent if intent else ""
    action_map = {
        "cheaper_alternative": "Если хочешь, я следующим сообщением оставлю только 2 самых выгодных шага, чтобы чек стал легче, а лицо всё равно выглядело собранно и дорого.",
        "premium_alternative": "Если хочешь, я сейчас соберу более статусную версию — ту, где результат сразу читается как более дорогой и взрослый.",
        "transform_radiant": "Если хочешь, я усилю свечение ещё на полшага или соберу более заметную версию, которая сильнее работает вживую и на фото.",
        "transform_matte": "Если хочешь, я сделаю финиш ещё чище и спокойнее или переведу это в очень удобный daily-вариант без лишнего блеска.",
        "transform_natural": "Если хочешь, я ещё сильнее упрощу набор и доведу его до ощущения «своя кожа, только заметно лучше».",
        "transform_evening": "Если хочешь, я сразу добавлю более вечерний акцент — на тон, губы или взгляд, чтобы лицо стало ещё заметнее и сильнее держало внимание.",
        "compare_products": "Если хочешь, я сразу зафиксирую победителя и дособеру к нему всё остальное так, чтобы результат был цельным, а не случайным.",
        "explain_product": "Если хочешь, я прямо сейчас подберу к нему ещё 1-2 шага, чтобы эффект на лице стал понятнее и ощутимо сильнее.",
        "halal_filter": "Если хочешь, я сейчас оставлю только halal-friendly основу и уберу всё спорное, не просаживая визуальный результат.",
    }
    if intent_name in action_map:
        return action_map[intent_name]
    mode = _style_mode(session)
    return TONE_CTA.get(mode, TONE_CTA["default"])


def _join_reply_parts(*parts: str) -> str:
    return "\n\n".join(part.strip() for part in parts if part and part.strip())


def compose_smalltalk_response(session: SessionState, recommendations: list[RecommendationItem], message: str) -> str:
    normalized = message.lower()
    if any(token in normalized for token in ["привет", "здар", "здрав"]):
        if recommendations:
            hero = pretty_product_title(recommendations[0].title)
            return f"Привет. Я уже вижу текущий набор и могу быстро с ним помочь: сейчас в центре у нас {hero}. Куда хочешь двинуть результат — сделать его спокойнее, заметнее или просто понятнее по шагам?"
        return "Привет. Давай быстро соберём это нормально. Скажи, ты хочешь сейчас уход, макияж или вариант под конкретный случай?"
    if any(token in normalized for token in ["спасибо", "благодар"]):
        return "Пожалуйста. Если хочешь, я не буду грузить лишним и просто предложу следующий самый удачный шаг."
    return "Я с тобой. Скажи коротко, какой результат хочешь получить, и я отвечу без шаблонов — просто как нормальный консультант."


def compose_initial_response(profile, recommendations: list[RecommendationItem], plan: RecommendationPlan) -> str:
    return _join_reply_parts(
        _initial_intro(profile, recommendations, plan),
        _conversation_logic_line(recommendations),
        _next_step_line(profile),
    )


def build_reply_prompt(session: SessionState, intent: DialogIntent, recommendations: list[RecommendationItem], message: str) -> str:
    rec_lines = "\n".join(f"- {pretty_product_title(item.title)} | brand={item.brand} | category={item.category.value} | price={item.price_value} | why={item.why}" for item in recommendations[:3])
    mode = _style_mode(session)
    return f"""
Ты — очень сильный beauty-консультант Golden Apple.
Отвечай по-русски.
Текущий retail-tone mode: {mode}.
Ты говоришь как живой консультант в магазине: спокойно, умно, по-человечески и без шаблонной роботской структуры.
Ты не звучишь как врач, нейтральный бот или рекламный баннер.
Ты пишешь интересно и живо, но без рекламной жижи.
Ответ должен быть таким, чтобы его хотелось дочитать и чтобы хотелось написать ещё; после него хочется продолжить разговор, а не закрыть чат.
КРИТИЧЕСКИЕ ОГРАНИЧЕНИЯ:
- НЕЛЬЗЯ придумывать бренды, товары, SKU, линейки, текстуры или продукты, которых нет в списке ниже.
- Можно упоминать ТОЛЬКО продукты из блока ПОДБОРКА.
- Если в подборке 1 продукт — говори только о нём и о следующем шаге, не выдумывай дополнительные товары.
- Нельзя уводить пользователя в другой домен без фактической подборки.
- Нельзя советовать новые бренды "от себя".
ФОРМАТ ОТВЕТА:
- 2-4 коротких абзаца или 3-5 коротких предложений
- не используй жёсткий шаблон из трёх блоков
- не используй заголовки "Что это даст образу", "Что я беру в набор", "Что делаем дальше"
- максимум 2-3 продукта в тексте
- без длинных редакторских вступлений
- без сухой диагностики
- без markdown-звёздочек и заголовков
- нельзя писать пустые формулы вроде "хорошо встанет в образ", "просто подойдёт", "закрывает задачу"
- нельзя писать рекламные клише вроде "безупречно", "премиальный уход", "словно после спа", "абсолютный комфорт", "идеальное покрытие"
- нельзя давить фразами "добавьте это в корзину", "берите прямо сейчас", "вам срочно нужно"
- ответ должен звучать как живой консультант, а не как заскриптованная рамочная штука
- сначала коротко скажи, какой визуальный результат человек получит
- в ответе должен быть понятный визуальный выигрыш, а не расплывчатая оценка
- потом по-человечески объясни логику 1-2 ключевых продуктов через "потому что", "за счёт этого", "поэтому"
- закончи одним нормальным следующим шагом или вопросом, который действительно двигает разговор
- если пользователь пишет просто "привет", "ок", "спасибо" или что-то короткое бытовое — отвечай как человек, а не как продавец с подборкой
ЗАДАЧА:
- коротко продать текущую подборку
- объяснить эффект образа
- закончить мягким следующим шагом
Если запрос на compare — сравни только товары из подборки.
Если запрос на explain — объясни только товары из подборки.
Сообщение пользователя: {message}
Action={intent.action.value}; domain={intent.domain.value}; target={intent.target_category.value if intent.target_category else ''};
ПОДБОРКА:
{rec_lines}
""".strip()


def pick_label(values: list[str], labels: dict[str, str]) -> str | None:
    for value in values:
        label = labels.get(value)
        if label:
            return label
    return None


def describe_item(item: RecommendationItem, session: SessionState) -> str:
    catalog = {product.sku: product for product in load_catalog()}
    product = catalog.get(item.sku)
    if not product:
        return item.why
    bits: list[str] = []
    if product.domain == ProductDomain.makeup:
        finish = pick_label(product.finishes, FINISH_LABELS)
        color = pick_label(product.color_families, COLOR_LABELS)
        if finish:
            bits.append(finish)
        if color:
            bits.append(f"в {color}")
        if product.longwear and "longwear" in session.current_plan.preferred_tags:
            bits.append("с хорошей стойкостью")
    else:
        if "soothing" in product.tags:
            bits.append("работает мягко")
        if "non-comedogenic" in product.tags:
            bits.append("не должен перегружать кожу")
    details = ", ".join(bits[:2])
    return details or item.why


def find_item_for_category(session: SessionState, recommendations: list[RecommendationItem], category: ProductCategory) -> RecommendationItem | None:
    for item in recommendations:
        if item.category == category:
            return item
    sku = session.dialog_context.current_recommendations.get(category)
    if not sku:
        return None
    product = next((product for product in load_catalog() if product.sku == sku), None)
    if not product:
        return None
    return RecommendationItem(
        sku=product.sku,
        title=product.title,
        brand=product.brand,
        category=product.category,
        domain=product.domain,
        price_segment=product.price_segment,
        price_value=product.price_value,
        why="текущий вариант",
        vector_score=0.0,
        rule_score=0.0,
        final_score=0.0,
    )


def alternative_for_category(session: SessionState, category: ProductCategory, intent: DialogIntent) -> RecommendationItem | None:
    alt_intent = DialogIntent(
        intent="replace_product",
        action=IntentAction.replace,
        domain=intent.domain,
        target_category=category,
        target_categories=[category],
        confidence=0.4,
    )
    alt = retrieve_products(session.skin_profile, session.current_plan, session.user_preferences, session=session, intent=alt_intent)
    for item in alt:
        if item.category == category:
            return item
    return None


def compose_compare_response(session: SessionState, intent: DialogIntent, recommendations: list[RecommendationItem]) -> str:
    target_categories = intent.target_categories or ([intent.target_category] if intent.target_category else [])
    items: list[RecommendationItem] = []
    if target_categories:
        for category in target_categories:
            item = find_item_for_category(session, recommendations, category)
            if item:
                items.append(item)
    else:
        items = recommendations[:2]
    if len(target_categories) == 1:
        alt = alternative_for_category(session, target_categories[0], intent)
        if alt:
            items.append(alt)
    if len(items) < 2:
        return "Сейчас не из чего собрать честное сравнение. Скажи, что сравнить — например две помады или два варианта для глаз."
    first, second = items[:2]
    return _join_reply_parts(
        f"Если нужен более собранный и заметный результат, я бы ставил выше {pretty_product_title(first.title)}. Если хочется мягче и спокойнее по ощущению, ближе {pretty_product_title(second.title)}.",
        f"Логика тут простая: {pretty_product_title(first.title)} выглядит сильнее под текущий запрос, а {pretty_product_title(second.title)} — аккуратнее и тише.",
        "Если хочешь, я сразу выберу победителя и дособеру к нему остальное без лишних сравнений.",
    )


def compose_explain_response(session: SessionState, intent: DialogIntent, recommendations: list[RecommendationItem]) -> str:
    target = intent.target_category or (intent.target_categories[0] if intent.target_categories else None)
    focus = find_item_for_category(session, recommendations, target) if target else (recommendations[0] if recommendations else None)
    if not focus:
        return "Скажи, какой именно продукт разобрать — я коротко объясню, почему он работает в образе."
    pretty_title = pretty_product_title(focus.title)
    return _join_reply_parts(
        f"{pretty_title} здесь не для галочки. Он нужен, чтобы лицо выглядело собраннее и чище по впечатлению.",
        f"Я оставляю его в наборе, потому что по факту он {describe_item(focus, session)}.",
        "Если хочешь, я сразу подберу к нему ещё 1-2 вещи, чтобы результат сложился до конца.",
    )


def compose_followup_response(session: SessionState, intent: DialogIntent, recommendations: list[RecommendationItem], message: str) -> str:
    if intent.action == IntentAction.compare:
        return compose_compare_response(session, intent, recommendations)
    if intent.action == IntentAction.explain:
        return compose_explain_response(session, intent, recommendations)
    visible_items: list[RecommendationItem] = []
    for item in recommendations[:3]:
        if intent.target_category and intent.action in {IntentAction.replace, IntentAction.cheaper} and item.category != intent.target_category:
            continue
        visible_items.append(item)
    if not visible_items:
        visible_items = recommendations[:3]
    return _join_reply_parts(
        _conversation_opening(session, intent),
        _conversation_logic_line(visible_items),
        _next_step_line(session, intent),
    )
