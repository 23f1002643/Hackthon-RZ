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

Run demo script (shows payment capture failure handling)

```bash
python -m backend.demo_payment_failure
```

Start server

```bash
python -m uvicorn backend.main:app --reload --port 8000
```

API endpoints

- POST `/api/checkout`
- GET  `/api/audit-log`
- GET  `/api/metrics`
- POST `/api/agent/toggle`

Dev notes

- Backend runs on http://127.0.0.1:8000 by default
- Frontend helper available at `frontend/api.js`
- Put Razorpay keys in `backend/.env` as `RAZORPAY_KEY_ID` and `RAZORPAY_KEY_SECRET` (already gitignored)
