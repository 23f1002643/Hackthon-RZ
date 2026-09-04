"""Policy engine — the deterministic money-safety layer."""
from backend import policy
from backend.models import MerchantConfig


def _cfg(**over) -> MerchantConfig:
    base = dict(
        merchant_id="test",
        max_order_value=10000,
        max_upsell_value=1500,
        max_discount_pct=20,
        require_user_confirmation=True,
        agent_active=True,
        currency="INR",
    )
    base.update(over)
    return MerchantConfig(**base)


def test_order_requires_confirmation():
    res = policy.check_order(_cfg(), subtotal=3098, discount=0, total=3098, budget=4000, confirmed=False)
    assert not res.allowed
    assert res.code == "CONFIRMATION_REQUIRED"


def test_order_ok_when_confirmed_and_within_limits():
    res = policy.check_order(_cfg(), subtotal=3098, discount=0, total=3098, budget=4000, confirmed=True)
    assert res.allowed
    assert res.code == "OK"


def test_order_blocks_over_merchant_limit():
    res = policy.check_order(_cfg(), subtotal=20000, discount=0, total=20000, budget=None, confirmed=True)
    assert not res.allowed
    assert res.code == "MAX_ORDER_VALUE_EXCEEDED"


def test_order_blocks_over_budget():
    res = policy.check_order(_cfg(), subtotal=5000, discount=0, total=5000, budget=4000, confirmed=True)
    assert not res.allowed
    assert res.code == "OVER_BUDGET"


def test_empty_cart_blocked():
    res = policy.check_order(_cfg(), subtotal=0, discount=0, total=0, confirmed=True)
    assert not res.allowed
    assert res.code == "EMPTY_CART"


def test_discount_cap_enforced():
    res = policy.check_order(_cfg(), subtotal=1000, discount=300, total=700, confirmed=True)
    assert not res.allowed
    assert res.code == "MAX_DISCOUNT_EXCEEDED"


def test_upsell_value_cap():
    res = policy.check_upsell(_cfg(), upsell_price=2000, remaining_budget=None)
    assert not res.allowed
    assert res.code == "MAX_UPSELL_EXCEEDED"


def test_upsell_over_remaining_budget():
    res = policy.check_upsell(_cfg(), upsell_price=900, remaining_budget=500)
    assert not res.allowed
    assert res.code == "UPSELL_OVER_BUDGET"


def test_upsell_ok():
    res = policy.check_upsell(_cfg(), upsell_price=599, remaining_budget=1501)
    assert res.allowed
