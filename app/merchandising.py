from __future__ import annotations

from .models import ProductCategory, RecommendationItem, RecommendationPlan, UserContext

HERO_PRIORITY = {
    ProductCategory.cleanser: 100,
    ProductCategory.serum: 98,
    ProductCategory.moisturizer: 96,
    ProductCategory.spf: 94,
    ProductCategory.foundation: 92,
    ProductCategory.skin_tint: 90,
    ProductCategory.concealer: 86,
    ProductCategory.powder: 82,
    ProductCategory.primer: 70,
    ProductCategory.brow_gel: 60,
    ProductCategory.setting_spray: 58,
    ProductCategory.lipstick: 54,
    ProductCategory.mascara: 52,
    ProductCategory.eyeliner: 50,
    ProductCategory.blush: 48,
    ProductCategory.highlighter: 46,
}

BUNDLE_SUPPORT = {
    ProductCategory.cleanser: [ProductCategory.serum, ProductCategory.moisturizer, ProductCategory.spf],
    ProductCategory.serum: [ProductCategory.moisturizer, ProductCategory.spf, ProductCategory.cleanser],
    ProductCategory.moisturizer: [ProductCategory.spf, ProductCategory.serum, ProductCategory.cleanser],
    ProductCategory.foundation: [ProductCategory.concealer, ProductCategory.powder, ProductCategory.spf],
    ProductCategory.skin_tint: [ProductCategory.concealer, ProductCategory.powder, ProductCategory.spf],
    ProductCategory.concealer: [ProductCategory.foundation, ProductCategory.skin_tint, ProductCategory.powder],
    ProductCategory.lipstick: [ProductCategory.mascara, ProductCategory.eyeliner, ProductCategory.foundation],
    ProductCategory.mascara: [ProductCategory.eyeliner, ProductCategory.lipstick, ProductCategory.concealer],
}


def hero_score(item: RecommendationItem, plan: RecommendationPlan, context: UserContext) -> float:
    score = HERO_PRIORITY.get(item.category, 40)
    score += item.final_score * 20
    if item.category in {ProductCategory.foundation, ProductCategory.skin_tint, ProductCategory.concealer, ProductCategory.powder}:
        score += 6
    if plan.look_strategy == 'sensual' and item.category in {ProductCategory.lipstick, ProductCategory.eyeliner, ProductCategory.mascara}:
        score += 54
    if plan.look_strategy == 'soft_luxury' and item.category in {ProductCategory.foundation, ProductCategory.primer, ProductCategory.blush, ProductCategory.highlighter}:
        score += 18
    if plan.look_strategy == 'fresh' and item.category in {ProductCategory.skin_tint, ProductCategory.blush, ProductCategory.lip_tint}:
        score += 16
    if context.budget_segment.value == 'premium' and item.price_segment.value == 'premium':
        score += 5
    if context.budget_direction.value == 'cheaper' and item.price_segment.value == 'budget':
        score += 4
    return score


def order_for_conversion(items: list[RecommendationItem], plan: RecommendationPlan, context: UserContext) -> list[RecommendationItem]:
    if not items:
        return []
    ordered = sorted(items, key=lambda item: hero_score(item, plan, context), reverse=True)
    hero = ordered[0]
    support_order = BUNDLE_SUPPORT.get(hero.category, [])
    support_rank = {category: idx for idx, category in enumerate(support_order)}
    rest = ordered[1:]
    rest.sort(key=lambda item: (support_rank.get(item.category, 999), -hero_score(item, plan, context)))
    return [hero, *rest]


def bundle_story(items: list[RecommendationItem]) -> tuple[RecommendationItem | None, list[RecommendationItem]]:
    if not items:
        return None, []
    return items[0], items[1:3]


def cta_for_conversion(plan: RecommendationPlan, context: UserContext) -> str:
    if context.budget_segment.value == 'premium':
        return 'Если хочешь, соберу более premium-версию того же Beauty ID basket и отмечу, где именно видна доплата.'
    if context.budget_direction.value == 'cheaper':
        return 'Если нужно, ещё сильнее ужму basket и оставлю только шаги с максимальной retail-отдачей.'
    if plan.look_strategy == 'sensual':
        return 'Если хочешь, доберу к этому 1-2 акцентных продукта, чтобы образ выглядел более вечерним и цепляющим.'
    if plan.look_strategy == 'soft_luxury':
        return 'Если хочешь, превращу это в более polished luxury-set без перегруза по количеству продуктов.'
    if plan.look_strategy == 'fresh':
        return 'Если хочешь, добавлю ещё пару лёгких штрихов, чтобы набор выглядел свежее и легче.'
    return 'Если хочешь, я сразу дособеру это в более цельный guided basket.'


def one_best_pick(items: list[RecommendationItem]) -> RecommendationItem | None:
    return items[0] if items else None


def vibe_alternative(items: list[RecommendationItem]) -> RecommendationItem | None:
    return items[1] if len(items) > 1 else None


def entry_bundle(items: list[RecommendationItem]) -> list[RecommendationItem]:
    return items[:3]


def selling_frame(items: list[RecommendationItem], plan: RecommendationPlan, context: UserContext) -> list[str]:
    lines: list[str] = []
    best = one_best_pick(items)
    alt = vibe_alternative(items)
    bundle = entry_bundle(items)
    if best:
        lines.append(f"Hero pick сейчас — {best.title}: он задаёт весь вектор набора.")
    if alt and alt.category != best.category:
        lines.append(f"Поддерживающим шагом я бы смотрел на {alt.title}, чтобы basket ощущался собранным, а не случайным.")
    if len(bundle) >= 2:
        lines.append("Самый лёгкий вход в образ сейчас — взять hero и добрать 1-2 поддерживающих шага для быстрого вау-эффекта.")
    if context.budget_segment.value == 'budget':
        lines.append('Если хочешь, могу оставить только позиции с максимальным wow-per-ruble.')
    if plan.look_strategy == 'soft_luxury':
        lines.append('Здесь особенно хорошо работает polished minimum: меньше продуктов, но каждый усиливает ощущение дорогого образа.')
    return lines
