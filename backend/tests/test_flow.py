"""End-to-end agentic journey: discovery -> cart -> order -> payment verification.

Razorpay is mocked at the module boundary so the money path is exercised without
network calls. Everything else (agent, policy, cart, orders, inventory) is real.
"""
import pytest

from backend import agent, cart_service, orders, razorpay_tools
from backend.models import CartStatus, OrderStatus, PaymentStatus


@pytest.fixture()
def fake_razorpay(monkeypatch):
    """Deterministic Razorpay stand-in. ``signature == "valid"`` verifies."""
    monkeypatch.setattr(
        razorpay_tools, "create_order",
        lambda amount_rupees, *, receipt, notes=None, currency="INR": {
            "id": f"order_TEST_{receipt}", "amount": amount_rupees * 100, "currency": currency,
        },
    )
    monkeypatch.setattr(
        razorpay_tools, "verify_payment_signature",
        lambda order_id, payment_id, signature: signature == "valid",
    )
    monkeypatch.setattr(razorpay_tools, "fetch_payment", lambda payment_id: None)
    return razorpay_tools


def test_discovery_recommends_saree_with_earrings_upsell(db, config):
    result = agent.run_discovery(db, "I need something for my sister's wedding under ₹4000", config)

    assert result["recommendation"] is not None
    assert result["recommendation"]["product"]["name"] == "Banarasi Silk Saree"

    assert result["upsell"] is not None
    assert result["upsell"]["product"]["name"] == "Pearl Drop Earrings"
    assert 1 <= len(result["upsell_options"]) <= 3
    assert result["upsell_options"][0]["product"]["name"] == "Pearl Drop Earrings"

    saree = result["recommendation"]["product"]["price"]
    earrings = result["upsell"]["product"]["price"]
    assert saree + earrings == 3098  # within the ₹4000 budget


def test_greeting_does_not_recommend_a_product(db, config):
    result = agent.run_discovery(db, "Hi", config)

    assert result["intent"]["intent"] == "greeting"
    assert result["recommendation"] is None
    assert result["upsell_options"] == []


def test_full_paid_flow_decrements_inventory(db, config, fake_razorpay, find_product):
    saree = find_product("Banarasi Silk Saree")
    earrings = find_product("Pearl Drop Earrings")
    saree_stock, earrings_stock = saree.stock, earrings.stock

    cart = cart_service.create_cart(db, budget=4000, ai_assisted=True)
    cart_service.add_item(db, cart.id, saree.id, quantity=1)
    cart_service.add_item(db, cart.id, earrings.id, quantity=1, is_upsell=True)

    serialized = cart_service.serialize_cart(cart_service.get_cart(db, cart.id))
    assert serialized["total"] == 3098
    assert serialized["upsell_total"] == 599
    assert serialized["over_budget"] is False

    order = orders.create_order(db, cart.id, config, confirmed=True)
    assert order.total == 3098
    assert order.status == OrderStatus.ORDER_CREATED
    assert order.razorpay_order_id.startswith("order_TEST_")

    done = orders.verify_and_complete(
        db, order.id, razorpay_payment_id="pay_TEST123", razorpay_order_id=order.razorpay_order_id,
        razorpay_signature="valid",
    )
    assert done.status == OrderStatus.COMPLETED
    assert done.payment_status == PaymentStatus.VERIFIED
    assert done.payments[-1].signature_verified is True

    db.refresh(saree)
    db.refresh(earrings)
    assert saree.stock == saree_stock - 1
    assert earrings.stock == earrings_stock - 1

    assert cart_service.get_cart(db, cart.id).status == CartStatus.ORDERED


def test_idempotent_verify_does_not_double_decrement(db, config, fake_razorpay, find_product):
    saree = find_product("Kanjivaram Silk Saree")
    start = saree.stock

    cart = cart_service.create_cart(db, budget=5000)
    cart_service.add_item(db, cart.id, saree.id, quantity=1)
    order = orders.create_order(db, cart.id, config, confirmed=True)

    orders.verify_and_complete(db, order.id, razorpay_payment_id="pay_A", razorpay_order_id=order.razorpay_order_id, razorpay_signature="valid")
    orders.verify_and_complete(db, order.id, razorpay_payment_id="pay_A", razorpay_order_id=order.razorpay_order_id, razorpay_signature="valid")

    db.refresh(saree)
    assert saree.stock == start - 1  # decremented exactly once


def test_bad_signature_never_marks_paid(db, config, fake_razorpay, find_product):
    product = find_product("Chanderi Cotton Saree")
    start = product.stock

    cart = cart_service.create_cart(db, budget=5000)
    cart_service.add_item(db, cart.id, product.id, quantity=1)
    order = orders.create_order(db, cart.id, config, confirmed=True)

    with pytest.raises(orders.OrderError) as exc:
        orders.verify_and_complete(
            db, order.id, razorpay_payment_id="pay_bad", razorpay_order_id=order.razorpay_order_id,
            razorpay_signature="forged",
        )
    assert exc.value.code == "SIGNATURE_VERIFICATION_FAILED"

    db.refresh(order)
    db.refresh(product)
    assert order.status == OrderStatus.PAYMENT_VERIFICATION_FAILED
    assert order.payment_status == PaymentStatus.FAILED
    assert product.stock == start  # inventory untouched on failure


def test_confirmation_required_blocks_order(db, config, find_product):
    product = find_product("Linen Handloom Saree")
    cart = cart_service.create_cart(db, budget=5000)
    cart_service.add_item(db, cart.id, product.id, quantity=1)

    with pytest.raises(orders.OrderError) as exc:
        orders.create_order(db, cart.id, config, confirmed=False)
    assert exc.value.code == "CONFIRMATION_REQUIRED"
