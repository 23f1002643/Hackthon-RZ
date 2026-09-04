"""LangGraph-style agent implementation.

Provides node functions:
- analyze_cart
- upsell_decision
- create_order
- capture_payment
- log_action

Also exposes `run_full_flow` to run the end-to-end checkout simulation.
"""
import json
import os
import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv
from openai import OpenAI

from . import razorpay_tools as rz, audit

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

_nvidia_api_key = os.getenv("NVIDIA_API_KEY", "")
_nvidia_client = OpenAI(
    base_url="https://integrate.api.nvidia.com/v1",
    api_key=_nvidia_api_key if _nvidia_api_key else "dummy-key-not-set",
) if _nvidia_api_key else None


def _clean_copy_text(value: Any, fallback: str) -> str:
    text = str(value or "").strip()
    if not text:
        return fallback

    # Strip model / provider fallback noise before rendering it in the UI.
    text = re.sub(r"\(fallback:.*$", "", text, flags=re.IGNORECASE).strip()
    text = re.sub(r"error code:\s*\d+.*$", "", text, flags=re.IGNORECASE).strip()
    text = re.sub(r"\{.*$", "", text).strip().strip("\"'")
    text = re.sub(r"\s+", " ", text).strip(" ,.;:-")
    return text or fallback


def _normalize_suggestion(llm_result: Dict[str, Any]) -> Dict[str, Any]:
    fallback_item = "Handcrafted dupatta"
    fallback_reason = "Adds a complementary festive finish to the current outfit."

    try:
        price = float(llm_result.get("price", 399) or 399)
    except Exception:
        price = 399.0

    price = min(max(price, 199.0), 1499.0)

    return {
        "item": _clean_copy_text(llm_result.get("item"), fallback_item),
        "price": price,
        "reason": _clean_copy_text(llm_result.get("reason"), fallback_reason),
    }


def _llm_analyze(cart_items, total) -> dict:
    """Call NVIDIA LLM to analyze cart and generate upsell suggestion with reason."""
    if not _nvidia_client:
        return {"item": "handcrafted dupatta", "price": 399, "reason": "A complementary ethnic accessory pairs well with this outfit."}

    cart_str = ", ".join([f"{i.get('name')} x{i.get('qty', 1)} @ ₹{i.get('price')}" for i in cart_items])
    prompt = f"""You are an AI commerce agent for Zephyr Apparel, an ethnic wear brand.

Cart: {cart_str}
Cart Total: ₹{total}

Your job:
1. Suggest ONE specific product to upsell (must be relevant to the cart)
2. Give a short reason (1 sentence, data-driven, mention cart context)
3. Suggest a price between ₹199-₹1499

Respond ONLY in this JSON format (no markdown, no extra text):
{{"item": "product name", "price": 599, "reason": "one sentence why this fits the cart"}}"""

    try:
        resp = _nvidia_client.chat.completions.create(
            model="meta/llama-3.1-70b-instruct",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=150,
            temperature=0.4,
        )
        text = resp.choices[0].message.content.strip()
        return json.loads(text)
    except Exception:
        return {
            "item": "handcrafted dupatta",
            "price": 399,
            "reason": "A complementary ethnic accessory pairs well with this outfit.",
        }


@dataclass
class AgentState:
    cart: List[Dict[str, Any]] = field(default_factory=list)
    customer_id: Optional[str] = None
    order_id: Optional[str] = None
    audit_trail: List[Dict[str, Any]] = field(default_factory=list)
    upsell_offered: bool = False
    payment_status: Optional[str] = None


