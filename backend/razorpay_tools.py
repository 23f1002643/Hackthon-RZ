"""Razorpay API wrappers using the `razorpay` SDK.

Functions:
- create_order(amount, currency, receipt)
- capture_payment(payment_id, amount)
- get_customer(customer_id)
- create_customer(name, email, contact)

Each function returns a dict containing: timestamp, action, inputs, outputs, error (optional).
Logs are appended to the in-memory audit via `audit.append_log`.
"""
import os
import time
from datetime import datetime
from typing import Any, Dict, Optional

import razorpay
from dotenv import load_dotenv

from . import audit


load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

RAZORPAY_KEY_ID = os.getenv("RAZORPAY_KEY_ID")
RAZORPAY_KEY_SECRET = os.getenv("RAZORPAY_KEY_SECRET")

MAX_ORDER_RUPEES = 50000
MAX_RETRIES = 3


def _now_iso() -> str:
    return datetime.utcnow().isoformat() + "Z"


def _make_client() -> razorpay.Client:
    if not RAZORPAY_KEY_ID or not RAZORPAY_KEY_SECRET:
        raise RuntimeError("Razorpay keys not set in environment (.env)")
    return razorpay.Client(auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET))


def _log_and_append(action: str, inputs: Dict[str, Any], outputs: Dict[str, Any], error: Optional[str] = None) -> Dict[str, Any]:
    entry = {
        "timestamp": _now_iso(),
        "action": action,
        "inputs": inputs,
        "outputs": outputs,
    }
    if error:
        entry["error"] = error
    # Append to audit (append-only in-memory store)
    try:
        audit.append_log({**entry, "source": "razorpay_tools"})
    except Exception:
        # avoid failing logging
        pass
    return entry


def _to_paise(amount_rupees: float) -> int:
    return int(round(float(amount_rupees) * 100))


def create_order(amount: float, currency: str = "INR", receipt: Optional[str] = None) -> Dict[str, Any]:
    action = "create_order"
    inputs = {"amount": amount, "currency": currency, "receipt": receipt}

    if amount > MAX_ORDER_RUPEES:
        return _log_and_append(action, inputs, {}, error=f"amount exceeds max limit {MAX_ORDER_RUPEES}")

    client = _make_client()
    amount_paise = _to_paise(amount)

    last_exc = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            payload = {"amount": amount_paise, "currency": currency}
            if receipt:
                payload["receipt"] = receipt
            resp = client.order.create(payload)
            outputs = {"raw": resp}
            return _log_and_append(action, inputs, outputs)
        except Exception as e:
            last_exc = e
            time.sleep(0.5 * attempt)

    return _log_and_append(action, inputs, {}, error=str(last_exc))


def capture_payment(payment_id: str, amount: float) -> Dict[str, Any]:
    action = "capture_payment"
    inputs = {"payment_id": payment_id, "amount": amount}

    client = _make_client()
    amount_paise = _to_paise(amount)

    last_exc = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            resp = client.payment.capture(payment_id, amount_paise)
            outputs = {"raw": resp}
            return _log_and_append(action, inputs, outputs)
        except Exception as e:
            last_exc = e
            # On capture failure do not infinite-retry; respect MAX_RETRIES
            time.sleep(0.5 * attempt)

    return _log_and_append(action, inputs, {}, error=str(last_exc))


def get_customer(customer_id: str) -> Dict[str, Any]:
    action = "get_customer"
    inputs = {"customer_id": customer_id}

    client = _make_client()
    try:
        resp = client.customer.fetch(customer_id)
        outputs = {"raw": resp}
        return _log_and_append(action, inputs, outputs)
    except Exception as e:
        return _log_and_append(action, inputs, {}, error=str(e))


def create_customer(name: str, email: Optional[str] = None, contact: Optional[str] = None) -> Dict[str, Any]:
    action = "create_customer"
    inputs = {"name": name, "email": email, "contact": contact}

    client = _make_client()
    try:
        payload = {"name": name}
        if email:
            payload["email"] = email
        if contact:
            payload["contact"] = contact
        resp = client.customer.create(payload)
        outputs = {"raw": resp}
        return _log_and_append(action, inputs, outputs)
    except Exception as e:
        return _log_and_append(action, inputs, {}, error=str(e))
