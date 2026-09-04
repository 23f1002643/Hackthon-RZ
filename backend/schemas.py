"""Pydantic request models for the API. Responses are assembled as plain dicts by
the service layer (cart_service / orders / metrics), so these focus on validating
and constraining what the client is allowed to send.

Note the deliberate omissions: the client never sends prices, amounts or totals.
It sends ids and intent; the backend computes money.
"""
from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class ShopSearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=500)


class CreateCartRequest(BaseModel):
    budget: Optional[int] = Field(default=None, ge=0, le=1_000_000)
    ai_assisted: bool = False
    customer_id: Optional[int] = Field(default=None, ge=1)


class AddItemRequest(BaseModel):
    product_id: int
    quantity: int = Field(default=1, ge=1, le=20)
    is_upsell: bool = False


class UpdateItemRequest(BaseModel):
    quantity: int = Field(ge=0, le=20)


class CustomerIn(BaseModel):
    name: Optional[str] = Field(default=None, max_length=160)
    email: Optional[str] = Field(default=None, max_length=200)
    contact: Optional[str] = Field(default=None, max_length=32)


class ProductIn(BaseModel):
    name: str = Field(min_length=2, max_length=200)
    description: str = Field(default="", max_length=4000)
    category: str = Field(min_length=2, max_length=64)
    subcategory: str = Field(default="", max_length=64)
    brand: str = Field(default="", max_length=96)
    price: int = Field(ge=0, le=10_000_000)
    currency: str = Field(default="INR", min_length=3, max_length=8)
    stock: int = Field(default=0, ge=0, le=1_000_000)
    image_url: str = Field(default="", max_length=2000)
    rating: float = Field(default=0, ge=0, le=5)
    tags: list[str] = Field(default_factory=list, max_length=30)
    occasion: list[str] = Field(default_factory=list, max_length=20)
    gender: str = Field(default="unisex", max_length=16)
    source_url: str = Field(default="", max_length=2000)
    active: bool = True


class CustomerRequest(CustomerIn):
    pass


class CreateOrderRequest(BaseModel):
    cart_id: int
    confirmed: bool = False
    customer: Optional[CustomerIn] = None
    customer_id: Optional[int] = Field(default=None, ge=1)


class VerifyPaymentRequest(BaseModel):
    order_id: int
    razorpay_payment_id: str = Field(min_length=1, max_length=64)
    razorpay_order_id: str = Field(min_length=1, max_length=64)
    razorpay_signature: str = Field(min_length=1, max_length=256)


class PaymentFailedRequest(BaseModel):
    order_id: int
    reason: Optional[str] = Field(default=None, max_length=300)


class AgentToggleRequest(BaseModel):
    active: bool


class PolicyUpdateRequest(BaseModel):
    max_order_value: Optional[int] = Field(default=None, ge=0, le=10_000_000)
    max_upsell_value: Optional[int] = Field(default=None, ge=0, le=10_000_000)
    max_discount_pct: Optional[int] = Field(default=None, ge=0, le=100)
    require_user_confirmation: Optional[bool] = None
