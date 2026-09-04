"""Deterministic catalog search, ranking and curated relations."""
from backend import catalog


def test_wedding_query_ranks_banarasi_first(db):
    # The scripted demo query, evaluated with the LLM disabled (deterministic ranker).
    results = catalog.search_products(
        db, query="something for my sister's wedding", occasion="wedding", max_price=4000, gender="women", limit=8
    )
    assert results, "expected at least one wedding match"
    assert results[0].name == "Banarasi Silk Saree"


def test_budget_filter_excludes_expensive(db):
    results = catalog.search_products(db, query="lehenga", max_price=4000, limit=20)
    assert all(p.price <= 4000 for p in results)


def test_gender_filter(db):
    results = catalog.search_products(db, query="kurta", gender="women", limit=20)
    assert all(p.gender in ("women", "unisex") for p in results)


def test_related_products_prioritises_earrings(db, find_product):
    saree = find_product("Banarasi Silk Saree")
    related = catalog.get_related_products(db, saree.id, limit=6, max_price=1500)
    assert related, "saree should have curated related products"
    assert related[0].name == "Pearl Drop Earrings"


def test_check_inventory(db, find_product):
    saree = find_product("Banarasi Silk Saree")
    assert catalog.check_inventory(db, saree.id, quantity=1) is True
