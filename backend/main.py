"""FastAPI application for the Vastra Studio commerce agent.

Two experiences share this API:
  * Buyer  (/shop)      — natural-language discovery, AI recommendation + upsell,
                          server-side cart, real Razorpay Test Mode checkout.
  * Merchant (/dashboard) — real metrics, audit trail, agent + policy controls.

Design rules enforced here:
  * Every response uses a structured envelope: success -> {"success": true, ...};
    error -> {"success": false, "error": {code, message, details}}.
  * The client sends ids and intent, never prices or amounts.
  * Auth is intentionally simplified for the demo (no login) — see README.

Run:  uvicorn backend.main:app --reload --port 8000
"""
from __future__ import annotations

from typing import Optional

from fastapi import Depends, FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from . import agent, cart_service, catalog, llm, metrics, orders, razorpay_tools
from .audit import EventType, get_recent_events, record_event
from .cart_service import CartError
from .db import get_db, init_db
from .models import DEMO_MERCHANT_ID, EventSource, MerchantConfig
from .orders import OrderError
from .schemas import (
    AddItemRequest,
    AgentToggleRequest,
    CreateCartRequest,
    CreateOrderRequest,
    PaymentFailedRequest,
    PolicyUpdateRequest,
    ShopSearchRequest,
    UpdateItemRequest,
    VerifyPaymentRequest,
)
from .seed import reset_and_seed, seed_all

