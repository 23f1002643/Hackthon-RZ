"""Deterministic policy engine — the safety layer for all money actions.

Every financial decision (order total, discount, upsell, budget, confirmation)
passes through here. The LLM cannot bypass these checks; it only proposes, the
policy engine disposes. Values are integer rupees.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from .models import MerchantConfig


@dataclass
class PolicyResult:
    allowed: bool
    code: str = "OK"
    message: str = "Within policy."
    details: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {"allowed": self.allowed, "code": self.code, "message": self.message, "details": self.details}


def check_order(
    config: MerchantConfig,
    *,
    subtotal: int,
    discount: int,
    total: int,
    budget: Optional[int] = None,
    confirmed: bool = False,
) -> PolicyResult:
    """Validate a would-be order against merchant guardrails and the buyer budget."""
    if total <= 0:
        return PolicyResult(False, "EMPTY_CART", "Your cart is empty.")

    if total > config.max_order_value:
        return PolicyResult(
            False,
            "MAX_ORDER_VALUE_EXCEEDED",
            f"Order total ₹{total:,} exceeds the merchant limit of ₹{config.max_order_value:,}.",
            {"total": total, "limit": config.max_order_value},
        )

    if subtotal > 0:
        discount_pct = round(discount / subtotal * 100, 2)
        if discount_pct > config.max_discount_pct:
            return PolicyResult(
                False,
                "MAX_DISCOUNT_EXCEEDED",
                f"Discount {discount_pct}% exceeds the maximum {config.max_discount_pct}%.",
                {"discount_pct": discount_pct, "limit": config.max_discount_pct},
            )

    if budget is not None and total > budget:
        return PolicyResult(
            False,
            "OVER_BUDGET",
            f"Total ₹{total:,} is over your budget of ₹{budget:,}.",
            {"total": total, "budget": budget},
        )

    if config.require_user_confirmation and not confirmed:
        return PolicyResult(
            False,
            "CONFIRMATION_REQUIRED",
            "Explicit buyer confirmation is required before payment.",
            {"require_user_confirmation": True},
        )

    return PolicyResult(True, "OK", "Order is within policy.", {"total": total})


def check_upsell(
    config: MerchantConfig,
    *,
    upsell_price: int,
    remaining_budget: Optional[int] = None,
) -> PolicyResult:
    """Decide whether a proposed upsell item is allowed (value cap + budget headroom)."""
    if upsell_price <= 0:
        return PolicyResult(False, "INVALID_UPSELL", "Upsell has no price.")

    if upsell_price > config.max_upsell_value:
        return PolicyResult(
            False,
            "MAX_UPSELL_EXCEEDED",
            f"Upsell ₹{upsell_price:,} exceeds the max upsell value ₹{config.max_upsell_value:,}.",
            {"upsell_price": upsell_price, "limit": config.max_upsell_value},
        )

    if remaining_budget is not None and upsell_price > remaining_budget:
        return PolicyResult(
            False,
            "UPSELL_OVER_BUDGET",
            f"Upsell ₹{upsell_price:,} would exceed the remaining budget of ₹{remaining_budget:,}.",
            {"upsell_price": upsell_price, "remaining_budget": remaining_budget},
        )

    return PolicyResult(True, "OK", "Upsell is within policy.", {"upsell_price": upsell_price})
