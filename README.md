<div align="center">

<img src="https://readme-typing-svg.demolab.com?font=Inter&weight=700&size=36&pause=1000&color=4F6EF7&center=true&vCenter=true&width=600&lines=Vastra+Studio;AI+Agentic+Commerce+Platform" alt="Vastra Studio" />

<br/>

[![Razorpay Buildathon](https://img.shields.io/badge/Razorpay-AI%20Buildathon%202025-0EA5E9?style=for-the-badge&logo=razorpay&logoColor=white)](https://razorpay.com/buildathon/)
[![Track](https://img.shields.io/badge/Track%2001-AI%20Growth%20%26%20Agentic%20Commerce-4F6EF7?style=for-the-badge)](https://razorpay.com/buildathon/)
[![LLM](https://img.shields.io/badge/LLaMA%203.1%2070B-NVIDIA%20NIM-76B900?style=for-the-badge&logo=nvidia&logoColor=white)](https://build.nvidia.com)
[![Framework](https://img.shields.io/badge/LangGraph-Agent%20Framework-FF6B35?style=for-the-badge)](https://langchain-ai.github.io/langgraph/)
[![Payments](https://img.shields.io/badge/Razorpay-Test%20Mode-0EA5E9?style=for-the-badge)](https://razorpay.com)

<br/>

> **An AI agent that understands what customers want, recommends the right product, upsells intelligently, and logs every decision — giving merchants complete visibility and control.**

</div>

---

## 📋 Table of Contents

- [Problem Statement](#-problem-statement)
- [Track 01 — How Requirements Are Met](#-track-01--how-requirements-are-met)
- [System Architecture](#-system-architecture)
- [Agent Pipeline](#-agent-pipeline)
- [Tech Stack](#-tech-stack)
- [Product Catalog](#-product-catalog)
- [Features](#-features)
- [Getting Started](#-getting-started)
- [API Reference](#-api-reference)
- [Author](#-author)

---

## 🎯 Problem Statement

Online fashion merchants lose **30–40% of potential revenue** because there is no intelligent layer between the customer and the catalog.

| Without AI | With Vastra Studio |
|---|---|
| Keyword-matched generic list | Natural language understanding |
| No upsell logic | Contextual upsell — right product, right moment |
| Merchant has zero visibility | Full audit trail — every decision logged with reason |
| Wrong product on no-results | Honest message + alternate suggestion |
| No control over agent | Pause / resume + hard policy limits |

**Vastra Studio** is an AI-powered agentic commerce platform. The agent understands intent, recommends products, upsells contextually, and keeps the merchant in full control — fulfilling every requirement of Track 01.

---

## ✅ Track 01 — How Requirements Are Met

```
Track 01: AI Growth & Agentic Commerce
```

| Requirement | Implementation |
|---|---|
| 🤖 **Autonomous revenue growth** | LangGraph agent recommends + upsells without merchant intervention |
| 💬 **Explainable actions** | Every recommendation has an LLM-generated reason in the audit log |
| 🔒 **Bounded & gated** | Merchant sets max order value + upsell threshold — agent cannot exceed |
| 📋 **Full audit trail** | Append-only log: action, reason, timestamp, outcome — CSV export |
| ⚡ **Graceful failure** | No product in budget → honest message. Payment failure → logged, no retry loop |
| ⏸️ **Merchant control** | One-click agent pause → pure catalog browse, zero AI involvement |

---

## 🏗 System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        VASTRA STUDIO                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│   ┌──────────────────┐         ┌──────────────────────────┐    │
│   │  Customer Shop   │         │   Merchant Dashboard     │    │
│   │  React + Router  │         │   React + Router         │    │
│   │  /shop           │         │   /dashboard             │    │
│   └────────┬─────────┘         └────────────┬─────────────┘    │
│            │                                │                  │
│            └──────────────┬─────────────────┘                  │
│                           │ HTTP REST                          │
│            ┌──────────────▼──────────────────┐                 │
│            │        FastAPI Backend           │                 │
│            │        18 REST endpoints         │                 │
│            └──────────────┬──────────────────┘                 │
│                           │                                    │
│         ┌─────────────────┼─────────────────┐                  │
│         │                 │                 │                  │
│  ┌──────▼──────┐  ┌───────▼──────┐  ┌──────▼───────┐         │
│  │  LangGraph  │  │  SQLite DB   │  │   Razorpay   │         │
│  │  AI Agent   │  │  102 Products│  │  Test Mode   │         │
│  └──────┬──────┘  └──────────────┘  └──────────────┘         │
│         │                                                      │
│  ┌──────▼──────┐                                              │
│  │  NVIDIA NIM │                                              │
│  │  LLaMA 3.1  │                                              │
│  │  70B Instruct│                                             │
│  └─────────────┘                                              │
└───────────────────────────────────────────────────────────────┘
```

---

## 🔄 Agent Pipeline

The LangGraph agent runs a **stateful 4-node pipeline** for every customer query:

```
Customer Query
      │
      ▼
┌─────────────────┐
│  parse_intent   │  ← LLaMA 70B: extracts occasion, budget,
│                 │    category, gender, recipient
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ search_catalog  │  ← SQLite search with filters
│                 │    Carries context from previous turns
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   recommend     │  ← LLaMA 70B: picks best match
│                 │    Generates personalized reason
│                 │    Selects upsell from pool
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   log_action    │  ← Appends to audit trail
│                 │    action + reason + timestamp + outcome
└────────┬────────┘
         │
         ▼
   Response to UI
```

> **Fallback:** When NVIDIA NIM is unavailable, the agent falls back to deterministic catalog search — always returns a result, never crashes.

---

## 🛠 Tech Stack

| Layer | Technology |
|---|---|
| **Frontend** | React 18, TanStack Router, Tailwind CSS, Recharts, Lucide Icons |
| **Backend** | FastAPI, Python 3.12, Uvicorn |
| **AI Agent** | LangGraph, NVIDIA NIM — LLaMA 3.1 70B Instruct |
| **Database** | SQLite via SQLAlchemy ORM |
| **Payments** | Razorpay Test Mode — Orders, Payments, Signature Verification |
| **UI Theme** | Dark / Light mode, oklch color system, gradient design tokens |

---

## 🛍 Product Catalog

**102 active products** across **14 categories:**

```
Category        Products    Price Range
──────────────────────────────────────────
Accessories        19       ₹349   – ₹13,27,999
Footwear           12       ₹899   – ₹12,449
Beauty             10       ₹746   – ₹10,789
Lifestyle          10       ₹91,299 – ₹12,44,999
Jewellery           9       ₹449   – ₹2,489
Bags                8       ₹449   – ₹49,799
Kurtas              6       ₹899   – ₹2,599
Sarees              5       ₹1,499 – ₹3,299
Shirts              5       ₹1,659 – ₹2,904
Tops                5       ₹1,659 – ₹3,319
Dresses             5       ₹4,149 – ₹14,939
Gifts               3       ₹749   – ₹1,299
Dupattas            3       ₹549   – ₹799
Lehengas            2       ₹4,499 – ₹8,999
```

---

## ✨ Features

### 🤖 Customer Shop — `/shop`
- Natural language search — `"saree for my sister's wedding under 4000"`
- Multi-turn context — remembers category and occasion across conversation turns
- LLM-generated personalized reason for every recommendation
- Proactive upsell — complementary product suggested based on cart
- Honest no-results — `"We don't carry Watches under ₹2,000"` instead of wrong recommendation
- Cart — add, remove, adjust quantity with `+` / `−` controls
- Razorpay checkout — real payment flow with cryptographic signature verification

### 📊 Merchant Dashboard — `/dashboard`
- Live KPI strip — Revenue, Orders, Upsell Acceptance Rate, Agent Actions
- Hourly revenue chart — today vs yesterday
- Agent activity feed — real-time action log with status indicators
- Audit log — every AI decision with reason, searchable, CSV export
- Agent toggle — pause/resume with one click
- Notification bell — payment captured, upsell accepted, errors

### ⚙️ Merchant Config
- Max order value — hard cap, agent cannot create orders above this
- Upsell threshold — minimum cart value to trigger upsell suggestion
- Agent active/paused state — persisted in database

---

## 🚀 Getting Started

### Prerequisites

- Python 3.10+
- Bun or Node.js 18+
- Razorpay Test Mode API keys → [dashboard.razorpay.com](https://dashboard.razorpay.com)
- NVIDIA NIM API key (free) → [build.nvidia.com/settings/api-keys](https://build.nvidia.com/settings/api-keys)

### 1. Clone

```bash
git clone https://github.com/23f1002643/Hackthon-RZ.git
cd Hackthon-RZ
```

### 2. Backend

```bash
cd backend
pip install -r requirements.txt
```

Create `backend/.env`:

```env
RAZORPAY_KEY_ID=rzp_test_xxxxxxxxxxxx
RAZORPAY_KEY_SECRET=xxxxxxxxxxxxxxxxxxxxxxxx
NVIDIA_API_KEY=nvapi-xxxxxxxxxxxxxxxxxxxx
```

```bash
uvicorn backend.main:app --reload --port 8000
```

### 3. Frontend

```bash
cd agent-growth-hub-main
bun install
bun dev
```

### 4. Open

| Surface | URL |
|---|---|
| Customer Shop | http://127.0.0.1:5173/shop |
| Merchant Dashboard | http://127.0.0.1:5173/dashboard |
| API Docs (Swagger) | http://127.0.0.1:8000/docs |

### 5. Seed images (one-time)

```bash
curl -X POST http://localhost:8000/api/admin/fix-images
```

---

## 📡 API Reference

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/shop/search` | AI agent — natural language search |
| `GET` | `/api/products` | List products with filters |
| `POST` | `/api/cart` | Create cart |
| `POST` | `/api/cart/{id}/items` | Add item |
| `PATCH` | `/api/cart/{id}/items/{item_id}` | Update quantity |
| `DELETE` | `/api/cart/{id}/items/{item_id}` | Remove item |
| `POST` | `/api/orders/create` | Create Razorpay order |
| `POST` | `/api/payments/verify` | Verify payment signature |
| `GET` | `/api/metrics` | Live KPI data |
| `GET` | `/api/audit-log` | Agent audit trail |
| `GET` | `/api/chart-data` | Hourly revenue |
| `POST` | `/api/agent/toggle` | Pause / resume agent |
| `POST` | `/api/config/policy` | Update merchant policy |

Full interactive docs → `http://localhost:8000/docs`

---

## 📁 Project Structure

```
Hackthon-RZ/
├── agent-growth-hub-main/         # React frontend
│   └── src/
│       ├── routes/
│       │   ├── index.tsx          # Merchant Dashboard
│       │   └── shop.tsx           # Customer Shop
│       ├── components/
│       │   ├── theme-provider.tsx
│       │   └── theme-toggle.tsx
│       └── lib/
│           └── api.ts             # All API calls
│
└── backend/                       # FastAPI backend
    ├── main.py                    # 18 REST endpoints
    ├── agent.py                   # LangGraph pipeline
    ├── llm.py                     # NVIDIA NIM integration
    ├── catalog.py                 # Product search
    ├── models.py                  # SQLAlchemy models
    ├── audit.py                   # Audit trail
    ├── db.py                      # Database
    └── requirements.txt
```

---

## 👤 Author

<div align="center">

**Saini Nirmal**

BS Data Science & Programming — IIT Madras (2023–2026)

[![LinkedIn](https://img.shields.io/badge/LinkedIn-Connect-0A66C2?style=for-the-badge&logo=linkedin)](https://linkedin.com/in/saini-nirmal-9140ab1b7)
[![GitHub](https://img.shields.io/badge/GitHub-23f1002643-181717?style=for-the-badge&logo=github)](https://github.com/23f1002643)

*Built for Razorpay AI Buildathon 2025 — Track 01: AI Growth & Agentic Commerce*

</div>

---

<div align="center">
Made with ❤️ for the Razorpay AI Buildathon
</div>
