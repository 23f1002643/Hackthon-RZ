"""NVIDIA LLM integration — the *reasoning* layer only.

Hard boundaries (enforced by the caller in ``agent.py``):
  * The LLM may parse intent, pick a product **from a supplied candidate list**,
    explain a recommendation, and judge whether an upsell is useful.
  * The LLM may NOT invent products or prices, compute totals, or move money.
    Every id it returns is validated against the candidate set; anything invalid
    is rejected and we fall back to deterministic logic.

If NVIDIA is unavailable/slow/malformed, every function degrades to a
deterministic result so the shopping flow keeps working.
"""
from __future__ import annotations

import json
import os
import re
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

_NVIDIA_API_KEY = os.getenv("NVIDIA_API_KEY", "").strip()
_NVIDIA_MODEL = os.getenv("NVIDIA_MODEL", "meta/llama-3.1-70b-instruct").strip()
_NVIDIA_BASE_URL = os.getenv("NVIDIA_BASE_URL", "https://integrate.api.nvidia.com/v1").strip()
_LLM_TIMEOUT = float(os.getenv("LLM_TIMEOUT_SECONDS", "12"))

_client = None
if _NVIDIA_API_KEY:
    try:
        from openai import OpenAI

        _client = OpenAI(base_url=_NVIDIA_BASE_URL, api_key=_NVIDIA_API_KEY, timeout=_LLM_TIMEOUT, max_retries=1)
    except Exception:  # pragma: no cover - defensive import guard
        _client = None


def llm_available() -> bool:
    return _client is not None


