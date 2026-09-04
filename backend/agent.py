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
    db: Session
    config: MerchantConfig
    intent: Dict[str, Any]
    candidates: List[Dict[str, Any]]
    recommendation: Optional[Dict[str, Any]]
    upsell: Optional[Dict[str, Any]]
    steps: List[Dict[str, str]]


CANDIDATE_LIMIT = 8


# --------------------------------------------------------------------------- #
# Graph nodes (pure-ish functions returning partial state updates)
# --------------------------------------------------------------------------- #
def node_parse_intent(state: ShopState) -> Dict[str, Any]:
    query = state["query"]
    intent = llm.parse_intent(query)
    record_event(
        state["db"],
        event_type=EventType.INTENT_PARSED,
        description=f"Understood request: occasion={intent.get('occasion') or '—'}, budget=₹{intent.get('budget') or '—'}",
        source=EventSource.AI,
        cart_id=None,
        metadata={"query": query, "intent": intent},
    )
    steps = state.get("steps", []) + [{"key": "intent", "label": "Understanding your request", "status": "done"}]
    return {"intent": intent, "steps": steps}


def node_search_catalog(state: ShopState) -> Dict[str, Any]:
    db, intent = state["db"], state["intent"]
    products = catalog.search_products(
        db,
        query=state["query"],
        category=intent.get("category"),
        occasion=intent.get("occasion"),
        max_price=intent.get("budget"),
        gender=intent.get("gender"),
        in_stock_only=True,
        limit=CANDIDATE_LIMIT,
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

    if not candidates:
        return {"recommendation": None, "upsell": None, "steps": steps}

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
    upsell = _resolve_upsell(db, config, primary, budget, rec, upsell_candidates)
    if upsell:
        record_event(
            db,
            event_type=EventType.UPSELL_PROPOSED,
            description=f"Proposed add-on: {upsell['product']['name']} (₹{upsell['product']['price']})",
            source=EventSource.AI,
            metadata={"product_id": upsell["product"]["id"], "reason": upsell["reason"]},
        )

    return {"recommendation": recommendation, "upsell": upsell, "steps": steps}


def _resolve_upsell(
    db: Session,
    config: MerchantConfig,
    primary: Optional[Product],
    budget: Optional[int],
    rec: Dict[str, Any],
    upsell_candidates: List[Dict[str, Any]],
) -> Optional[Dict[str, Any]]:
    if primary is None:
        return None
    remaining = None if budget is None else max(0, budget - primary.price)

    def _valid(product: Product) -> bool:
        return policy.check_upsell(config, upsell_price=product.price, remaining_budget=remaining).allowed

    # 1) Honour a policy-valid LLM upsell choice.
    if rec.get("upsell_product_id"):
        product = catalog.get_product(db, rec["upsell_product_id"])
        if product and product.id != primary.id and product.stock > 0 and _valid(product):
            return {"product": product.to_dict(), "reason": rec.get("upsell_reason") or "Pairs beautifully with your selection."}

    # 2) Deterministic fallback: best curated related item within policy/budget.
    for product in catalog.get_related_products(db, primary.id, limit=6, max_price=config.max_upsell_value):
        if product.id != primary.id and _valid(product):
            return {"product": product.to_dict(), "reason": "Frequently paired with this piece and keeps you within budget."}
    return None


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


def run_discovery(db: Session, query: str, config: MerchantConfig) -> Dict[str, Any]:
    """Execute the discovery pipeline and return the assembled result for the API."""
    initial: ShopState = {"query": query, "db": db, "config": config, "steps": []}

    graph = _get_graph()
    if graph is not None:
        try:
            final = graph.invoke(initial)
        except Exception:
            final = _run_sequential(initial)
    else:
        final = _run_sequential(initial)

    intent = final.get("intent", {})
    return {
        "intent": {k: intent.get(k) for k in ("intent", "occasion", "recipient", "category", "budget", "gender", "preferences", "constraints")},
        "products": final.get("candidates", []),
        "recommendation": final.get("recommendation"),
        "upsell": final.get("upsell"),
        "steps": final.get("steps", []),
        "backend": _graph_backend,
    }


def _run_sequential(state: ShopState) -> ShopState:
    for node in (node_parse_intent, node_search_catalog, node_recommend):
        state = {**state, **node(state)}
    return state
