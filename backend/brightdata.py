"""Backend-only Bright Data catalog ingestion.

The importer accepts a Bright Data dataset/API response and normalizes it into
local Product rows. The shopping flow never calls Bright Data; SQLite remains
its source of truth. Configure BRIGHTDATA_API_URL for the dataset endpoint.
"""
from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any

import requests
from dotenv import load_dotenv
from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import DEMO_MERCHANT_ID, Product

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))


class BrightDataError(RuntimeError):
    pass


def _value(item: dict, *keys: str, default=None):
    for key in keys:
        value = item.get(key)
        if value not in (None, ""):
            return value
    return default


def _products(payload: Any) -> list[dict]:
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    if isinstance(payload, dict):
        for key in ("products", "items", "results", "data"):
            if isinstance(payload.get(key), list):
                return [item for item in payload[key] if isinstance(item, dict)]
    raise BrightDataError("Bright Data returned an unsupported product payload.")


def normalize(item: dict) -> dict:
    raw_price = _value(item, "price", "sale_price", "amount")
    try:
        price = int(round(float(str(raw_price).replace(",", "").replace("₹", ""))))
    except (TypeError, ValueError):
        raise BrightDataError("A product had an invalid price.")
    if price < 0:
        raise BrightDataError("A product had a negative price.")
    name = str(_value(item, "name", "title", default="")).strip()
    category = str(_value(item, "category", "product_type", default="Accessories")).strip() or "Accessories"
    if len(name) < 2:
        raise BrightDataError("A product had no usable name.")
    tags = _value(item, "tags", "keywords", default=[])
    if isinstance(tags, str):
        tags = [tag.strip() for tag in tags.split(",") if tag.strip()]
    occasions = _value(item, "occasion", "occasions", default=[])
    if isinstance(occasions, str):
        occasions = [occasion.strip() for occasion in occasions.split(",") if occasion.strip()]
    return {
        "name": name[:200],
        "description": str(_value(item, "description", default=""))[:4000],
        "category": category[:64],
        "subcategory": str(_value(item, "subcategory", default=""))[:64],
        "brand": str(_value(item, "brand", default=""))[:96],
        "price": price,
        "currency": str(_value(item, "currency", default="INR"))[:8].upper(),
        "stock": max(0, int(_value(item, "stock", "quantity", default=0) or 0)),
        "image_url": str(_value(item, "image_url", "image", "thumbnail", default=""))[:2000],
        "source_url": str(_value(item, "source_url", "url", "product_url", default=""))[:2000],
        "external_product_id": str(_value(item, "external_product_id", "id", "product_id", default=""))[:160] or None,
        "rating": min(5, max(0, float(_value(item, "rating", "stars", default=0) or 0))),
        "reviews_count": max(0, int(_value(item, "reviews_count", "review_count", default=0) or 0)),
        "color": str(_value(item, "color", default=""))[:64],
        "material": str(_value(item, "material", default=""))[:96],
        "style": str(_value(item, "style", default=""))[:96],
        "season": str(_value(item, "season", default=""))[:64],
        "tags": tags[:30],
        "occasion": occasions[:20],
        "gender": str(_value(item, "gender", default="unisex"))[:16],
    }


def import_catalog(db: Session, *, payload: Any = None) -> dict:
    """Import supplied data or fetch the configured Bright Data endpoint."""
    api_key = os.getenv("BRIGHTDATA_API_KEY", "").strip()
    endpoint = os.getenv("BRIGHTDATA_API_URL", "").strip()
    if payload is None:
        if not api_key or not endpoint:
            raise BrightDataError("Bright Data is not configured. Set BRIGHTDATA_API_KEY and BRIGHTDATA_API_URL.")
        try:
            response = requests.get(endpoint, headers={"Authorization": f"Bearer {api_key}"}, timeout=20)
            response.raise_for_status()
            payload = response.json()
        except requests.RequestException as exc:
            raise BrightDataError("Bright Data could not be reached.") from exc
        except ValueError as exc:
            raise BrightDataError("Bright Data returned invalid JSON.") from exc
    rows = _products(payload)
    created = updated = skipped = 0
    errors = []
    for raw in rows:
        try:
            data = normalize(raw)
            identity = data["external_product_id"]
            existing = None
            if identity:
                existing = db.execute(select(Product).where(Product.merchant_id == DEMO_MERCHANT_ID, Product.external_product_id == identity)).scalar_one_or_none()
            if existing is None:
                existing = db.execute(select(Product).where(Product.merchant_id == DEMO_MERCHANT_ID, Product.name == data["name"], Product.source == "brightdata")).scalar_one_or_none()
            if existing is None:
                existing = Product(merchant_id=DEMO_MERCHANT_ID, source="brightdata")
                db.add(existing)
                created += 1
            else:
                updated += 1
            for key, value in data.items():
                setattr(existing, key, value)
            existing.source = "brightdata"
            existing.imported_at = datetime.now(timezone.utc)
        except (BrightDataError, ValueError, TypeError) as exc:
            skipped += 1
            errors.append(str(exc))
    db.commit()
    return {"created": created, "updated": updated, "skipped": skipped, "errors": errors[:20], "total": len(rows)}
