"""Deterministic catalog search & inventory service.

The database does the coarse filtering (category, price band, stock, gender,
active). A small, fully deterministic relevance score then ranks the candidate
set in Python. The LLM never runs SQL and never sees the whole catalog — it only
receives a short candidate list to reason over (see ``llm.py`` / ``agent.py``).
"""
from __future__ import annotations

from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import DEMO_MERCHANT_ID, Product, ProductRelation

FASHION_CATEGORIES = {
    "Sarees", "Kurtas", "Dupattas", "Jewellery", "Bags", "Accessories",
    "Gifts", "Footwear", "Dresses", "Shirts", "Trousers", "Lehengas",
    "Festive Wear", "Casual Wear", "Tops",
}


def _tokens(text: str) -> List[str]:
    return [t for t in "".join(c.lower() if c.isalnum() else " " for c in (text or "")).split() if len(t) > 1]


def _score(product: Product, query_tokens: List[str], occasion: Optional[str]) -> float:
    """Relevance score for a product against the parsed query. Higher is better."""
    if not query_tokens and not occasion:
        return product.rating  # no query signal -> rank by quality

    haystack_name = (product.name or "").lower()
    haystack_desc = (product.description or "").lower()
    tags = [str(t).lower() for t in (product.tags or [])]
    occasions = [str(o).lower() for o in (product.occasion or [])]
    category = (product.category or "").lower()
    subcategory = (product.subcategory or "").lower()

    score = 0.0
    for tok in query_tokens:
        variants = {tok, tok[:-1] if len(tok) > 3 and tok.endswith("s") else tok}
        if any(variant in haystack_name for variant in variants):
            score += 5.0
        if any(variant in tag for variant in variants for tag in tags):
            score += 4.0
        if any(variant == category or variant == subcategory or variant in category for variant in variants):
            score += 3.5
        if any(variant in occasion_name for variant in variants for occasion_name in occasions):
            score += 3.0
        if any(variant in haystack_desc for variant in variants):
            score += 1.5

    if occasion and occasion.lower() in occasions:
        score += 6.0

    # Quality tie-breakers keep results stable & sensible.
    score += product.rating * 0.4
    if product.stock > 0:
        score += 0.5
    return score


def search_products(
    db: Session,
    query: str = "",
    *,
    category: Optional[str] = None,
    occasion: Optional[str] = None,
    min_price: Optional[int] = None,
    max_price: Optional[int] = None,
    tags: Optional[List[str]] = None,
    gender: Optional[str] = None,
    in_stock_only: bool = True,
    limit: int = 10,
    merchant_id: str = DEMO_MERCHANT_ID,
    allowed_categories: Optional[set[str]] = None,
) -> List[Product]:
    """Return the best-matching products, most relevant first."""
    stmt = select(Product).where(Product.merchant_id == merchant_id, Product.active.is_(True))

    if category:
        stmt = stmt.where(Product.category == category)
    if min_price is not None:
        stmt = stmt.where(Product.price >= int(min_price))
    if max_price is not None:
        stmt = stmt.where(Product.price <= int(max_price))
    if gender and gender in {"women", "men"}:
        stmt = stmt.where(Product.gender.in_([gender, "unisex"]))
    if allowed_categories:
        stmt = stmt.where(Product.category.in_(allowed_categories))
    if in_stock_only:
        stmt = stmt.where(Product.stock > 0)

    candidates = list(db.execute(stmt).scalars().all())

    query_tokens = _tokens(query)
    if tags:
        query_tokens.extend(t.lower() for t in tags)

    ranked = sorted(
        candidates,
        key=lambda p: (_score(p, query_tokens, occasion), p.rating, -p.price),
        reverse=True,
    )
    return ranked[: max(1, limit)]


def get_product(db: Session, product_id: int, merchant_id: str = DEMO_MERCHANT_ID) -> Optional[Product]:
    return db.execute(
        select(Product).where(Product.id == product_id, Product.merchant_id == merchant_id)
    ).scalar_one_or_none()


def get_related_products(
    db: Session,
    product_id: int,
    *,
    limit: int = 4,
    in_stock_only: bool = True,
    max_price: Optional[int] = None,
) -> List[Product]:
    """Return curated related products (from product_relations), highest priority first."""
    rows = list(
        db.execute(
            select(ProductRelation)
            .where(ProductRelation.product_id == product_id)
            .order_by(ProductRelation.priority.asc())
        ).scalars().all()
    )

    results: List[Product] = []
    seen: set[int] = set()
    for rel in rows:
        if rel.related_product_id in seen:
            continue
        product = get_product(db, rel.related_product_id)
        if not product or not product.active:
            continue
        if in_stock_only and product.stock <= 0:
            continue
        if max_price is not None and product.price > max_price:
            continue
        seen.add(product.id)
        results.append(product)
        if len(results) >= limit:
            break
    return results


def check_inventory(db: Session, product_id: int, quantity: int = 1) -> bool:
    product = get_product(db, product_id)
    return bool(product and product.active and product.stock >= max(1, quantity))


def list_categories(db: Session, merchant_id: str = DEMO_MERCHANT_ID) -> List[str]:
    rows = db.execute(
        select(Product.category).where(Product.merchant_id == merchant_id, Product.active.is_(True)).distinct()
    ).scalars().all()
    return sorted({r for r in rows if r})
