"""Server-side cart — the backend is the single source of truth for cart contents
and totals. The frontend holds only a ``cart_id``; it never sends prices or
amounts. Unit prices are snapshotted at add-time so a later catalog price change
cannot alter an in-flight cart.

Money is integer rupees throughout.
"""
from __future__ import annotations

from typing import Optional

from sqlalchemy.orm import Session

from . import catalog
from .models import Cart, CartItem, CartStatus


class CartError(Exception):
    """Domain error with a stable ``code`` for the structured API envelope."""

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


def create_cart(db: Session, *, budget: Optional[int] = None, ai_assisted: bool = False) -> Cart:
    cart = Cart(status=CartStatus.ACTIVE, budget=budget, ai_assisted=ai_assisted)
    db.add(cart)
    db.commit()
    db.refresh(cart)
    return cart


def get_cart(db: Session, cart_id: int) -> Optional[Cart]:
    return db.get(Cart, cart_id)


def get_active_cart(db: Session, cart_id: int) -> Cart:
    cart = get_cart(db, cart_id)
    if cart is None:
        raise CartError("CART_NOT_FOUND", "Cart not found.")
    if cart.status != CartStatus.ACTIVE:
        raise CartError("CART_NOT_ACTIVE", "This cart has already been checked out.")
    return cart


def _find_item(cart: Cart, product_id: int) -> Optional[CartItem]:
    return next((it for it in cart.items if it.product_id == product_id), None)


def add_item(db: Session, cart_id: int, product_id: int, *, quantity: int = 1, is_upsell: bool = False) -> Cart:
    """Add (or increment) a product in the cart after validating live inventory."""
    quantity = max(1, int(quantity))
    cart = get_active_cart(db, cart_id)

    product = catalog.get_product(db, product_id)
    if product is None or not product.active:
        raise CartError("PRODUCT_NOT_FOUND", "Product is unavailable.")

    existing = _find_item(cart, product_id)
    desired_qty = quantity + (existing.quantity if existing else 0)
    if product.stock < desired_qty:
        raise CartError("OUT_OF_STOCK", f"Only {product.stock} of “{product.name}” left in stock.")

    if existing:
        existing.quantity = desired_qty
        if is_upsell:
            existing.is_upsell = True
    else:
        db.add(
            CartItem(
                cart_id=cart.id,
                product_id=product.id,
                product_name=product.name,
                unit_price=product.price,  # snapshot
                quantity=quantity,
                is_upsell=is_upsell,
            )
        )

    if is_upsell:
        cart.ai_assisted = True

    db.commit()
    db.refresh(cart)
    return cart


def update_item_quantity(db: Session, cart_id: int, item_id: int, quantity: int) -> Cart:
    cart = get_active_cart(db, cart_id)
    item = next((it for it in cart.items if it.id == item_id), None)
    if item is None:
        raise CartError("ITEM_NOT_FOUND", "Cart item not found.")

    quantity = int(quantity)
    if quantity <= 0:
        db.delete(item)
        db.commit()
        db.refresh(cart)
        return cart

    product = catalog.get_product(db, item.product_id)
    if product is None or product.stock < quantity:
        available = product.stock if product else 0
        raise CartError("OUT_OF_STOCK", f"Only {available} in stock.")

    item.quantity = quantity
    db.commit()
    db.refresh(cart)
    return cart


def remove_item(db: Session, cart_id: int, item_id: int) -> Cart:
    cart = get_active_cart(db, cart_id)
    item = next((it for it in cart.items if it.id == item_id), None)
    if item is not None:
        db.delete(item)
        db.commit()
        db.refresh(cart)
    return cart


def clear_cart(db: Session, cart_id: int) -> Cart:
    cart = get_active_cart(db, cart_id)
    for item in list(cart.items):
        db.delete(item)
    db.commit()
    db.refresh(cart)
    return cart


def cart_totals(cart: Cart) -> dict:
    """Authoritative totals computed from snapshotted unit prices (integer rupees)."""
    subtotal = sum(it.line_total for it in cart.items)
    upsell_total = sum(it.line_total for it in cart.items if it.is_upsell)
    discount = 0  # reserved for future promo codes; policy engine already enforces the cap
    total = subtotal - discount
    return {
        "subtotal": subtotal,
        "discount": discount,
        "total": total,
        "upsell_total": upsell_total,
        "item_count": sum(it.quantity for it in cart.items),
    }


def serialize_cart(cart: Cart) -> dict:
    totals = cart_totals(cart)
    return {
        "id": cart.id,
        "status": cart.status,
        "budget": cart.budget,
        "ai_assisted": cart.ai_assisted,
        "items": [
            {
                "id": it.id,
                "product_id": it.product_id,
                "name": it.product_name,
                "unit_price": it.unit_price,
                "quantity": it.quantity,
                "line_total": it.line_total,
                "is_upsell": it.is_upsell,
            }
            for it in cart.items
        ],
        **totals,
        "budget_remaining": (cart.budget - totals["total"]) if cart.budget is not None else None,
        "over_budget": (cart.budget is not None and totals["total"] > cart.budget),
    }
