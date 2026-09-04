"""Audit trail — append-only, database-backed record of every agent decision.

This is one of the strongest merchant-facing features: every meaningful step in
the commerce flow writes a typed event with a human-readable description and
structured metadata, so a judge can trace *why* the agent did what it did.
"""
from __future__ import annotations

from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import DEMO_MERCHANT_ID, AgentEvent, EventSource


# Canonical event types used across the platform.
class EventType:
    INTENT_PARSED = "INTENT_PARSED"
    PRODUCT_SEARCH = "PRODUCT_SEARCH"
    PRODUCT_RECOMMENDED = "PRODUCT_RECOMMENDED"
    UPSELL_PROPOSED = "UPSELL_PROPOSED"
    UPSELL_ACCEPTED = "UPSELL_ACCEPTED"
    CART_UPDATED = "CART_UPDATED"
    POLICY_CHECK = "POLICY_CHECK"
    ORDER_CREATED = "ORDER_CREATED"
    CHECKOUT_OPENED = "CHECKOUT_OPENED"
    PAYMENT_VERIFIED = "PAYMENT_VERIFIED"
    ORDER_COMPLETED = "ORDER_COMPLETED"
    PAYMENT_FAILED = "PAYMENT_FAILED"
    AGENT_ERROR = "AGENT_ERROR"
    AGENT_TOGGLED = "AGENT_TOGGLED"
    LLM_FALLBACK = "LLM_FALLBACK"


def record_event(
    db: Session,
    *,
    event_type: str,
    description: str,
    source: str = EventSource.SYSTEM,
    order_id: Optional[int] = None,
    cart_id: Optional[int] = None,
    metadata: Optional[dict] = None,
    merchant_id: str = DEMO_MERCHANT_ID,
    commit: bool = True,
) -> AgentEvent:
    """Append an event to the audit trail. Never raises into the caller's flow."""
    event = AgentEvent(
        merchant_id=merchant_id,
        order_id=order_id,
        cart_id=cart_id,
        event_type=event_type,
        description=description,
        source=source,
        event_metadata=metadata or {},
    )
    db.add(event)
    if commit:
        db.commit()
        db.refresh(event)
    else:
        db.flush()
    return event


def get_recent_events(
    db: Session,
    *,
    limit: int = 50,
    source: Optional[str] = None,
    event_type: Optional[str] = None,
    merchant_id: str = DEMO_MERCHANT_ID,
) -> List[AgentEvent]:
    stmt = select(AgentEvent).where(AgentEvent.merchant_id == merchant_id)
    if source:
        stmt = stmt.where(AgentEvent.source == source)
    if event_type:
        stmt = stmt.where(AgentEvent.event_type == event_type)
    stmt = stmt.order_by(AgentEvent.created_at.desc(), AgentEvent.id.desc()).limit(limit)
    return list(db.execute(stmt).scalars().all())
