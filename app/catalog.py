from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from urllib.parse import quote_plus

from .models import CatalogProduct, HalalStatus, ProductCategory


IRRITANT_MAP = {
    "fragrance": {"fragrance", "parfum", "essential_oils", "limonene", "linalool", "citral", "geraniol", "eugenol", "cinnamal", "benzyl alcohol"},
    "niacinamide": {"niacinamide"},
    "retinoids": {"retinol", "retinal", "retinoid"},
    "aha": {"glycolic acid", "lactic acid", "aha"},
    "bha": {"salicylic acid", "bha"},
    "acids": {"acid", "aha", "bha", "glycolic acid", "lactic acid", "salicylic acid"},
    "alcohol_denat": {"alcohol denat", "ethanol"},
}


def _product_image_url(sku: str) -> str:
    return f"/v1/product-media/{sku}"


def _goldapple_search_query(title: str, brand: str) -> str:
    return quote_plus(f"{brand} {title} Golden Apple")


CATEGORY_BADGES = {
    ProductCategory.foundation: "Hero complexion",
    ProductCategory.skin_tint: "Second-skin pick",
    ProductCategory.concealer: "Under-eye support",
    ProductCategory.powder: "Shine balance",
    ProductCategory.serum: "Care layer",
    ProductCategory.moisturizer: "Barrier support",
    ProductCategory.spf: "Daily SPF",
}


@lru_cache(maxsize=1)
def load_catalog() -> list[CatalogProduct]:
    path = Path(__file__).parent / "data" / "catalog.json"
    raw = json.loads(path.read_text(encoding="utf-8"))
    enriched: list[CatalogProduct] = []
    for item in raw:
        ingredients = [str(ingredient).lower() for ingredient in item.get("ingredients", [])]
        common_irritants = sorted({
            key
            for key, tokens in IRRITANT_MAP.items()
            if any(any(token in ingredient for token in tokens) for ingredient in ingredients)
        })
        sensitivity_exclusions = [key for key in common_irritants if key in {"niacinamide", "retinoids", "aha", "bha", "acids", "alcohol_denat"}]
        if item["category"] in {"lipstick", "mascara", "eyeliner"}:
            halal_status = HalalStatus.unknown
            halal_note = "No explicit halal confirmation in demo metadata yet."
            contains_animal_derived = True
        elif "alcohol denat" in ingredients:
            halal_status = HalalStatus.unknown
            halal_note = "Alcohol content needs live catalog confirmation."
            contains_animal_derived = False
        else:
            halal_status = HalalStatus.friendly
            halal_note = "Demo metadata suggests no obvious animal-derived ingredient flags."
            contains_animal_derived = False
        alcohol_free = not any("alcohol" in ingredient for ingredient in ingredients)
        item = {
            **item,
            "image_url": item.get("image_url") or _product_image_url(item["sku"]),
            "goldapple_url": item.get("goldapple_url"),
            "goldapple_search_query": item.get("goldapple_search_query") or _goldapple_search_query(item["title"], item["brand"]),
            "hero_badge": item.get("hero_badge") or CATEGORY_BADGES.get(ProductCategory(item["category"]), "Beauty pick"),
            "card_note": item.get("card_note") or "Live Golden Apple URL can be connected when the retail catalog is linked.",
            "halal_status": item.get("halal_status") or halal_status.value,
            "halal_note": item.get("halal_note") or halal_note,
            "contains_animal_derived": item.get("contains_animal_derived", contains_animal_derived),
            "alcohol_free": item.get("alcohol_free", alcohol_free),
            "common_irritants": item.get("common_irritants") or common_irritants,
            "sensitivity_exclusions": item.get("sensitivity_exclusions") or sensitivity_exclusions,
        }
        enriched.append(CatalogProduct.model_validate(item))
    return enriched
