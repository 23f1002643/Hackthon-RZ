"""Merchant metrics & notifications — all derived from real orders and events.

No fabricated figures: every number here comes from rows the platform actually
wrote. If there is no data yet, values are honest zeros. "Today" is evaluated in
the merchant's local timezone (Asia/Kolkata).
"""
from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from typing import List, Optional
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.orm import Session

from .audit import EventType, get_recent_events
from .models import (
    DEMO_MERCHANT_ID,
    AgentEvent,
    EventSource,
    Order,
    OrderStatus,
    Payment,
    PaymentStatus,
)

IST = ZoneInfo("Asia/Kolkata")
_PAID_STATES = (OrderStatus.PAID, OrderStatus.COMPLETED)
_CHART_SLOTS = ["00:00", "03:00", "06:00", "09:00", "12:00", "15:00", "18:00", "21:00"]


def _ist(dt: Optional[datetime]) -> Optional[datetime]:
    """Interpret a stored (naive UTC) timestamp in IST."""
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(IST)


def _paid_orders(db: Session, merchant_id: str) -> List[Order]:
    return list(
        db.execute(
            select(Order).where(Order.merchant_id == merchant_id, Order.status.in_(_PAID_STATES))
        ).scalars().all()
    )


def _pct(part: int, whole: int) -> float:
    return round(part / whole * 100, 1) if whole else 0.0


def compute_metrics(db: Session, merchant_id: str = DEMO_MERCHANT_ID) -> dict:
    today = datetime.now(IST).date()

    paid = _paid_orders(db, merchant_id)
    paid_today = [o for o in paid if (_ist(o.created_at) or datetime.now(IST)).date() == today]

    revenue_today = sum(o.total for o in paid_today)
    revenue_all = sum(o.total for o in paid)
    orders_today = len(paid_today)

    ai_orders_today = [o for o in paid_today if o.ai_assisted]
    ai_revenue_today = sum(o.total for o in ai_orders_today)
    upsell_revenue_today = sum(o.upsell_total for o in paid_today)

    aov_today = round(revenue_today / orders_today) if orders_today else 0

    # Upsell funnel from the audit trail (proposed vs accepted).
    events = get_recent_events(db, limit=1000, merchant_id=merchant_id)
    proposed = sum(1 for e in events if e.event_type == EventType.UPSELL_PROPOSED)
    accepted = sum(1 for e in events if e.event_type == EventType.UPSELL_ACCEPTED)
    agent_actions = sum(1 for e in events if e.source == EventSource.AI)

    # Payment success rate from payment attempts.
    payments = list(db.execute(select(Payment).where(Payment.order_id.isnot(None))).scalars().all())
    verified = sum(1 for p in payments if p.status == PaymentStatus.VERIFIED)
    failed = sum(1 for p in payments if p.status == PaymentStatus.FAILED)

    return {
        "revenue_today": revenue_today,
        "revenue_all_time": revenue_all,
        "orders_today": orders_today,
        "ai_assisted_orders_today": len(ai_orders_today),
        "ai_assisted_revenue_today": ai_revenue_today,
        "ai_assisted_share": _pct(len(ai_orders_today), orders_today),
        "aov_today": aov_today,
        "upsell_revenue_today": upsell_revenue_today,
        "upsell_proposed": proposed,
        "upsell_accepted": accepted,
        "upsell_conversion": _pct(accepted, proposed),
        "payment_success_rate": _pct(verified, verified + failed),
        "payments_verified": verified,
        "payments_failed": failed,
        "agent_actions": agent_actions,
        "currency": "INR",
    }


def revenue_timeseries(db: Session, merchant_id: str = DEMO_MERCHANT_ID) -> List[dict]:
    """Real hourly revenue for today and yesterday, bucketed into 3-hour slots (IST)."""
    today = datetime.now(IST).date()
    yesterday = today - timedelta(days=1)

    buckets: dict[date, dict[str, int]] = {today: defaultdict(int), yesterday: defaultdict(int)}
    for order in _paid_orders(db, merchant_id):
        local = _ist(order.created_at)
        if local is None:
            continue
        d = local.date()
        if d in buckets:
            slot = f"{(local.hour // 3) * 3:02d}:00"
            buckets[d][slot] += order.total

    return [
        {
            "hour": slot,
            "today": buckets[today].get(slot, 0),
            "yesterday": buckets[yesterday].get(slot, 0),
        }
        for slot in _CHART_SLOTS
    ]


_NOTIFY_TITLES = {
    EventType.ORDER_COMPLETED: "Order completed",
    EventType.PAYMENT_VERIFIED: "Payment verified",
    EventType.PAYMENT_FAILED: "Payment failed",
    EventType.UPSELL_ACCEPTED: "Upsell accepted",
    EventType.ORDER_CREATED: "New order",
}


def recent_notifications(db: Session, *, limit: int = 8, merchant_id: str = DEMO_MERCHANT_ID) -> List[dict]:
    """Surface notable real events as notifications for the merchant UI."""
    events = get_recent_events(db, limit=200, merchant_id=merchant_id)
    notifs = []
    for e in events:
        if e.event_type not in _NOTIFY_TITLES:
            continue
        notifs.append(
            {
                "id": e.id,
                "title": _NOTIFY_TITLES[e.event_type],
                "description": e.description,
                "type": "error" if e.source == EventSource.ERROR else "success",
                "timestamp": e.to_dict()["timestamp"],
            }
        )
        if len(notifs) >= limit:
            break
    return notifs