# --------------------------------------------------------------------------- #
# Low-level helpers
# --------------------------------------------------------------------------- #
def _extract_json(text: str) -> Optional[Any]:
    """Pull the first JSON object/array out of a model response, tolerating fences/prose."""
    if not text:
        return None
    cleaned = text.strip()
    cleaned = re.sub(r"^```(?:json)?", "", cleaned).strip()
    cleaned = re.sub(r"```$", "", cleaned).strip()
    try:
        return json.loads(cleaned)
    except Exception:
        pass
    match = re.search(r"(\{.*\}|\[.*\])", cleaned, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except Exception:
            return None
    return None


def _chat_json(prompt: str, *, max_tokens: int = 220, temperature: float = 0.3) -> Optional[Any]:
    if not _client:
        return None
    try:
        resp = _client.chat.completions.create(
            model=_NVIDIA_MODEL,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=max_tokens,
            temperature=temperature,
        )
        return _extract_json(resp.choices[0].message.content or "")
    except Exception:
        return None


# --------------------------------------------------------------------------- #
# Intent parsing
# --------------------------------------------------------------------------- #
_OCCASION_KEYWORDS = {
    "wedding": ["wedding", "shaadi", "marriage", "bride", "groom"],
    "festive": ["festive", "festival", "diwali", "navratri", "eid", "puja", "pooja", "rakhi", "holi"],
    "party": ["party", "cocktail", "reception", "celebration", "night out"],
    "office": ["office", "work", "formal", "meeting"],
    "casual": ["casual", "everyday", "daily", "regular"],
    "gifting": ["gift", "gifting", "present", "birthday", "anniversary"],
}
_CATEGORY_KEYWORDS = {
    "Sarees": ["saree", "sari"],
    "Kurtas": ["kurta", "kurti", "kurta set"],
    "Dupattas": ["dupatta", "stole"],
    "Jewellery": ["jewellery", "jewelry", "earring", "necklace", "choker", "bangle", "jhumka"],
    "Bags": ["bag", "potli", "clutch", "handbag"],
    "Accessories": ["wallet", "belt", "accessory", "accessories", "watch"],
    "Gifts": ["gift box", "hamper"],
    "Footwear": ["juttis", "jutti", "shoes", "footwear", "mojari", "sandals"],
}

_GREETING_WORDS = {"hi", "hii", "hello", "hey", "thanks", "thank you", "good morning", "good evening", "good afternoon"}
_NON_FASHION_WORDS = {"laptop", "computer", "phone", "smartphone", "tablet", "camera", "television", "tv", "electronics", "refrigerator", "fridge", "microwave", "software", "python", "javascript", "sql", "code", "malware", "quantum", "recursion", "essay", "joke"}
_SHOPPING_SIGNALS = set(sum(_OCCASION_KEYWORDS.values(), []) + sum(_CATEGORY_KEYWORDS.values(), []) + ["buy", "find", "need", "looking", "show", "want", "under", "budget", "price", "₹", "rs"])


def classify_message(query: str) -> str:
    """Classify conversational input before any catalog retrieval occurs."""
    normalized = re.sub(r"[^a-z0-9₹ ]+", " ", (query or "").lower()).strip()
    if normalized in _GREETING_WORDS or len(normalized.split()) <= 2 and normalized in _GREETING_WORDS:
        return "greeting"
    tokens = set(normalized.split())
    if tokens.intersection(_NON_FASHION_WORDS):
        return "unclear"
    if any((signal in tokens) or (" " in signal and signal in normalized) for signal in _SHOPPING_SIGNALS):
        return "shopping"
    return "unclear"


def _deterministic_intent(query: str) -> Dict[str, Any]:
    q = (query or "").lower()

    budget: Optional[int] = None
    m = re.search(r"(?:under|below|less than|within|budget of|upto|up to|max|maximum)?\s*(?:rs\.?|inr|₹)?\s*([\d,]{2,7})\s*(k)?", q)
    if m:
        raw = m.group(1).replace(",", "")
        try:
            value = int(raw)
            if m.group(2) == "k":
                value *= 1000
            if 50 <= value <= 500000:
                budget = value
        except Exception:
            budget = None

    occasion = next((occ for occ, kws in _OCCASION_KEYWORDS.items() if any(k in q for k in kws)), None)
    category = next((cat for cat, kws in _CATEGORY_KEYWORDS.items() if any(k in q for k in kws)), None)

    gender = None
    if any(k in q for k in ["men", "male", "him", "husband", "father", "brother", "dad", "boyfriend"]):
        gender = "men"
    elif any(k in q for k in ["women", "woman", "female", "her", "wife", "mother", "sister", "girlfriend", "mom"]):
        gender = "women"

    recipient = None
    for rel in ["sister", "mother", "wife", "husband", "brother", "friend", "daughter", "son", "mom", "dad", "father"]:
        if rel in q:
            recipient = rel
            break

    return {
        "intent": "shopping" if classify_message(query) == "shopping" else classify_message(query),
        "occasion": occasion,
        "recipient": recipient,
        "category": category,
        "budget": budget,
        "gender": gender,
        "preferences": [],
        "constraints": [],
        "source": "deterministic",
    }


def parse_intent(query: str) -> Dict[str, Any]:
    """Return a structured shopping intent. LLM-first, deterministic fallback + merge."""
    fallback = _deterministic_intent(query)

    prompt = (
        "You extract shopping intent from a shopper message for an Indian ethnic-wear store.\n"
        f"Message: \"{query}\"\n\n"
        "Respond ONLY with minified JSON (no markdown) of this exact shape:\n"
        '{"intent":"shopping","occasion":null,"recipient":null,"category":null,'
        '"budget":null,"gender":null,"preferences":[],"constraints":[]}\n'
        "Rules: occasion in [wedding,festive,party,office,casual,gifting] or null. "
        "category in [Sarees,Kurtas,Dupattas,Jewellery,Bags,Accessories,Gifts,Footwear] or null. "
        "gender in [women,men] or null. budget is an integer in rupees or null. "
        "preferences/constraints are short strings."
    )
    data = _chat_json(prompt, max_tokens=200, temperature=0.1)
    if not isinstance(data, dict):
        return fallback

    def pick(key, allowed=None):
        val = data.get(key)
        if val in (None, "", "null"):
            return fallback.get(key)
        if allowed and val not in allowed:
            return fallback.get(key)
        return val

    budget = data.get("budget")
    try:
        budget = int(budget) if budget not in (None, "", "null") else fallback.get("budget")
    except Exception:
        budget = fallback.get("budget")

    merged = {
        "intent": "shopping",
        "occasion": pick("occasion", set(_OCCASION_KEYWORDS)),
        "recipient": pick("recipient"),
        "category": pick("category", set(_CATEGORY_KEYWORDS)),
        "budget": budget,
        "gender": pick("gender", {"women", "men"}),
        "preferences": data.get("preferences") if isinstance(data.get("preferences"), list) else [],
        "constraints": data.get("constraints") if isinstance(data.get("constraints"), list) else [],
        "source": "llm",
    }
    return merged


# --------------------------------------------------------------------------- #
# Recommendation
# --------------------------------------------------------------------------- #
def generate_recommendation(
    query: str,
    intent: Dict[str, Any],
    candidates: List[Dict[str, Any]],
    upsell_candidates: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """Ask the LLM to choose a primary product + optional upsell from GIVEN sets.

    Returns {product_id, reason, upsell_product_id|None, upsell_reason}. All ids
    are validated by the caller against the candidate sets.
    """
    valid_ids = {c["id"] for c in candidates}
    valid_upsell_ids = {c["id"] for c in upsell_candidates}

    def _fallback() -> Dict[str, Any]:
        top = candidates[0] if candidates else None
        upsell = upsell_candidates[0] if upsell_candidates else None
        occasion = intent.get("occasion")
        reason = (
            f"A strong match for {occasion} and well within your budget."
            if occasion
            else "A top-rated pick that fits your request and budget."
        )
        return {
            "product_id": top["id"] if top else None,
            "reason": reason,
            "upsell_product_id": upsell["id"] if upsell else None,
            "upsell_reason": ("Pairs beautifully with your selection." if upsell else ""),
            "source": "deterministic",
        }

    if not candidates:
        return _fallback()

    cand_lines = "\n".join(
        f'- id={c["id"]} | {c["name"]} | ₹{c["price"]} | {c["category"]} | occasions={c.get("occasion", [])}'
        for c in candidates[:8]
    )
    upsell_lines = "\n".join(
        f'- id={c["id"]} | {c["name"]} | ₹{c["price"]} | {c["category"]}' for c in upsell_candidates[:6]
    ) or "(none available)"

    prompt = (
        "You are a shopping assistant for an Indian ethnic-wear store. Choose the single best "
        "product for the shopper from the CANDIDATES, and optionally one complementary add-on "
        "from UPSELL OPTIONS if it genuinely fits.\n\n"
        f'Shopper: "{query}"\n'
        f"Intent: occasion={intent.get('occasion')}, budget=₹{intent.get('budget')}, recipient={intent.get('recipient')}\n\n"
        f"CANDIDATES:\n{cand_lines}\n\n"
        f"UPSELL OPTIONS:\n{upsell_lines}\n\n"
        "Respond ONLY with minified JSON of this exact shape (ids MUST come from the lists above; "
        "use null for no upsell):\n"
        '{"product_id":0,"reason":"one short sentence","upsell_product_id":null,"upsell_reason":""}\n'
        "The reason must reference the occasion/budget/fit in one sentence."
    )
    data = _chat_json(prompt, max_tokens=180, temperature=0.4)
    if not isinstance(data, dict):
        return _fallback()

    fb = _fallback()
    try:
        product_id = int(data.get("product_id"))
    except Exception:
        product_id = None
    if product_id not in valid_ids:
        product_id = fb["product_id"]

    upsell_id = data.get("upsell_product_id")
    try:
        upsell_id = int(upsell_id) if upsell_id not in (None, "", "null") else None
    except Exception:
        upsell_id = None
    if upsell_id is not None and upsell_id not in valid_upsell_ids:
        upsell_id = None  # reject hallucinated upsell; deterministic layer may re-add one

    reason = str(data.get("reason") or fb["reason"]).strip()[:220] or fb["reason"]
    upsell_reason = str(data.get("upsell_reason") or "").strip()[:220]

    return {
        "product_id": product_id,
        "reason": reason,
        "upsell_product_id": upsell_id,
        "upsell_reason": upsell_reason or ("Pairs beautifully with your selection." if upsell_id else ""),
        "source": "llm",
    }
