# Agent Growth Hub

"You are a senior product designer building a professional AI Commerce Agent Dashboard for a fintech hackathon (Razorpay AI Buildathon).

CONTEXT:

This is a merchant-facing dashboard where an AI agent autonomously grows revenue — upsells, conversational checkout, audit trail of every AI action, real-time revenue impact. The evaluators are Razorpay's senior engineering panel. They have high taste and will instantly reject anything that looks templated or generic.

This is NOT a generic SaaS dashboard.

Think: Stripe Dashboard × Linear × Bloomberg Terminal.

Dark. Data-dense. Precise. Trustworthy. Fintech-grade.

---

DESIGN DIRECTION:

Palette:

- Background: #0A0B0F

- Surface: #111318

- Border: #1E2028

- Accent: #4F6EF7 (electric indigo)

- Success: #22C55E

- Warning: #F59E0B

- Text: #F1F5F9 / Muted: #64748B

Typography:

- Inter font throughout

- tabular-nums on all number displays

- Sentence case everywhere. No ALL CAPS labels. No decorative arrows on buttons.

Layout:

- Left sidebar: icon-only collapsed, expandable on hover

- Top bar: Merchant name + Agent status pill (LIVE/PAUSED) + real-time clock

- Main: 3-column grid — Agent Activity Feed | Revenue Metrics | Audit Log

- Use borders and subtle elevation, NOT rounded card soup

Motion:

- Single page-load fade only

- Micro-transition on status pill change only

- No scroll animations

---

BUILD THESE SECTIONS:

1. DASHBOARD HOME

   - Top KPI strip: Revenue Today | Orders | Upsell Accepted | Agent Actions

   - Agent Activity Feed (left): live scrolling list of agent actions with timestamp, action type badge, and outcome (success/failed/pending)

   - Revenue Chart (center): line chart — today's revenue vs yesterday, hour by hour

   - Audit Log (right): every agent decision with reason field visible

2. AGENT CONTROL PANEL

   - Agent status toggle (LIVE / PAUSED) with confirmation modal

   - Configurable limits: max order value, max retries, upsell threshold

   - Last 5 actions summary

3. CHECKOUT SIMULATION VIEW

   - Simulated customer cart (3-4 products)

   - Agent suggestion panel: shows what upsell the agent recommended and why

   - Payment status tracker: Pending → Captured → Logged

---

IMPORTANT RULES:

- No lorem ipsum. Use realistic fintech/merchant data (merchant: "Zephyr Apparel", products: kurtas, ethnic wear)

- No decorative gradients as backgrounds

- No numbered section markers (01, 02) unless it's truly a sequence

- Every empty state should have a direction, not just an illustration

- Errors must say what happened and how to fix it — never vague

- The UI must look like it was built by a team that ships at Stripe or Razorpay internally

Make it production-quality. This is the first impression for an internship panel."   i want ui like razarpay or atlanssian website like. and also like gredient colors similar to lovable website have but i but professional so use gradient coloar professionally also. expecting hybrid theme (light/dark both)  and push code to this repo https://github.com/23f1002643/Hackthon-RZ

This project was built with [Lovable](https://lovable.dev).

## Build with Lovable

Continue developing this project in the [Lovable editor](https://lovable.dev/projects/b47bbcbe-da0a-4567-bb6f-e6453cf74810).

- **Ship faster**: describe what you want to build and Lovable handles the code.
- **Stay in sync**: every change made in Lovable is committed straight to this repository.
- **Full ownership**: this code is yours. Push to `main` on GitHub and your changes sync back into Lovable, ready for your next prompt.

## Development

Prefer working locally? You need Node.js and npm — [install with nvm](https://github.com/nvm-sh/nvm#installing-and-updating).

```sh
git clone <this-repository-url>
cd <repository-name>
npm i
npm run dev
```
