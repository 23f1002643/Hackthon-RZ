Razorpay Commerce Agent Backend

Setup

```bash
# from workspace root
python -m pip install -r backend/requirements.txt
```

Run tests

```bash
cd backend
pytest -q
```

Start server

```bash
python -m uvicorn backend.main:app --reload --port 8000
```

API endpoints

- POST `/api/shop/search`
- POST `/api/cart`
- POST `/api/cart/{cart_id}/items`
- POST `/api/orders/create`
- POST `/api/payments/verify`
- POST `/api/payments/failed`
- GET  `/api/audit-log`
- GET  `/api/metrics`
- POST `/api/agent/toggle` with `{ "active": true|false }`

Dev notes

- Backend runs on http://127.0.0.1:8000 by default
- Frontend API client is in `agent-growth-hub-main/src/lib/api.ts`
- Put Razorpay keys in `backend/.env` as `RAZORPAY_KEY_ID` and `RAZORPAY_KEY_SECRET` (already gitignored)
