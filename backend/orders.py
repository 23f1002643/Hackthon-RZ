"""Order lifecycle & payment verification — the deterministic money path.

State machine (Order.status):

    ORDER_CREATED ──▶ PAID ──▶ COMPLETED
          │
          ├──▶ PAYMENT_VERIFICATION_FAILED   (bad/forged signature)
          ├──▶ PAYMENT_FAILED                (buyer cancelled / gateway failure)
          └──▶ CANCELLED                     (superseded by an edited cart)

Guarantees:
  * The backend computes the amount from the server-side cart. Frontend amounts
    are never trusted (the client only sends ``cart_id`` then ``order_id``).
  * A payment is marked successful only after the Razorpay signature verifies
    server-side. On failure the order is never PAID and inventory is untouched.
  * Inventory is decremented exactly once, guarded by ``Order.inventory_committed``.
  * ``create_order`` and ``verify_and_complete`` are idempotent under retries.
"""
from __future__ import annotations

import uuid
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from . import cart_service, policy, razorpay_tools
from .audit import EventType, record_event
from .cart_service import CartError
from .models import (
    Cart,
    CartStatus,
    Customer,
    MerchantConfig,
    Order,
    OrderItem,
    OrderStatus,
    Payment,
    PaymentStatus,
    Product,
    EventSource,
)
from .razorpay_tools import RazorpayError


class OrderError(Exception):
    """Domain error carrying a stable ``code`` and optional structured ``details``."""

    def __init__(self, code: str, message: str, details: Optional[dict] = None):
        super().__init__(message)
        self.code = code
        self.message = message
        self.details = details or {}


_OPEN_ORDER_STATES = (OrderStatus.ORDER_CREATED, OrderStatus.PAYMENT_PENDING)
_TERMINAL_PAID_STATES = (OrderStatus.PAID, OrderStatus.COMPLETED)


def _order_number() -> str:
    return f"VS-{uuid.uuid4().hex[:8].upper()}"


def get_order(db: Session, order_id: int) -> Optional[Order]:
    return db.get(Order, order_id)


def get_order_by_razorpay_id(db: Session, razorpay_order_id: str) -> Optional[Order]:
    return db.execute(
        select(Order).where(Order.razorpay_order_id == razorpay_order_id)
    ).scalar_one_or_none()


# --------------------------------------------------------------------------- #
# Create
# --------------------------------------------------------------------------- #
def create_order(
    db: Session,
    cart_id: int,
    config: MerchantConfig,
    *,
    confirmed: bool,
    customer: Optional[dict] = None,
) -> Order:
    """Turn an active cart into a Razorpay-backed order after policy + inventory checks."""
    try:
        cart = cart_service.get_active_cart(db, cart_id)
    except CartError as exc:
        raise OrderError(exc.code, exc.message) from exc

    if not cart.items:
        raise OrderError("EMPTY_CART", "Your cart is empty.")

    totals = cart_service.cart_totals(cart)
    subtotal, discount, total = totals["subtotal"], totals["discount"], totals["total"]

    # 1) Policy — the deterministic safety gate (records the decision either way).
    result = policy.check_order(
        config,
        subtotal=subtotal,
        discount=discount,
        total=total,
        budget=cart.budget,
        confirmed=confirmed,
    )
    record_event(
        db,
        event_type=EventType.POLICY_CHECK,
        description=f"Policy {result.code}: {result.message}",
        source=EventSource.POLICY,
        cart_id=cart.id,
        metadata=result.to_dict(),
    )
    if not result.allowed:
        raise OrderError(result.code, result.message, result.details)

    # 2) Re-validate inventory at order time (stock can change between add and checkout).
    for item in cart.items:
        product = db.get(Product, item.product_id)
        if product is None or not product.active or product.stock < item.quantity:
            available = product.stock if product else 0
            raise OrderError(
                "OUT_OF_STOCK",
                f"“{item.product_name}” is no longer available in the requested quantity.",
                {"product_id": item.product_id, "available": available},
            )

    # 3) Idempotency: reuse an open order for this cart if the total is unchanged.
    existing = db.execute(
        select(Order)
        .where(Order.cart_id == cart.id, Order.status.in_(_OPEN_ORDER_STATES))
        .order_by(Order.id.desc())
    ).scalars().first()
    if existing is not None:
        if existing.total == total and existing.razorpay_order_id:
            return existing
        existing.status = OrderStatus.CANCELLED  # cart changed -> supersede stale order

    # 4) Optional customer record.
    customer_id = _upsert_customer(db, customer)

    # 5) Create the REAL Razorpay order (amount is backend-computed).
    order_number = _order_number()
    try:
        rzp_order = razorpay_tools.create_order(
            total,
            receipt=order_number,
            notes={"merchant": config.merchant_id, "cart_id": str(cart.id), "ai_assisted": str(cart.ai_assisted)},
        )
    except RazorpayError as exc:
        record_event(
            db,
            event_type=EventType.AGENT_ERROR,
            description="Could not create payment order with Razorpay.",
            source=EventSource.ERROR,
            cart_id=cart.id,
            metadata={"error": str(exc)},
        )
        raise OrderError("PAYMENT_GATEWAY_UNAVAILABLE", "Unable to start payment right now. Please try again.") from exc

    # 6) Persist the order, items and a pending payment row.
    order = Order(
        order_number=order_number,
        customer_id=customer_id,
        cart_id=cart.id,
        razorpay_order_id=rzp_order.get("id"),
        subtotal=subtotal,
        discount=discount,
        total=total,
        currency=config.currency,
        status=OrderStatus.ORDER_CREATED,
        payment_status=PaymentStatus.CREATED,
        ai_assisted=cart.ai_assisted,
        upsell_total=totals["upsell_total"],
        inventory_committed=False,
    )
    db.add(order)
    db.flush()

    for item in cart.items:
        db.add(
            OrderItem(
                order_id=order.id,
                product_id=item.product_id,
                product_name=item.product_name,
                unit_price=item.unit_price,
                quantity=item.quantity,
                total=item.line_total,
                is_upsell=item.is_upsell,
            )
        )

    db.add(
        Payment(
            order_id=order.id,
            razorpay_order_id=rzp_order.get("id"),
            status=PaymentStatus.CREATED,
            amount=total,
        )
    )

    record_event(
        db,
        event_type=EventType.ORDER_CREATED,
        description=f"Order {order_number} created for ₹{total:,} ({totals['item_count']} item(s)).",
        source=EventSource.ORDER,
        order_id=order.id,
        cart_id=cart.id,
        metadata={"razorpay_order_id": rzp_order.get("id"), "total": total, "upsell_total": totals["upsell_total"]},
        commit=False,
    )
    db.commit()
    db.refresh(order)
    return order