app = FastAPI(title="Vastra Studio — Commerce Agent", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:5173",
        "http://localhost:8080",
        "http://localhost:8081",
        "http://localhost:4173",
        "http://127.0.0.1:8080",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --------------------------------------------------------------------------- #
# Response envelope helpers
# --------------------------------------------------------------------------- #
def ok(data: Optional[dict] = None) -> dict:
    return {"success": True, **(data or {})}


def _error_response(code: str, message: str, *, status: int = 400, details: Optional[dict] = None) -> JSONResponse:
    return JSONResponse(
        status_code=status,
        content={"success": False, "error": {"code": code, "message": message, "details": details or {}}},
    )


def _status_for(code: str) -> int:
    if code.endswith("NOT_FOUND"):
        return 404
    if code in {"SIGNATURE_VERIFICATION_FAILED", "AMOUNT_MISMATCH", "ORDER_MISMATCH"}:
        return 400
    if code == "PAYMENT_GATEWAY_UNAVAILABLE":
        return 502
    return 400


@app.exception_handler(OrderError)
async def _order_error_handler(_: Request, exc: OrderError) -> JSONResponse:
    return _error_response(exc.code, exc.message, status=_status_for(exc.code), details=exc.details)


@app.exception_handler(CartError)
async def _cart_error_handler(_: Request, exc: CartError) -> JSONResponse:
    return _error_response(exc.code, exc.message, status=_status_for(exc.code))


@app.exception_handler(RequestValidationError)
async def _validation_handler(_: Request, exc: RequestValidationError) -> JSONResponse:
    return _error_response("VALIDATION_ERROR", "Request could not be validated.", status=422, details={"errors": exc.errors()[:5]})


@app.exception_handler(Exception)
async def _unhandled_handler(_: Request, exc: Exception) -> JSONResponse:
    # Never leak internals to the client.
    return _error_response("INTERNAL_ERROR", "Something went wrong. Please try again.", status=500)


# --------------------------------------------------------------------------- #
# Startup
# --------------------------------------------------------------------------- #
@app.on_event("startup")
def _startup() -> None:
    init_db()
    seed_all()


def _config(db: Session) -> MerchantConfig:
    config = db.get(MerchantConfig, DEMO_MERCHANT_ID)
    if config is None:  # defensive; startup seeds it
        seed_all()
        config = db.get(MerchantConfig, DEMO_MERCHANT_ID)
    return config


# --------------------------------------------------------------------------- #
# Health & config
# --------------------------------------------------------------------------- #
@app.get("/")
async def root():
    return ok({"service": "vastra-studio-commerce-agent", "status": "ready"})


@app.get("/api/config")
async def get_config(db: Session = Depends(get_db)):
    config = _config(db)
    return ok(
        {
            "merchant": config.to_dict(),
            "capabilities": {
                "razorpay_enabled": razorpay_tools.razorpay_enabled(),
                "razorpay_key_id": razorpay_tools.get_key_id(),  # public key id only
                "llm_available": llm.llm_available(),
                "agent_backend": agent.graph_backend(),
            },
        }
    )


@app.post("/api/agent/toggle")
async def toggle_agent(payload: AgentToggleRequest, db: Session = Depends(get_db)):
    config = _config(db)
    config.agent_active = payload.active
    record_event(
        db,
        event_type=EventType.AGENT_TOGGLED,
        description=f"Agent {'resumed' if payload.active else 'paused'} by merchant.",
        source=EventSource.SYSTEM,
        metadata={"active": payload.active},
    )
    return ok({"merchant": config.to_dict()})


@app.post("/api/config/policy")
async def update_policy(payload: PolicyUpdateRequest, db: Session = Depends(get_db)):
    config = _config(db)
    if payload.max_order_value is not None:
        config.max_order_value = payload.max_order_value
    if payload.max_upsell_value is not None:
        config.max_upsell_value = payload.max_upsell_value
    if payload.max_discount_pct is not None:
        config.max_discount_pct = payload.max_discount_pct
    if payload.require_user_confirmation is not None:
        config.require_user_confirmation = payload.require_user_confirmation
    db.commit()
    record_event(
        db,
        event_type=EventType.POLICY_CHECK,
        description="Merchant updated policy guardrails.",
        source=EventSource.POLICY,
        metadata=config.to_dict(),
    )
    return ok({"merchant": config.to_dict()})


# --------------------------------------------------------------------------- #
# Catalog & discovery
# --------------------------------------------------------------------------- #
@app.get("/api/products")
async def list_products(
    q: str = "",
    category: Optional[str] = None,
    occasion: Optional[str] = None,
    limit: int = 24,
    db: Session = Depends(get_db),
):
    products = catalog.search_products(
        db, query=q, category=category, occasion=occasion, in_stock_only=False, limit=min(max(limit, 1), 100)
    )
    return ok({"products": [p.to_dict() for p in products]})


@app.get("/api/products/{product_id}")
async def get_product(product_id: int, db: Session = Depends(get_db)):
    product = catalog.get_product(db, product_id)
    if product is None:
        return _error_response("PRODUCT_NOT_FOUND", "Product not found.", status=404)
    related = catalog.get_related_products(db, product_id, limit=6)
    return ok({"product": product.to_dict(), "related": [p.to_dict() for p in related]})


@app.get("/api/categories")
async def get_categories(db: Session = Depends(get_db)):
    return ok({"categories": catalog.list_categories(db)})


@app.post("/api/shop/search")
async def shop_search(payload: ShopSearchRequest, db: Session = Depends(get_db)):
    config = _config(db)

    # Merchant paused the agent -> deterministic catalog browse only (no AI reasoning/upsell).
    if not config.agent_active:
        intent = llm._deterministic_intent(payload.query)
        products = catalog.search_products(
            db,
            query=payload.query,
            category=intent.get("category"),
            occasion=intent.get("occasion"),
            max_price=intent.get("budget"),
            gender=intent.get("gender"),
            limit=agent.CANDIDATE_LIMIT,
        )
        return ok(
            {
                "agent_active": False,
                "intent": {k: intent.get(k) for k in ("occasion", "recipient", "category", "budget", "gender")},
                "products": [p.to_dict() for p in products],
                "recommendation": None,
                "upsell": None,
                "steps": [{"key": "catalog", "label": "Browsing catalog (agent paused)", "status": "done"}],
                "backend": "paused",
            }
        )

    result = agent.run_discovery(db, payload.query, config)
    result["agent_active"] = True
    return ok(result)


# --------------------------------------------------------------------------- #
# Cart
# --------------------------------------------------------------------------- #
@app.post("/api/cart")
async def create_cart(payload: CreateCartRequest, db: Session = Depends(get_db)):
    cart = cart_service.create_cart(db, budget=payload.budget, ai_assisted=payload.ai_assisted)
    return ok({"cart": cart_service.serialize_cart(cart)})


@app.get("/api/cart/{cart_id}")
async def get_cart(cart_id: int, db: Session = Depends(get_db)):
    cart = cart_service.get_cart(db, cart_id)
    if cart is None:
        return _error_response("CART_NOT_FOUND", "Cart not found.", status=404)
    return ok({"cart": cart_service.serialize_cart(cart)})


@app.post("/api/cart/{cart_id}/items")
async def add_cart_item(cart_id: int, payload: AddItemRequest, db: Session = Depends(get_db)):
    cart = cart_service.add_item(
        db, cart_id, payload.product_id, quantity=payload.quantity, is_upsell=payload.is_upsell
    )
    item = next((it for it in cart.items if it.product_id == payload.product_id), None)
    record_event(
        db,
        event_type=EventType.UPSELL_ACCEPTED if payload.is_upsell else EventType.CART_UPDATED,
        description=(
            f"Buyer accepted upsell: {item.product_name}" if payload.is_upsell and item
            else f"Added {item.product_name if item else 'item'} to cart"
        ),
        source=EventSource.USER,
        cart_id=cart.id,
        metadata={"product_id": payload.product_id, "is_upsell": payload.is_upsell},
    )
    return ok({"cart": cart_service.serialize_cart(cart)})


@app.patch("/api/cart/{cart_id}/items/{item_id}")
async def update_cart_item(cart_id: int, item_id: int, payload: UpdateItemRequest, db: Session = Depends(get_db)):
    cart = cart_service.update_item_quantity(db, cart_id, item_id, payload.quantity)
    return ok({"cart": cart_service.serialize_cart(cart)})


@app.delete("/api/cart/{cart_id}/items/{item_id}")
async def remove_cart_item(cart_id: int, item_id: int, db: Session = Depends(get_db)):
    cart = cart_service.remove_item(db, cart_id, item_id)
    return ok({"cart": cart_service.serialize_cart(cart)})


@app.post("/api/cart/{cart_id}/clear")
async def clear_cart(cart_id: int, db: Session = Depends(get_db)):
    cart = cart_service.clear_cart(db, cart_id)
    return ok({"cart": cart_service.serialize_cart(cart)})


# --------------------------------------------------------------------------- #
# Orders & payments
# --------------------------------------------------------------------------- #
@app.post("/api/orders/create")
async def create_order(payload: CreateOrderRequest, db: Session = Depends(get_db)):
    config = _config(db)
    customer = payload.customer.model_dump() if payload.customer else None
    order = orders.create_order(db, payload.cart_id, config, confirmed=payload.confirmed, customer=customer)

    record_event(
        db,
        event_type=EventType.CHECKOUT_OPENED,
        description=f"Checkout opened for order {order.order_number}.",
        source=EventSource.ORDER,
        order_id=order.id,
        metadata={"total": order.total},
    )
    return ok(
        {
            "order": orders.serialize_order(order),
            "checkout": {
                "key": razorpay_tools.get_key_id(),
                "razorpay_order_id": order.razorpay_order_id,
                "amount": order.total * 100,  # paise, derived from the backend order total
                "currency": order.currency,
                "name": config.name,
                "description": f"Order {order.order_number}",
            },
        }
    )


@app.get("/api/orders/{order_id}")
async def get_order(order_id: int, db: Session = Depends(get_db)):
    order = orders.get_order(db, order_id)
    if order is None:
        return _error_response("ORDER_NOT_FOUND", "Order not found.", status=404)
    return ok({"order": orders.serialize_order(order)})


@app.post("/api/payments/verify")
async def verify_payment(payload: VerifyPaymentRequest, db: Session = Depends(get_db)):
    order = orders.verify_and_complete(
        db,
        payload.order_id,
        razorpay_payment_id=payload.razorpay_payment_id,
        razorpay_order_id=payload.razorpay_order_id,
        razorpay_signature=payload.razorpay_signature,
    )
    return ok({"order": orders.serialize_order(order), "verified": True})


@app.post("/api/payments/failed")
async def payment_failed(payload: PaymentFailedRequest, db: Session = Depends(get_db)):
    order = orders.mark_payment_failed(db, payload.order_id, reason=payload.reason or "Payment was not completed.")
    return ok({"order": orders.serialize_order(order)})


# --------------------------------------------------------------------------- #
# Merchant analytics
# --------------------------------------------------------------------------- #
@app.get("/api/metrics")
async def get_metrics(db: Session = Depends(get_db)):
    return ok({"metrics": metrics.compute_metrics(db)})


@app.get("/api/chart-data")
async def get_chart_data(db: Session = Depends(get_db)):
    return ok({"chart": metrics.revenue_timeseries(db)})


@app.get("/api/notifications")
async def get_notifications(db: Session = Depends(get_db)):
    return ok({"notifications": metrics.recent_notifications(db)})


@app.get("/api/audit-log")
async def get_audit_log(
    source: Optional[str] = None,
    event_type: Optional[str] = None,
    limit: int = 50,
    db: Session = Depends(get_db),
):
    events = get_recent_events(db, limit=min(max(limit, 1), 200), source=source, event_type=event_type)
    return ok({"logs": [e.to_dict() for e in events]})


# --------------------------------------------------------------------------- #
# Demo utilities (clearly demo-only)
# --------------------------------------------------------------------------- #
@app.post("/api/demo/reset")
async def demo_reset():
    """Demo only: wipe transactional data and reseed the catalog to a clean state."""
    summary = reset_and_seed()
    return ok({"reset": True, "seeded": summary})