class CommerceAgent:
    UPSALE_THRESHOLD = 500.0

    def __init__(self):
        self.state = AgentState()

    def _now(self) -> str:
        return datetime.utcnow().isoformat() + "Z"

    def log_action(self, action: str, inputs: Dict[str, Any], outputs: Dict[str, Any], reason: str) -> Dict[str, Any]:
        entry = {
            "timestamp": self._now(),
            "action": action,
            "inputs": inputs,
            "outputs": outputs,
            "reason": reason,
        }
        # append-only audit
        audit.append_log(entry)
        self.state.audit_trail.append(entry)
        return entry

    def analyze_cart(self, cart_items: List[Dict[str, Any]]) -> Dict[str, Any]:
        self.state.cart = cart_items
        total = sum(float(i.get("price", 0)) * int(i.get("qty", 1)) for i in cart_items)

        suggestion = _normalize_suggestion(_llm_analyze(cart_items, total))
        reason = suggestion["reason"]

        outputs = {"total": total, "suggestion": suggestion}
        return self.log_action("analyze_cart", {"cart": cart_items}, outputs, reason=reason)

    def upsell_decision(self) -> Dict[str, Any]:
        total = sum(float(it.get("price", 0)) * int(it.get("qty", 1)) for it in self.state.cart)
        decision = total > self.UPSALE_THRESHOLD
        reason = f"order total {total} {'>' if decision else '<='} upsell threshold {self.UPSALE_THRESHOLD}"
        outputs = {"decision": decision, "total": total}
        if decision:
            self.state.upsell_offered = True
        return self.log_action("upsell_decision", {"cart_total": total}, outputs, reason=reason)

    def create_order(self, currency: str = "INR", receipt: Optional[str] = None) -> Dict[str, Any]:
        total = sum(float(it.get("price", 0)) * int(it.get("qty", 1)) for it in self.state.cart)
        # enforce hard max
        if total > rz.MAX_ORDER_RUPEES:
            return self.log_action("create_order", {"amount": total}, {}, reason=f"amount exceeds max {rz.MAX_ORDER_RUPEES}")

        resp = rz.create_order(total, currency, receipt)
        # try extract order id
        order_id = None
        raw = resp.get("outputs", {}).get("raw") if isinstance(resp.get("outputs"), dict) else resp.get("outputs")
        if isinstance(raw, dict):
            order_id = raw.get("id") or raw.get("order_id")
        if order_id:
            self.state.order_id = order_id

        return self.log_action("create_order", {"amount": total, "currency": currency, "receipt": receipt}, resp, reason="Created order via Razorpay")

    def capture_payment(self, payment_id: str, amount: float) -> Dict[str, Any]:
        resp = rz.capture_payment(payment_id, amount)
        err = resp.get("error")
        if err:
            self.state.payment_status = "failed"
            # log and stop
            return self.log_action("capture_payment", {"payment_id": payment_id, "amount": amount}, resp, reason=f"capture failed: {err}")

        self.state.payment_status = "captured"
        return self.log_action("capture_payment", {"payment_id": payment_id, "amount": amount}, resp, reason="Payment captured successfully")

    def log_action_node(self, action: str, inputs: Dict[str, Any], outputs: Dict[str, Any], reason: str) -> Dict[str, Any]:
        return self.log_action(action, inputs, outputs, reason)

    def run_full_flow(self, cart: List[Dict[str, Any]], customer_info: Dict[str, Any]) -> Dict[str, Any]:
        # analyze
        self.analyze_cart(cart)
        upsell_entry = self.upsell_decision()

        # ensure customer exists
        cust_resp = rz.create_customer(customer_info.get("name", "Guest"), customer_info.get("email"), customer_info.get("contact"))
        cust_id = None
        outputs = cust_resp.get("outputs") if isinstance(cust_resp, dict) else None
        if isinstance(outputs, dict):
            raw = outputs.get("raw")
            if isinstance(raw, dict):
                cust_id = raw.get("id") or raw.get("customer_id")
        if not cust_id:
            # fallback to response field
            cust_id = cust_resp.get("outputs", {}).get("customer_id") if isinstance(cust_resp.get("outputs"), dict) else cust_resp.get("customer_id")
        self.state.customer_id = cust_id
        self.log_action("create_customer", {"customer_info": customer_info}, cust_resp, reason="Ensured customer record")

        # handle upsell acceptance (frontend may indicate acceptance)
        accept_upsell = bool(customer_info.get("accept_upsell", False))
        if self.state.upsell_offered and accept_upsell:
            # append upsell item from last analyze_cart suggestion
            last_suggestion = None
            # find last analyze_cart in audit_trail
            for e in reversed(self.state.audit_trail):
                if e.get("action") == "analyze_cart":
                    last_suggestion = e.get("outputs", {}).get("suggestion")
                    break
            if last_suggestion:
                self.state.cart.append({"name": last_suggestion.get("item"), "price": last_suggestion.get("price", 0), "qty": 1})
                self.log_action("upsell_accepted", {"suggestion": last_suggestion}, {"accepted": True}, reason="Customer accepted upsell")

        # create order
        order_entry = self.create_order(receipt=f"rcpt_{int(datetime.utcnow().timestamp())}")

        # simulate payment capture: in tests, caller should pass payment_id; here we simulate a payment id
        simulated_payment_id = customer_info.get("simulate_payment_id") or f"pay_{int(datetime.utcnow().timestamp())}"
        # determine amount for capture: try to read from order raw response
        raw_amount = 0
        try:
            raw = order_entry.get("outputs", {}).get("raw")
            if isinstance(raw, dict):
                raw_amount = raw.get("amount", 0) / 100.0 if raw.get("amount") else 0
        except Exception:
            raw_amount = 0

        # fallback to sum from cart
        if not raw_amount:
            raw_amount = sum(float(it.get("price", 0)) * int(it.get("qty", 1)) for it in self.state.cart)

        capture_entry = self.capture_payment(simulated_payment_id, raw_amount)

        return {
            "order": order_entry,
            "capture": capture_entry,
            "customer": cust_resp,
            "upsell_decision": upsell_entry,
        }


# expose a default agent instance
agent = CommerceAgent()


def build_langgraph_agent():
    try:
        import langgraph as lg

        # This is a light integration: create nodes wrapping the methods
        graph = {}
        graph["analyze_cart"] = agent.analyze_cart
        graph["upsell_decision"] = agent.upsell_decision
        graph["create_order"] = agent.create_order
        graph["capture_payment"] = agent.capture_payment
        graph["log_action"] = agent.log_action_node
        return graph
    except Exception:
        # LangGraph not available or integration deferred; return simple dict of callables
        return {
            "analyze_cart": agent.analyze_cart,
            "upsell_decision": agent.upsell_decision,
            "create_order": agent.create_order,
            "capture_payment": agent.capture_payment,
            "log_action": agent.log_action_node,
        }


__all__ = ["agent", "build_langgraph_agent", "CommerceAgent", "AgentState"]