def _upsert_customer(db: Session, customer: Optional[dict]) -> Optional[int]:
    if not customer:
        return None
    name = (customer.get("name") or "Guest").strip() or "Guest"
    email = (customer.get("email") or None)
    contact = (customer.get("contact") or None)
    row = Customer(name=name, email=email, contact=contact)
    db.add(row)
    db.flush()
    return row.id


# --------------------------------------------------------------------------- #
# Verify & complete
# --------------------------------------------------------------------------- #
def verify_and_complete(
    db: Session,
    order_id: int,
    *,
    razorpay_payment_id: str,
    razorpay_signature: str,
    razorpay_order_id: Optional[str] = None,
) -> Order:
    """Verify the Checkout signature server-side; only then mark PAID and commit inventory."""
    order = get_order(db, order_id)
    if order is None:
        raise OrderError("ORDER_NOT_FOUND", "Order not found.")

    # Idempotent: a already-completed order just returns (no double inventory decrement).
    if order.status in _TERMINAL_PAID_STATES:
        return order

    if razorpay_order_id and razorpay_order_id != order.razorpay_order_id:
        raise OrderError("ORDER_MISMATCH", "Payment does not match this order.")

    ok = razorpay_tools.verify_payment_signature(
        order.razorpay_order_id or "", razorpay_payment_id, razorpay_signature
    )

    payment = _latest_payment(db, order)

    if not ok:
        payment.razorpay_payment_id = razorpay_payment_id
        payment.signature = razorpay_signature
        payment.signature_verified = False
        payment.status = PaymentStatus.FAILED
        order.payment_status = PaymentStatus.FAILED
        order.status = OrderStatus.PAYMENT_VERIFICATION_FAILED
        record_event(
            db,
            event_type=EventType.PAYMENT_FAILED,
            description=f"Signature verification FAILED for order {order.order_number}. Payment rejected.",
            source=EventSource.ERROR,
            order_id=order.id,
            metadata={"razorpay_payment_id": razorpay_payment_id},
            commit=False,
        )
        db.commit()
        raise OrderError("SIGNATURE_VERIFICATION_FAILED", "We could not verify this payment. You have not been charged.")

    # Best-effort amount cross-check (defends against tampering; non-fatal if unreachable).
    fetched = razorpay_tools.fetch_payment(razorpay_payment_id)
    if fetched and isinstance(fetched.get("amount"), int):
        if fetched["amount"] != order.total * 100:
            payment.razorpay_payment_id = razorpay_payment_id
            payment.signature = razorpay_signature
            payment.signature_verified = True
            payment.status = PaymentStatus.FAILED
            order.payment_status = PaymentStatus.FAILED
            order.status = OrderStatus.PAYMENT_VERIFICATION_FAILED
            record_event(
                db,
                event_type=EventType.PAYMENT_FAILED,
                description=f"Amount mismatch on order {order.order_number}: gateway ₹{fetched['amount']//100} vs order ₹{order.total}.",
                source=EventSource.ERROR,
                order_id=order.id,
                metadata={"gateway_amount_paise": fetched["amount"], "order_total": order.total},
                commit=False,
            )
            db.commit()
            raise OrderError("AMOUNT_MISMATCH", "Payment amount did not match the order. You have not been charged.")

    # Verified — record payment, mark PAID.
    payment.razorpay_payment_id = razorpay_payment_id
    payment.signature = razorpay_signature
    payment.signature_verified = True
    payment.status = PaymentStatus.VERIFIED
    payment.amount = order.total
    order.payment_status = PaymentStatus.VERIFIED
    order.status = OrderStatus.PAID

    record_event(
        db,
        event_type=EventType.PAYMENT_VERIFIED,
        description=f"Payment verified for order {order.order_number} (₹{order.total:,}).",
        source=EventSource.PAYMENT,
        order_id=order.id,
        metadata={"razorpay_payment_id": razorpay_payment_id, "razorpay_order_id": order.razorpay_order_id},
        commit=False,
    )

    # Commit inventory exactly once.
    _commit_inventory(db, order)

    # Mark the source cart as ordered so it can't be checked out again.
    if order.cart_id:
        cart = db.get(Cart, order.cart_id)
        if cart is not None and cart.status == CartStatus.ACTIVE:
            cart.status = CartStatus.ORDERED

    order.status = OrderStatus.COMPLETED
    record_event(
        db,
        event_type=EventType.ORDER_COMPLETED,
        description=f"Order {order.order_number} completed. Inventory updated.",
        source=EventSource.ORDER,
        order_id=order.id,
        metadata={"total": order.total, "ai_assisted": order.ai_assisted, "upsell_total": order.upsell_total},
        commit=False,
    )
    db.commit()
    db.refresh(order)
    return order


