"""Razorpay Test Mode integration — the only place money touches an external API.

What this module does:
  * ``create_order``      — create a REAL Razorpay order (amount computed by the
                            backend, converted rupees -> paise here and nowhere else).
  * ``verify_payment_signature`` — verify the Checkout callback server-side using
                            the official HMAC-SHA256 mechanism
                            ``hmac_sha256(order_id + "|" + payment_id, secret)``.
  * ``fetch_payment``     — optionally read a payment back from Razorpay to
                            cross-check status/amount.
  * ``create_customer``   — best-effort customer creation (non-critical).

What it must never do: fabricate payment ids, fabricate a signature, or report a
payment as successful without a verified signature. There is no fake-capture path.
"""
from __future__ import annotations

import hashlib
import hmac
import os
from typing import Any, Dict, Optional

import razorpay
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

RAZORPAY_KEY_ID = (os.getenv("RAZORPAY_KEY_ID") or "").strip()
RAZORPAY_KEY_SECRET = (os.getenv("RAZORPAY_KEY_SECRET") or "").strip()


class RazorpayError(RuntimeError):
    """Raised for any Razorpay-side failure. Callers translate this to a
    structured API error; the raw exception never reaches the client."""


def razorpay_enabled() -> bool:
    return bool(RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET)


def get_key_id() -> str:
    """Public key id — safe to send to the frontend for Checkout. (The secret never leaves the server.)"""
    return RAZORPAY_KEY_ID


def _client() -> razorpay.Client:
    if not razorpay_enabled():
        raise RazorpayError("Razorpay keys are not configured on the server.")
    client = razorpay.Client(auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET))
    client.set_app_details({"title": "VastraStudio-CommerceAgent", "version": "1.0"})
    return client


def _to_paise(amount_rupees: int) -> int:
    # DB stores integer rupees; Razorpay expects integer paise.
    return int(round(int(amount_rupees) * 100))


def create_order(amount_rupees: int, *, receipt: str, notes: Optional[Dict[str, Any]] = None, currency: str = "INR") -> Dict[str, Any]:
    """Create a Razorpay order for a backend-computed amount. Returns the raw order dict."""
    if amount_rupees <= 0:
        raise RazorpayError("Order amount must be positive.")
    client = _client()
    payload: Dict[str, Any] = {
        "amount": _to_paise(amount_rupees),
        "currency": currency,
        "receipt": receipt,
        "payment_capture": 1,  # auto-capture on successful authorization
    }
    if notes:
        payload["notes"] = notes
    try:
        return client.order.create(payload)
    except Exception as exc:  # razorpay.errors.* or network
        raise RazorpayError(f"Failed to create Razorpay order: {exc}") from exc


def verify_payment_signature(razorpay_order_id: str, razorpay_payment_id: str, razorpay_signature: str) -> bool:
    """Verify the Checkout signature server-side (constant-time HMAC compare).

    Official mechanism: expected = HMAC_SHA256(order_id + "|" + payment_id, secret).
    Returns True only on an exact match.
    """
    if not (razorpay_order_id and razorpay_payment_id and razorpay_signature):
        return False
    if not RAZORPAY_KEY_SECRET:
        return False
    message = f"{razorpay_order_id}|{razorpay_payment_id}".encode("utf-8")
    expected = hmac.new(RAZORPAY_KEY_SECRET.encode("utf-8"), message, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, razorpay_signature.strip())


def fetch_payment(payment_id: str) -> Optional[Dict[str, Any]]:
    """Read a payment back from Razorpay (best-effort cross-check). Returns None on error."""
    try:
        return _client().payment.fetch(payment_id)
    except Exception:
        return None


def create_customer(name: str, email: Optional[str] = None, contact: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Best-effort Razorpay customer creation. Returns None on failure (non-critical)."""
    try:
        payload: Dict[str, Any] = {"name": name, "fail_existing": 0}
        if email:
            payload["email"] = email
        if contact:
            payload["contact"] = contact
        return _client().customer.create(payload)
    except Exception:
        return None
