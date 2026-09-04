"""Idempotent database seeding for the demo merchant.

Running ``seed_all`` multiple times is safe: it upserts the merchant config and
inserts products/relations only if they are missing. Call ``reset_and_seed`` for
a clean demo state (labelled "Demo only" in the UI/README).
"""
from __future__ import annotations

from typing import Dict

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from .db import session_scope
from .models import (
    DEMO_MERCHANT_ID,
    MerchantConfig,
    Product,
    ProductRelation,
)
from .seed_products import PRODUCTS, RELATIONS


def _ensure_merchant(db: Session) -> MerchantConfig:
    config = db.get(MerchantConfig, DEMO_MERCHANT_ID)
    if config is None:
        config = MerchantConfig(
            merchant_id=DEMO_MERCHANT_ID,
            name="Vastra Studio",
            max_order_value=10000,
            max_upsell_value=1500,
            max_discount_pct=20,
            require_user_confirmation=True,
            agent_active=True,
            currency="INR",
        )
        db.add(config)
        db.flush()
    return config


def _seed_products(db: Session) -> Dict[str, int]:
    """Insert any products not already present (keyed by name). Returns name->id."""
    existing = {
        p.name: p.id
        for p in db.execute(
            select(Product).where(Product.merchant_id == DEMO_MERCHANT_ID)
        ).scalars().all()
    }

    for spec in PRODUCTS:
        if spec["name"] in existing:
            continue
        product = Product(
            merchant_id=DEMO_MERCHANT_ID,
            name=spec["name"],
            description=spec.get("description", ""),
            category=spec["category"],
            subcategory=spec.get("subcategory", ""),
            brand=spec.get("brand", ""),
            price=int(spec["price"]),
            currency="INR",
            stock=int(spec.get("stock", 0)),
            image_url=spec.get("image_url", ""),  # empty -> frontend renders a branded gradient tile
            rating=float(spec.get("rating", 4.5)),
            tags=list(spec.get("tags", [])),
            occasion=list(spec.get("occasion", [])),
            gender=spec.get("gender", "unisex"),
            active=True,
        )
        db.add(product)
        db.flush()
        existing[product.name] = product.id

    return existing


def _seed_relations(db: Session, name_to_id: Dict[str, int]) -> None:
    """Insert curated relations, resolving product names to ids. Skips duplicates."""
    existing_pairs = {
        (r.product_id, r.related_product_id)
        for r in db.execute(select(ProductRelation)).scalars().all()
    }

    for rel in RELATIONS:
        pid = name_to_id.get(rel["product"])
        rid = name_to_id.get(rel["related"])
        if not pid or not rid or pid == rid:
            continue
        if (pid, rid) in existing_pairs:
            continue
        db.add(
            ProductRelation(
                product_id=pid,
                related_product_id=rid,
                relation_type=rel.get("type", "complement"),
                priority=int(rel.get("priority", 100)),
            )
        )
        existing_pairs.add((pid, rid))


def seed_all() -> Dict[str, int]:
    """Idempotently seed merchant config, products and relations. Returns a summary."""
    with session_scope() as db:
        _ensure_merchant(db)
        name_to_id = _seed_products(db)
        _seed_relations(db, name_to_id)
        product_count = db.execute(
            select(Product).where(Product.merchant_id == DEMO_MERCHANT_ID)
        ).scalars().all()
        relation_count = db.execute(select(ProductRelation)).scalars().all()
        return {"products": len(product_count), "relations": len(relation_count)}


def reset_and_seed() -> Dict[str, int]:
    """Demo only: wipe transactional + catalog tables, then reseed from scratch."""
    from .models import (
        AgentEvent,
        Cart,
        CartItem,
        Order,
        OrderItem,
        Payment,
    )

    with session_scope() as db:
        # Order matters for FK integrity on SQLite when constraints are enforced.
        for model in (Payment, OrderItem, Order, CartItem, Cart, AgentEvent, ProductRelation, Product):
            db.execute(delete(model))
    return seed_all()


if __name__ == "__main__":  # pragma: no cover - manual utility
    from .db import init_db

    init_db()
    summary = seed_all()
    print(f"Seeded Vastra Studio: {summary['products']} products, {summary['relations']} relations.")