def _commit_inventory(db: Session, order: Order) -> None:
    if order.inventory_committed:
        return
    for item in order.items:
        product = db.get(Product, item.product_id)
        if product is not None:
            product.stock = max(0, product.stock - item.quantity)
    order.inventory_committed = True


def _latest_payment(db: Session, order: Order) -> Payment:
    if order.payments:
        return order.payments[-1]
    payment = Payment(
        order_id=order.id,
        razorpay_order_id=order.razorpay_order_id,
        status=PaymentStatus.CREATED,
        amount=order.total,
    )
    db.add(payment)
    db.flush()
    return payment


def mark_payment_failed(db: Session, order_id: int, *, reason: str = "Payment was not completed.") -> Order:
    """Record a buyer-cancelled / gateway-failed payment. Never touches inventory; cart stays active for retry."""
    order = get_order(db, order_id)
    if order is None:
        raise OrderError("ORDER_NOT_FOUND", "Order not found.")
    if order.status in _TERMINAL_PAID_STATES:
        return order  # already paid; ignore a late failure signal

    order.status = OrderStatus.PAYMENT_FAILED
    order.payment_status = PaymentStatus.FAILED
    payment = _latest_payment(db, order)
    payment.status = PaymentStatus.FAILED
    record_event(
        db,
        event_type=EventType.PAYMENT_FAILED,
        description=f"Payment not completed for order {order.order_number}: {reason}",
        source=EventSource.PAYMENT,
        order_id=order.id,
        metadata={"reason": reason},
        commit=False,
    )
    db.commit()
    db.refresh(order)
    return order


# --------------------------------------------------------------------------- #
# Serialize
# --------------------------------------------------------------------------- #
def serialize_order(order: Order) -> dict:
    return {
        "id": order.id,
        "order_number": order.order_number,
        "razorpay_order_id": order.razorpay_order_id,
        "status": order.status,
        "payment_status": order.payment_status,
        "subtotal": order.subtotal,
        "discount": order.discount,
        "total": order.total,
        "currency": order.currency,
        "ai_assisted": order.ai_assisted,
        "upsell_total": order.upsell_total,
        "items": [
            {
                "product_id": it.product_id,
                "name": it.product_name,
                "unit_price": it.unit_price,
                "quantity": it.quantity,
                "total": it.total,
                "is_upsell": it.is_upsell,
            }
            for it in order.items
        ],
        "created_at": order.created_at.isoformat() if order.created_at else None,
    }
