"""Optional DummyJSON fashion/lifestyle catalog importer.

DummyJSON is an ingestion source only. Imported rows are persisted locally and
shop searches never call the external API. Re-running the importer updates rows
by source + external_product_id instead of creating duplicates.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import requests
from sqlalchemy import select
from sqlalchemy.orm import Session

from .brightdata import BrightDataError, normalize
from .models import DEMO_MERCHANT_ID, Product

DUMMYJSON_URL = "https://dummyjson.com/products"
_ALLOWED_CATEGORIES = {
    "womens-dresses", "womens-jewellery", "womens-shoes", "womens-bags",
    "mens-shirts", "mens-shoes", "mens-watches", "womens-watches",
    "sunglasses", "beauty", "fragrances", "tops", "laptops", "motorcycle",
}


def _category(raw: str) -> tuple[str, str]:
    value = (raw or "lifestyle").strip().lower()
    labels = {
        "womens-dresses": ("Dresses", "Women's Dresses"),
        "womens-jewellery": ("Jewellery", "Women's Jewellery"),
        "womens-shoes": ("Footwear", "Women's Shoes"),
        "womens-bags": ("Bags", "Women's Bags"),
        "mens-shirts": ("Shirts", "Men's Shirts"),
        "mens-shoes": ("Footwear", "Men's Shoes"),
        "mens-watches": ("Accessories", "Men's Watches"),
        "womens-watches": ("Accessories", "Women's Watches"),
        "sunglasses": ("Accessories", "Sunglasses"),
        "beauty": ("Beauty", "Beauty"),
        "fragrances": ("Beauty", "Fragrances"),
        "tops": ("Tops", "Tops"),
    }
    return labels.get(value, ("Lifestyle", value.replace("-", " ").title()))


def _normalize(item: dict) -> dict:
    category, subcategory = _category(str(item.get("category", "")))
    gender = "women" if str(item.get("category", "")).startswith("womens") else "men" if str(item.get("category", "")).startswith("mens") else "unisex"
    data = normalize({
        "id": f"dummyjson:{item.get('id')}",
        "title": item.get("title"),
        "description": item.get("description", ""),
        "category": category,
        "subcategory": subcategory,
        "brand": item.get("brand", ""),
        # DummyJSON prices are USD; Vastra Studio stores integer INR amounts.
        "price": round(float(item.get("price", 0) or 0) * 83),
        "currency": "INR",
        "stock": item.get("stock", 0),
        "thumbnail": item.get("thumbnail", ""),
        "url": f"https://dummyjson.com/products/{item.get('id')}",
        "rating": item.get("rating", 0),
        "tags": [category.lower(), subcategory.lower()],
        "gender": gender,
    })
    data["source"] = "dummyjson"
    return data


def _upsert(db: Session, data: dict) -> str:
    identity = data["external_product_id"]
    existing = db.execute(select(Product).where(Product.merchant_id == DEMO_MERCHANT_ID, Product.source == "dummyjson", Product.external_product_id == identity)).scalar_one_or_none()
    action = "updated" if existing else "created"
    if existing is None:
        existing = Product(merchant_id=DEMO_MERCHANT_ID, source="dummyjson")
        db.add(existing)
    for key, value in data.items():
        setattr(existing, key, value)
    existing.source = "dummyjson"
    existing.imported_at = datetime.now(timezone.utc)
    return action


def import_catalog(db: Session, *, page_size: int = 100) -> dict:
    try:
        first = requests.get(DUMMYJSON_URL, params={"limit": 0}, timeout=15)
        first.raise_for_status()
        total = int(first.json().get("total", 0))
        rows: list[dict] = []
        for skip in range(0, total, page_size):
            response = requests.get(DUMMYJSON_URL, params={"limit": page_size, "skip": skip}, timeout=20)
            response.raise_for_status()
            payload: Any = response.json()
            rows.extend(item for item in payload.get("products", []) if item.get("category") in _ALLOWED_CATEGORIES)
    except requests.RequestException as exc:
        raise BrightDataError("DummyJSON could not be reached; existing local products remain available.") from exc
    except (ValueError, TypeError) as exc:
        raise BrightDataError("DummyJSON returned an invalid catalog response.") from exc

    created = updated = skipped = 0
    errors: list[str] = []
    for raw in rows:
        try:
            if _upsert(db, _normalize(raw)) == "created":
                created += 1
            else:
                updated += 1
        except (BrightDataError, ValueError, TypeError, KeyError) as exc:
            skipped += 1
            errors.append(str(exc))
    db.commit()
    return {"source": "dummyjson", "fetched": len(rows), "created": created, "updated": updated, "skipped": skipped, "errors": errors[:20]}
