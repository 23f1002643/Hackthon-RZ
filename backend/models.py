"""SQLAlchemy ORM models for the commerce platform.

Money is stored as **integer rupees** everywhere in the database. Conversion to
paise (the unit Razorpay expects) happens only at the Razorpay boundary in
``razorpay_tools.py``. This avoids floating-point drift on totals.

Status values are plain strings backed by the constants below rather than DB
enums, which keeps SQLite migrations trivial while still giving callers a single
source of truth to import from.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    JSON,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base

DEMO_MERCHANT_ID = "vastra_studio"


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


# --------------------------------------------------------------------------- #
# Status constants — the order/payment state machine
# --------------------------------------------------------------------------- #
class OrderStatus:
    CART = "CART"
    ORDER_CREATED = "ORDER_CREATED"
    PAYMENT_PENDING = "PAYMENT_PENDING"
    PAID = "PAID"
    COMPLETED = "COMPLETED"
    PAYMENT_FAILED = "PAYMENT_FAILED"
    PAYMENT_VERIFICATION_FAILED = "PAYMENT_VERIFICATION_FAILED"
    CANCELLED = "CANCELLED"


class PaymentStatus:
    CREATED = "CREATED"
    PENDING = "PENDING"
    VERIFIED = "VERIFIED"
    FAILED = "FAILED"


class CartStatus:
    ACTIVE = "ACTIVE"
    ORDERED = "ORDERED"
    ABANDONED = "ABANDONED"


class RelationType:
    ACCESSORY = "accessory"
    COMPLEMENT = "complement"
    ALTERNATIVE = "alternative"
    FREQUENTLY_BOUGHT_TOGETHER = "frequently_bought_together"


# Audit event sources — drive the coloured badges in the merchant UI.
class EventSource:
    AI = "AI"
    USER = "USER"
    POLICY = "POLICY"
    ORDER = "ORDER"
    PAYMENT = "PAYMENT"
    ERROR = "ERROR"
    SYSTEM = "SYSTEM"


# --------------------------------------------------------------------------- #
# Catalog
# --------------------------------------------------------------------------- #
class Product(Base):
    __tablename__ = "products"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    merchant_id: Mapped[str] = mapped_column(String(64), default=DEMO_MERCHANT_ID, index=True)
    name: Mapped[str] = mapped_column(String(200), index=True)
    description: Mapped[str] = mapped_column(Text, default="")
    category: Mapped[str] = mapped_column(String(64), index=True)
    subcategory: Mapped[str] = mapped_column(String(64), default="")
    brand: Mapped[str] = mapped_column(String(96), default="")
    price: Mapped[int] = mapped_column(Integer)  # integer rupees
    currency: Mapped[str] = mapped_column(String(8), default="INR")
    stock: Mapped[int] = mapped_column(Integer, default=0)
    image_url: Mapped[str] = mapped_column(Text, default="")
    rating: Mapped[float] = mapped_column(Float, default=4.5)
    tags: Mapped[list] = mapped_column(JSON, default=list)  # list[str]
    occasion: Mapped[list] = mapped_column(JSON, default=list)  # list[str]
    gender: Mapped[str] = mapped_column(String(16), default="unisex")
    active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    source: Mapped[str] = mapped_column(String(32), default="seed")
    source_url: Mapped[str] = mapped_column(Text, default="")
    external_product_id: Mapped[Optional[str]] = mapped_column(String(160), nullable=True, index=True)
    reviews_count: Mapped[int] = mapped_column(Integer, default=0)
    color: Mapped[str] = mapped_column(String(64), default="")
    material: Mapped[str] = mapped_column(String(96), default="")
    style: Mapped[str] = mapped_column(String(96), default="")
    season: Mapped[str] = mapped_column(String(64), default="")
    imported_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow, onupdate=_utcnow)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "category": self.category,
            "subcategory": self.subcategory,
            "brand": self.brand,
            "price": self.price,
            "currency": self.currency,
            "stock": self.stock,
            "in_stock": self.stock > 0,
            "image_url": self.image_url,
            "rating": self.rating,
            "tags": self.tags or [],
            "occasion": self.occasion or [],
            "gender": self.gender,
            "source": self.source,
            "source_url": self.source_url,
            "reviews_count": self.reviews_count,
            "color": self.color,
            "material": self.material,
            "style": self.style,
            "season": self.season,
        }


class ProductRelation(Base):
    __tablename__ = "product_relations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), index=True)
    related_product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), index=True)
    relation_type: Mapped[str] = mapped_column(String(48), default=RelationType.COMPLEMENT)
    priority: Mapped[int] = mapped_column(Integer, default=100)


# --------------------------------------------------------------------------- #
# Customers
# --------------------------------------------------------------------------- #
class Customer(Base):
    __tablename__ = "customers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    merchant_id: Mapped[str] = mapped_column(String(64), default=DEMO_MERCHANT_ID, index=True)
    name: Mapped[str] = mapped_column(String(160), default="Guest")
    email: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    contact: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    razorpay_customer_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)

    def to_dict(self) -> dict:
        return {"id": self.id, "name": self.name, "email": self.email, "contact": self.contact, "created_at": self.created_at.isoformat() if self.created_at else None}


# --------------------------------------------------------------------------- #
# Cart
# --------------------------------------------------------------------------- #
class Cart(Base):
    __tablename__ = "carts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    merchant_id: Mapped[str] = mapped_column(String(64), default=DEMO_MERCHANT_ID, index=True)
    customer_id: Mapped[Optional[int]] = mapped_column(ForeignKey("customers.id"), nullable=True)
    status: Mapped[str] = mapped_column(String(24), default=CartStatus.ACTIVE, index=True)
    budget: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # integer rupees, from AI intent
    ai_assisted: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow, onupdate=_utcnow)

    items: Mapped[list["CartItem"]] = relationship(
        back_populates="cart", cascade="all, delete-orphan", order_by="CartItem.id"
    )
    customer: Mapped[Optional["Customer"]] = relationship()


class CartItem(Base):
    __tablename__ = "cart_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    cart_id: Mapped[int] = mapped_column(ForeignKey("carts.id"), index=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), index=True)
    product_name: Mapped[str] = mapped_column(String(200))
    unit_price: Mapped[int] = mapped_column(Integer)  # integer rupees, snapshot at add time
    quantity: Mapped[int] = mapped_column(Integer, default=1)
    is_upsell: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)

    cart: Mapped["Cart"] = relationship(back_populates="items")

    @property
    def line_total(self) -> int:
        return int(self.unit_price) * int(self.quantity)


# --------------------------------------------------------------------------- #
# Orders & payments
# --------------------------------------------------------------------------- #
class Order(Base):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    order_number: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    merchant_id: Mapped[str] = mapped_column(String(64), default=DEMO_MERCHANT_ID, index=True)
    customer_id: Mapped[Optional[int]] = mapped_column(ForeignKey("customers.id"), nullable=True)
    cart_id: Mapped[Optional[int]] = mapped_column(ForeignKey("carts.id"), nullable=True)
    razorpay_order_id: Mapped[Optional[str]] = mapped_column(String(64), index=True, nullable=True)
    subtotal: Mapped[int] = mapped_column(Integer, default=0)
    discount: Mapped[int] = mapped_column(Integer, default=0)
    total: Mapped[int] = mapped_column(Integer, default=0)
    currency: Mapped[str] = mapped_column(String(8), default="INR")
    status: Mapped[str] = mapped_column(String(40), default=OrderStatus.ORDER_CREATED, index=True)
    payment_status: Mapped[str] = mapped_column(String(24), default=PaymentStatus.CREATED)
    ai_assisted: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    upsell_total: Mapped[int] = mapped_column(Integer, default=0)  # revenue attributable to accepted upsells
    inventory_committed: Mapped[bool] = mapped_column(Boolean, default=False)  # guards against double-decrement
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow, index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow, onupdate=_utcnow)

    items: Mapped[list["OrderItem"]] = relationship(
        back_populates="order", cascade="all, delete-orphan", order_by="OrderItem.id"
    )
    customer: Mapped[Optional["Customer"]] = relationship()
    payments: Mapped[list["Payment"]] = relationship(
        back_populates="order", cascade="all, delete-orphan", order_by="Payment.id"
    )


class OrderItem(Base):
    __tablename__ = "order_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id"), index=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"))
    product_name: Mapped[str] = mapped_column(String(200))
    unit_price: Mapped[int] = mapped_column(Integer)
    quantity: Mapped[int] = mapped_column(Integer, default=1)
    total: Mapped[int] = mapped_column(Integer, default=0)
    is_upsell: Mapped[bool] = mapped_column(Boolean, default=False)

    order: Mapped["Order"] = relationship(back_populates="items")


class Payment(Base):
    __tablename__ = "payments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id"), index=True)
    razorpay_payment_id: Mapped[Optional[str]] = mapped_column(String(64), index=True, nullable=True)
    razorpay_order_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    signature: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    signature_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    status: Mapped[str] = mapped_column(String(24), default=PaymentStatus.CREATED)
    amount: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)

    order: Mapped["Order"] = relationship(back_populates="payments")


# --------------------------------------------------------------------------- #
# Agent events (audit trail) & merchant config
# --------------------------------------------------------------------------- #
class AgentEvent(Base):
    __tablename__ = "agent_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    merchant_id: Mapped[str] = mapped_column(String(64), default=DEMO_MERCHANT_ID, index=True)
    order_id: Mapped[Optional[int]] = mapped_column(ForeignKey("orders.id"), nullable=True, index=True)
    cart_id: Mapped[Optional[int]] = mapped_column(ForeignKey("carts.id"), nullable=True)
    event_type: Mapped[str] = mapped_column(String(48), index=True)
    description: Mapped[str] = mapped_column(Text, default="")
    source: Mapped[str] = mapped_column(String(16), default=EventSource.SYSTEM, index=True)
    event_metadata: Mapped[dict] = mapped_column("metadata", JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow, index=True)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "event_type": self.event_type,
            "description": self.description,
            "source": self.source,
            "order_id": self.order_id,
            "metadata": self.event_metadata or {},
            "timestamp": self.created_at.replace(tzinfo=timezone.utc).isoformat()
            if self.created_at and self.created_at.tzinfo is None
            else (self.created_at.isoformat() if self.created_at else ""),
        }


class MerchantConfig(Base):
    __tablename__ = "merchant_config"

    merchant_id: Mapped[str] = mapped_column(String(64), primary_key=True, default=DEMO_MERCHANT_ID)
    name: Mapped[str] = mapped_column(String(120), default="Vastra Studio")
    max_order_value: Mapped[int] = mapped_column(Integer, default=10000)  # integer rupees
    max_upsell_value: Mapped[int] = mapped_column(Integer, default=1500)
    max_discount_pct: Mapped[int] = mapped_column(Integer, default=20)
    require_user_confirmation: Mapped[bool] = mapped_column(Boolean, default=True)
    agent_active: Mapped[bool] = mapped_column(Boolean, default=True)
    currency: Mapped[str] = mapped_column(String(8), default="INR")
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow, onupdate=_utcnow)

    def to_dict(self) -> dict:
        return {
            "merchant_id": self.merchant_id,
            "name": self.name,
            "max_order_value": self.max_order_value,
            "max_upsell_value": self.max_upsell_value,
            "max_discount_pct": self.max_discount_pct,
            "require_user_confirmation": self.require_user_confirmation,
            "agent_active": self.agent_active,
            "currency": self.currency,
        }
