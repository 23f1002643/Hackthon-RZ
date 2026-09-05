# Vastra Studio — AI Growth & Agentic Commerce

Vastra Studio is a full-stack commerce-agent prototype built for the **Razorpay AI Buildathon 2026**. It connects natural-language product discovery with a merchant dashboard, persistent catalog/cart/order data, explainable agent decisions, and Razorpay Test Mode checkout.

The project is designed around a simple idea: **understand shopper intent → find relevant products → recommend responsibly → assist with checkout → record what happened**.

## ✨ What it does

### Buyer experience
- Natural-language shopping on `/shop`.
- Intent-aware product discovery across fashion, jewellery, accessories, and other catalog categories.
- Product recommendations are selected from the merchant's persisted catalog rather than invented by the model.
- Contextual upsell suggestions based on the current cart and related products.
- Server-side cart and order creation.
- Razorpay Test Mode checkout with server-side payment verification.
- Customer/order history persisted in SQLite.

### Merchant experience
- Merchant dashboard on `/dashboard`.
- Live revenue, order, upsell, and agent-activity metrics from the backend.
- Catalog management with manual product creation.
- DummyJSON catalog import for a broad baseline dataset.
- Optional Bright Data catalog ingestion for external commerce data.
- Agent on/off control and merchant policy limits.
- Searchable and exportable audit trail of agent decisions.
- Customer and order views for merchant operations.

## 🧠 Agent architecture

The agent uses a LangGraph workflow with clear stages:

```text
Shopper message
      ↓
Intent parsing / domain guardrail
      ↓
Local catalog search
      ↓
AI recommendation + ranking
      ↓
Contextual upsell
      ↓
Cart / checkout
      ↓
Razorpay verification
      ↓
Audit trail + merchant metrics
```

The NVIDIA LLM is used as a reasoning layer for intent interpretation, recommendation selection, and explanations. Deterministic fallbacks keep the demo usable when an LLM key is unavailable.

The backend remains the source of truth for product IDs, prices, inventory, order totals, payment verification, and merchant policy checks.

## 🗂️ Project structure

```text
Hackthon-RZ/
├── backend/
│   ├── main.py              # FastAPI application and API routes
│   ├── agent.py             # LangGraph commerce-agent workflow
│   ├── llm.py               # NVIDIA LLM + deterministic fallbacks
│   ├── models.py            # SQLAlchemy models
│   ├── catalog.py           # Catalog/search logic
│   ├── dummyjson.py         # DummyJSON catalog ingestion
│   ├── brightdata.py        # Optional Bright Data ingestion
│   ├── cart_service.py      # Cart operations
│   ├── orders.py            # Order and inventory logic
│   ├── razorpay_tools.py    # Razorpay Test Mode integration
│   ├── audit.py             # Explainable agent events
│   ├── metrics.py           # Merchant analytics
│   ├── seed_products.py     # Local demo seed data
│   ├── requirements.txt
│   └── .env.example
├── agent-growth-hub-main/
│   └── src/
│       ├── routes/           # Buyer and merchant routes
│       ├── components/       # UI components and theme provider
│       ├── lib/api.ts        # Frontend API client
│       └── styles.css        # Dashboard design system
├── frontend/                 # Supporting frontend assets/config
├── testing.md
└── LICENSE
```

## 🚀 Run locally

### 1. Backend

From the repository root:

```bash
python -m venv .venv
```

Activate the environment:

**Windows PowerShell**

```powershell
.venv\Scripts\Activate.ps1
```

**macOS / Linux**

```bash
source .venv/bin/activate
```

Install dependencies:

```bash
pip install -r backend/requirements.txt
```

Copy the environment template:

```bash
cp backend/.env.example backend/.env
```

On Windows, copy the file manually if `cp` is unavailable.

Start FastAPI:

```bash
uvicorn backend.main:app --reload --port 8000
```

### 2. Frontend

Open another terminal:

```bash
cd agent-growth-hub-main
npm install
npm run dev
```

The Vite development server normally runs at:

```text
http://127.0.0.1:5173
```

Useful routes:

- `http://127.0.0.1:5173/shop` — buyer experience
- `http://127.0.0.1:5173/dashboard` — merchant dashboard

## 🔐 Environment variables

The application supports:

- `RAZORPAY_KEY_ID`
- `RAZORPAY_KEY_SECRET`
- `NVIDIA_API_KEY`
- `NVIDIA_MODEL`
- `NVIDIA_BASE_URL`
- `LLM_TIMEOUT_SECONDS`
- `BRIGHTDATA_API_KEY`
- `BRIGHTDATA_API_URL`
- `DATABASE_URL` (optional)

Never commit real API keys or secrets. Use `backend/.env` locally and keep the committed `.env.example` limited to placeholders.

## 🛍️ Catalog sources

Vastra Studio normalizes external products into its local SQLite catalog before the shopping agent uses them.

### DummyJSON

DummyJSON provides a broad, predictable baseline dataset that is useful for development and demonstrations. The dashboard can import it directly with **Import DummyJSON**.

### Bright Data

Bright Data is supported as an optional external catalog source. Its ingestion endpoint is configured through environment variables and imported products are persisted locally. The buyer flow does **not** depend on making an external catalog request for every shopper message.

### Manual products

Merchants can add products one by one from the dashboard. Manual products are stored in the local database and remain part of the same searchable catalog.

## 💳 Payments

Razorpay is integrated in **Test Mode**. The client does not decide the payable amount. The backend calculates the order total from persisted product/cart data, creates the Razorpay order, and verifies the payment signature before marking the order as paid.

No real money should be processed during the demo.

## 🛡️ Safety and agent boundaries

The commerce agent is intentionally bounded to shopping tasks. It should not turn arbitrary prompts into general-purpose answers or allow user instructions to override merchant policies.

Important boundaries include:

- Product recommendations must reference catalog products.
- Prices and order totals are controlled by the backend.
- Merchant policy limits are enforced server-side.
- Checkout and payment state are verified server-side.
- Agent decisions are recorded for merchant review.
- External catalog providers are ingestion sources, not payment or order authorities.

## 🧪 Testing

The repository includes focused checkout and audit tests. Run the backend tests with:

```bash
pytest -q
```

For a broader manual verification checklist, see [`testing.md`](testing.md).

For frontend validation:

```bash
cd agent-growth-hub-main
npm run build
npm run lint
```

## 📊 Demo flow

A good end-to-end demonstration is:

1. Open `/shop`.
2. Ask for a fashion or jewellery item with an occasion and budget.
3. Review products returned from the local catalog.
4. Add an item to the cart.
5. Review the contextual upsell.
6. Continue to Razorpay Test Mode checkout.
7. Complete/verify the test payment.
8. Open `/dashboard`.
9. Check the order, customer, metrics, and audit trail.
10. Open the catalog and demonstrate importing or manually adding a product.

## 🧩 Design principles

- **Backend is the source of truth** for commerce state.
- **AI assists decisions; it does not invent inventory or payment amounts.**
- **External data is normalized before use.**
- **Every meaningful agent action should be explainable.**
- **Merchant controls remain explicit and auditable.**
- **The demo should degrade gracefully when optional AI/data-provider credentials are unavailable.**

## 🏆 Buildathon context

This project targets the **AI Growth & Agentic Commerce** direction of the Razorpay AI Buildathon. The prototype focuses on demonstrating how an agent can contribute to measurable commerce outcomes while keeping payment and merchant-control boundaries deterministic and reviewable.

## 📄 License

This project is released under the license included in [`LICENSE`](LICENSE).
