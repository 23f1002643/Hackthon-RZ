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

from . import agent, brightdata, cart_service, catalog, dummyjson, llm, metrics, orders, razorpay_tools
from .audit import EventType, get_recent_events, record_event
from .cart_service import CartError
from .db import get_db, init_db
from .models import DEMO_MERCHANT_ID, EventSource, MerchantConfig, Customer, Order, OrderStatus, Product
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
    CustomerRequest,
    ProductIn,
)
from .seed import reset_and_seed, seed_all

app = FastAPI(title="Vastra Studio — Commerce Agent", version="1.0.0")

_CATEGORY_IMAGES = {
    "Sarees": "https://images.unsplash.com/photo-1610030469983-98e550d6193c?w=400&q=80",
    "Kurtas": "https://images.unsplash.com/photo-1583391733956-6c78276477e1?w=400&q=80",
    "Dupattas": "https://images.unsplash.com/photo-1617897903246-719242758050?w=400&q=80",
    "Jewellery": "https://images.unsplash.com/photo-1535632066927-ab7c9ab60908?w=400&q=80",
    "Bags": "https://images.unsplash.com/photo-1548036328-c9fa89d128fa?w=400&q=80",
    "Footwear": "https://images.unsplash.com/photo-1603808033192-082d6919d3e1?w=400&q=80",
    "Accessories": "https://images.unsplash.com/photo-1523293182086-7651a899d37f?w=400&q=80",
    "Gifts": "https://images.unsplash.com/photo-1549465220-1a8b9238cd48?w=400&q=80",
    "Lehengas": "https://images.unsplash.com/photo-1583391733956-6c78276477e1?w=400&q=80",
    "Dresses": "https://images.unsplash.com/photo-1515886657613-9f3515b0c78f?w=400&q=80",
}

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


@app.post("/api/admin/fix-images")
async def fix_images(db: Session = Depends(get_db)):
    products = db.query(Product).filter((Product.image_url.is_(None)) | (Product.image_url == "")).all()
    updated = 0
    for product in products:
        image_url = _CATEGORY_IMAGES.get(product.category)
        if image_url:
            product.image_url = image_url
            updated += 1
    db.commit()
    return ok({"updated": updated, "total": len(products)})


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


@app.post("/api/customers")
async def create_or_get_customer(payload: CustomerRequest, db: Session = Depends(get_db)):
    if not payload.email and not payload.contact:
        return _error_response("CUSTOMER_IDENTITY_REQUIRED", "Provide an email or contact number for demo session identity.")
    customer = None
    if payload.email:
        customer = db.query(Customer).filter(Customer.email == payload.email).first()
    if customer is None and payload.contact:
        customer = db.query(Customer).filter(Customer.contact == payload.contact).first()
    if customer is None:
        customer = Customer(name=payload.name or "Guest", email=payload.email, contact=payload.contact)
        db.add(customer)
    elif payload.name:
        customer.name = payload.name
    db.commit()
    db.refresh(customer)
    return ok({"customer": customer.to_dict()})


@app.get("/api/customers")
async def list_customers(db: Session = Depends(get_db)):
    customers = db.query(Customer).order_by(Customer.created_at.desc()).all()
    result = []
    for customer in customers:
        orders_for_customer = db.query(Order).filter(Order.customer_id == customer.id, Order.status.in_([OrderStatus.PAID, OrderStatus.COMPLETED])).all()
        result.append({**customer.to_dict(), "order_count": len(orders_for_customer), "total_spend": sum(order.total for order in orders_for_customer), "ai_assisted_orders": sum(1 for order in orders_for_customer if order.ai_assisted), "last_order": orders_for_customer[-1].created_at.isoformat() if orders_for_customer else None})
    return ok({"customers": result})


@app.get("/api/customers/{customer_id}/orders")
async def customer_orders(customer_id: int, db: Session = Depends(get_db)):
    customer = db.get(Customer, customer_id)
    if customer is None:
        return _error_response("CUSTOMER_NOT_FOUND", "Customer not found.", status=404)
    rows = db.query(Order).filter(Order.customer_id == customer_id).order_by(Order.created_at.desc()).all()
    return ok({"customer": customer.to_dict(), "orders": [orders.serialize_order(order) for order in rows]})


@app.get("/api/orders")
async def list_orders(db: Session = Depends(get_db)):
    rows = db.query(Order).order_by(Order.created_at.desc()).limit(200).all()
    return ok({"orders": [orders.serialize_order(order) for order in rows]})


@app.post("/api/catalog/import")
async def import_catalog(source: str = "brightdata", payload: Optional[dict] = None, db: Session = Depends(get_db)):
    try:
        if source == "dummyjson":
            result = dummyjson.import_catalog(db)
        elif source == "brightdata":
            result = brightdata.import_catalog(db, payload=payload or None)
        else:
            return _error_response("INVALID_CATALOG_SOURCE", "Supported catalog sources are dummyjson and brightdata.")
    except brightdata.BrightDataError as exc:
        return _error_response("CATALOG_IMPORT_FAILED", str(exc), status=502)
    return ok({"import": result})


@app.post("/api/products")
async def create_product(payload: ProductIn, db: Session = Depends(get_db)):
    product = Product(merchant_id=DEMO_MERCHANT_ID, source="manual", **payload.model_dump())
    db.add(product)
    db.commit()
    db.refresh(product)
    return ok({"product": product.to_dict()})


@app.patch("/api/products/{product_id}")
async def update_product(product_id: int, payload: ProductIn, db: Session = Depends(get_db)):
    product = catalog.get_product(db, product_id)
    if product is None:
        return _error_response("PRODUCT_NOT_FOUND", "Product not found.", status=404)
    for key, value in payload.model_dump().items():
        setattr(product, key, value)
    db.commit()
    db.refresh(product)
    return ok({"product": product.to_dict()})


@app.delete("/api/products/{product_id}")
async def archive_product(product_id: int, db: Session = Depends(get_db)):
    product = catalog.get_product(db, product_id)
    if product is None:
        return _error_response("PRODUCT_NOT_FOUND", "Product not found.", status=404)
    product.active = False
    db.commit()
    return ok({"archived": True, "product_id": product_id})


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
            allowed_categories=catalog.FASHION_CATEGORIES,
        )
        return ok(
            {
                "agent_active": False,
                "intent": {"intent": "shopping", **{k: intent.get(k) for k in ("occasion", "recipient", "category", "budget", "gender")}},
                "products": [p.to_dict() for p in products],
                "recommendation": None,
                "upsell": None,
                "upsell_options": [],
                "message": "Our shopping assistant is resting right now. I can still show fashion products from the Vastra Studio catalog, but AI recommendations are paused.",
                "steps": [{"key": "catalog", "label": "Browsing catalog (agent paused)", "status": "done"}],
                "backend": "paused",
            }
        )

    result = agent.run_discovery(db, payload.query, config, payload.context)
    result["agent_active"] = True
    return ok(result)


# --------------------------------------------------------------------------- #
# Cart
# --------------------------------------------------------------------------- #
@app.post("/api/cart")
async def create_cart(payload: CreateCartRequest, db: Session = Depends(get_db)):
    cart = cart_service.create_cart(db, budget=payload.budget, ai_assisted=payload.ai_assisted, customer_id=payload.customer_id)
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
    order = orders.create_order(db, payload.cart_id, config, confirmed=payload.confirmed, customer=customer, customer_id=payload.customer_id)

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
