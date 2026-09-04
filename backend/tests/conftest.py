"""Pytest fixtures. Runs the backend fully offline against an isolated temp DB.

Env is set BEFORE importing any backend module so ``backend.db`` binds its engine
to the temp database, and the LLM/Razorpay layers start disabled (tests that need
Razorpay monkeypatch the functions directly).
"""
import os
import pathlib
import tempfile

# --- Isolate + force deterministic offline mode (must precede backend imports) ---
_TMP_DB = pathlib.Path(tempfile.gettempdir()) / "vastra_studio_test.db"
if _TMP_DB.exists():
    _TMP_DB.unlink()
os.environ["DATABASE_URL"] = f"sqlite:///{_TMP_DB.as_posix()}"
os.environ["NVIDIA_API_KEY"] = ""        # deterministic intent + recommendation
os.environ["RAZORPAY_KEY_ID"] = ""       # flow tests monkeypatch razorpay_tools
os.environ["RAZORPAY_KEY_SECRET"] = ""

import pytest  # noqa: E402

from backend.db import SessionLocal, init_db  # noqa: E402
from backend.models import DEMO_MERCHANT_ID, MerchantConfig, Product  # noqa: E402
from backend.seed import seed_all  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def _prepare_db():
    init_db()
    seed_all()
    yield


@pytest.fixture()
def db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture()
def config(db):
    return db.get(MerchantConfig, DEMO_MERCHANT_ID)


@pytest.fixture()
def find_product(db):
    """Return a lookup(name) -> Product bound to the test's own session."""
    from sqlalchemy import select

    def _find(name: str) -> Product:
        return db.execute(select(Product).where(Product.name == name)).scalar_one()

    return _find
