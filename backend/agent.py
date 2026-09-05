"""Agent orchestration for the shopping *discovery* flow.

This is a real LangGraph ``StateGraph`` (parse_intent -> search_catalog ->
recommend). The identical node functions also run as a plain sequential pipeline
if LangGraph is unavailable, so behaviour is deterministic either way.

Deliberate boundary: the graph covers only reasoning/discovery. The
money-moving steps from the product spec — create_order, verify_payment,
complete_order — are **deterministic backend services** (see ``orders.py``)
invoked by explicit, user-confirmed API calls. The LLM never sits on the money
path. (LLM = reasoning, backend = truth, policy = safety, Razorpay = payment.)
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, TypedDict

from sqlalchemy.orm import Session

from . import catalog, llm, policy
from .audit import EventType, record_event
from .models import EventSource, MerchantConfig, Product


class ShopState(TypedDict, total=False):
    query: str
    context: List[str]
    db: Session
    config: MerchantConfig
    intent: Dict[str, Any]
    candidates: List[Dict[str, Any]]
    recommendation: Optional[Dict[str, Any]]
    upsell: Optional[Dict[str, Any]]
    upsell_options: List[Dict[str, Any]]
    no_results_message: str
    steps: List[Dict[str, str]]


CANDIDATE_LIMIT = 8


# --------------------------------------------------------------------------- #
# Graph nodes (pure-ish functions returning partial state updates)
# --------------------------------------------------------------------------- #
def node_parse_intent(state: ShopState) -> Dict[str, Any]:
    query = state["query"]
    steps = state.get("steps", []) + [{"key": "intent", "label": "Understanding your request", "status": "done"}]
    message_type = llm.classify_message(query)
    if message_type != "shopping":
        intent = {"intent": message_type, "source": "deterministic", "preferences": [], "constraints": []}
        return {"intent": intent, "steps": steps}
    intent = llm.parse_intent(query)
    context_list = state.get("context", [])
    if context_list:
        ctx = llm.extract_context_intent(context_list)
        if not intent.get("category") and ctx.get("category"):
            intent["category"] = ctx["category"]
        if not intent.get("occasion") and ctx.get("occasion"):
            intent["occasion"] = ctx["occasion"]
        if ctx.get("affordability_requested") and not intent.get("budget"):
            intent["budget"] = 5000
    record_event(
        state["db"],
        event_type=EventType.INTENT_PARSED,
        description=f"Understood request: occasion={intent.get('occasion') or '—'}, budget=₹{intent.get('budget') or '—'}",
        source=EventSource.AI,
        cart_id=None,
        metadata={"query": query, "intent": intent},
    )
    return {"intent": intent, "steps": steps}


def node_search_catalog(state: ShopState) -> Dict[str, Any]:
    db, intent = state["db"], state["intent"]
    if intent.get("intent") != "shopping":
        return {"candidates": [], "steps": state.get("steps", [])}
    products = catalog.search_products(
        db,
        query=state["query"],
        category=intent.get("category"),
        occasion=intent.get("occasion"),
        max_price=intent.get("budget"),
        gender=intent.get("gender"),
        tags=[*intent.get("preferences", []), *intent.get("constraints", [])],
        in_stock_only=True,
        limit=CANDIDATE_LIMIT,
        allowed_categories=catalog.FASHION_CATEGORIES,
    )
    candidates = [p.to_dict() for p in products]
    record_event(
        db,
        event_type=EventType.PRODUCT_SEARCH,
        description=f"Searched catalog — {len(candidates)} in-stock matches.",
        source=EventSource.AI,
        metadata={"count": len(candidates), "filters": {k: intent.get(k) for k in ("category", "occasion", "budget", "gender")}},
    )
    steps = state.get("steps", []) + [
        {"key": "catalog", "label": "Checking merchant catalog", "status": "done"},
        {"key": "inventory", "label": "Checking availability", "status": "done"},
    ]
    return {"candidates": candidates, "steps": steps}


def _upsell_pool(db: Session, candidates: List[Dict[str, Any]], config: MerchantConfig, budget: Optional[int]) -> List[Dict[str, Any]]:
    """Related products of the top candidates, offered to the LLM as upsell options.

    An item may legitimately be both a search result and a good add-on (e.g.
    matching earrings for a saree), so we do NOT exclude search candidates here —
    we only avoid suggesting a product as its own upsell and dedupe by id.
    """
    pool: Dict[int, Dict[str, Any]] = {}
    for c in candidates[:3]:
        headroom = None if budget is None else max(0, budget - c["price"])
        cap = config.max_upsell_value if headroom is None else min(config.max_upsell_value, headroom)
        for rel in catalog.get_related_products(db, c["id"], limit=4, max_price=cap):
            if rel.id == c["id"] or rel.id in pool:
                continue
            pool[rel.id] = rel.to_dict()
    return list(pool.values())


def node_recommend(state: ShopState) -> Dict[str, Any]:
    db, config, intent = state["db"], state["config"], state["intent"]
    candidates = state.get("candidates", [])
    steps = state.get("steps", []) + [{"key": "match", "label": "Finding your best match", "status": "done"}]

    if intent.get("intent") != "shopping":
        return {"recommendation": None, "upsell": None, "upsell_options": [], "steps": steps}
    if not candidates:
        category = intent.get("category") or "items"
        budget = intent.get("budget")
        if budget:
            no_msg = (
                f"We don't carry {category} under ₹{budget:,} right now — "
                f"our {category.lower()} start from higher price points. "
                "Want me to show what's available, or suggest something else in your budget?"
            )
        else:
            no_msg = (
                f"I couldn't find {category} in our current catalog. "
                "Try a different category or tell me your budget and occasion — I'll find the best match."
            )
        return {"recommendation": None, "upsell": None, "upsell_options": [], "steps": steps, "no_results_message": no_msg}

    budget = intent.get("budget")
    upsell_candidates = _upsell_pool(db, candidates, config, budget)

    rec = llm.generate_recommendation(state["query"], intent, candidates, upsell_candidates)

    primary = catalog.get_product(db, rec["product_id"]) if rec.get("product_id") else None
    if primary is None:
        primary = catalog.get_product(db, candidates[0]["id"])

    recommendation = {"product": primary.to_dict(), "reason": rec.get("reason", "")} if primary else None
    record_event(
        db,
        event_type=EventType.PRODUCT_RECOMMENDED,
        description=f"Recommended {primary.name}" if primary else "No recommendation",
        source=EventSource.AI,
        metadata={"product_id": primary.id if primary else None, "reason": rec.get("reason"), "llm": rec.get("source")},
    )

    # Resolve upsell deterministically under policy, using the LLM choice as a hint.
    upsell_options = _resolve_upsells(db, config, primary, budget, rec, upsell_candidates)
    upsell = upsell_options[0] if upsell_options else None
    if upsell:
        record_event(
            db,
            event_type=EventType.UPSELL_PROPOSED,
            description=f"Proposed add-on: {upsell['product']['name']} (₹{upsell['product']['price']})",
            source=EventSource.AI,
            metadata={"product_id": upsell["product"]["id"], "reason": upsell["reason"]},
        )

    return {"recommendation": recommendation, "upsell": upsell, "upsell_options": upsell_options, "steps": steps}


def _resolve_upsells(
    db: Session,
    config: MerchantConfig,
    primary: Optional[Product],
    budget: Optional[int],
    rec: Dict[str, Any],
    upsell_candidates: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    if primary is None:
        return []
    remaining = None if budget is None else max(0, budget - primary.price)

    def _valid(product: Product) -> bool:
        return policy.check_upsell(config, upsell_price=product.price, remaining_budget=remaining).allowed

    options: List[Dict[str, Any]] = []
    seen: set[int] = set()

    # 1) Honour a policy-valid LLM upsell choice as the first option.
    if rec.get("upsell_product_id"):
        product = catalog.get_product(db, rec["upsell_product_id"])
        if product and product.id != primary.id and product.stock > 0 and _valid(product):
            options.append({"product": product.to_dict(), "reason": rec.get("upsell_reason") or "Pairs beautifully with your selection."})
            seen.add(product.id)

    # 2) Fill a short, curated suggestion rail from related products only.
    for product in catalog.get_related_products(db, primary.id, limit=8, max_price=config.max_upsell_value):
        if product.id == primary.id or product.id in seen or not _valid(product):
            continue
        options.append({"product": product.to_dict(), "reason": "Complements your selected outfit and stays within your budget."})
        seen.add(product.id)
        if len(options) >= 3:
            break
    return options


# --------------------------------------------------------------------------- #
# Graph assembly (LangGraph if available, deterministic sequential otherwise)
# --------------------------------------------------------------------------- #
_compiled_graph = None
_graph_backend = "sequential"


def _build_langgraph():
    global _graph_backend
    from langgraph.graph import END, START, StateGraph

    builder = StateGraph(ShopState)
    builder.add_node("parse_intent", node_parse_intent)
    builder.add_node("search_catalog", node_search_catalog)
    builder.add_node("recommend", node_recommend)
    builder.add_edge(START, "parse_intent")
    builder.add_edge("parse_intent", "search_catalog")
    builder.add_edge("search_catalog", "recommend")
    builder.add_edge("recommend", END)
    graph = builder.compile()
    _graph_backend = "langgraph"
    return graph


def _get_graph():
    global _compiled_graph
    if _compiled_graph is None:
        try:
            _compiled_graph = _build_langgraph()
        except Exception:
            _compiled_graph = None  # sequential fallback used
    return _compiled_graph


def graph_backend() -> str:
    _get_graph()
    return _graph_backend


def run_discovery(db: Session, query: str, config: MerchantConfig, context: Optional[List[str]] = None) -> Dict[str, Any]:
    """Execute the discovery pipeline and return the assembled result for the API."""
    initial: ShopState = {"query": query, "context": context or [], "db": db, "config": config, "steps": []}

    graph = _get_graph()
    if graph is not None:
        try:
            final = graph.invoke(initial)
        except Exception:
            try:
                final = _run_sequential(initial)
            except Exception:
                final = {"intent": {"intent": "unclear"}, "candidates": [], "recommendation": None, "upsell": None, "upsell_options": [], "steps": []}
    else:
        try:
            final = _run_sequential(initial)
        except Exception:
            final = {"intent": {"intent": "unclear"}, "candidates": [], "recommendation": None, "upsell": None, "upsell_options": [], "steps": []}

    intent = final.get("intent", {})
    message_type = intent.get("intent", "unclear")
    response = llm.seller_response(query, message_type) if message_type in {"greeting", "unclear"} else None
    if response is None and not final.get("candidates"):
        response = final.get("no_results_message") or (
            "I couldn't find a close match right now. Try a different category, adjust your budget, "
            "or tell me the occasion and I'll suggest the best fit."
        )
    return {
        "intent": {k: intent.get(k) for k in ("intent", "occasion", "recipient", "category", "budget", "gender", "preferences", "constraints")},
        "products": final.get("candidates", []),
        "recommendation": final.get("recommendation"),
        "upsell": final.get("upsell"),
        "upsell_options": final.get("upsell_options", []),
        "steps": final.get("steps", []),
        "backend": _graph_backend,
        "message": response,
    }


def _run_sequential(state: ShopState) -> ShopState:
    for node in (node_parse_intent, node_search_catalog, node_recommend):
        state = {**state, **node(state)}
    return state
