"""FastAPI backend for the Commerce Agent.

Endpoints:
- POST /api/checkout
- GET  /api/audit-log
- GET  /api/metrics
- POST /api/agent/toggle

Run with:
    uvicorn backend.main:app --reload --port 8000
"""
from datetime import datetime, timezone
from typing import Any, Dict

from fastapi import Body, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse

from . import agent as ag, audit


app = FastAPI()

# allow requests from React dev server
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# in-memory agent toggling
AGENT_PAUSED = False


@app.get("/")
async def root():
    return {"status": "backend ready"}


@app.post("/api/checkout")
async def checkout(payload: Dict[str, Any] = Body(...)):
    global AGENT_PAUSED
    if AGENT_PAUSED:
        raise HTTPException(status_code=503, detail="Agent is paused")

    cart = payload.get("cart", [])
    customer = payload.get("customer", {})

    # run agent flow
    try:
        result = ag.agent.run_full_flow(cart, customer)
        return {"ok": True, "result": result}
    except Exception as e:
        # log failure
        audit.append_log({"timestamp": datetime.utcnow().isoformat() + "Z", "action": "checkout_error", "error": str(e)})
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/audit-log")
async def get_audit():
    return {"logs": audit.get_recent(50)}


def _is_today(ts: str) -> bool:
    try:
        dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        now = datetime.now(timezone.utc)
        return dt.date() == now.date()
    except Exception:
        return False


@app.get("/api/metrics")
async def get_metrics():
    logs = audit.get_recent(1000)
    revenue = 0.0
    orders = 0
    upsell_offered = 0
    upsell_accepted = 0
    for e in logs:
        ts = e.get("timestamp")
        if not ts or not _is_today(ts):
            continue
        action = e.get("action")
        if action == "capture_payment":
            # attempt to read amount
            amt = 0
            try:
                outputs = e.get("outputs", {})
                raw = outputs.get("raw") if isinstance(outputs, dict) else None
                if isinstance(raw, dict) and raw.get("amount"):
                    amt = raw.get("amount") / 100.0
                else:
                    amt = outputs.get("amount", 0)
            except Exception:
                amt = 0
            revenue += float(amt or 0)
        if action == "create_order":
            orders += 1
        if action == "upsell_decision":
            if e.get("outputs", {}).get("decision"):
                upsell_offered += 1
        if action == "upsell_accepted":
            upsell_accepted += 1

    upsell_rate = (upsell_accepted / upsell_offered * 100.0) if upsell_offered else 0.0
    return {"revenue": revenue, "order_count": orders, "upsell_acceptance_rate": upsell_rate}


@app.post("/api/agent/toggle")
async def toggle_agent(payload: Dict[str, Any] = Body(...)):
    global AGENT_PAUSED
    action = payload.get("action")
    if action == "pause":
        AGENT_PAUSED = True
    elif action == "resume":
        AGENT_PAUSED = False
    else:
        raise HTTPException(status_code=400, detail="action must be 'pause' or 'resume'")
    return {"agent_paused": AGENT_PAUSED}


@app.get("/demo", response_class=HTMLResponse)
async def demo_page():
        html = """
        <!doctype html>
        <html>
        <head>
            <meta charset="utf-8" />
            <title>Zephyr Demo</title>
            <style>body{font-family:system-ui,Segoe UI,Roboto,Helvetica,Arial;margin:24px}button{margin:6px;padding:8px 12px}</style>
        </head>
        <body>
            <h2>Zephyr Apparel — Demo</h2>
            <div>
                <button id="run">Run checkout simulation</button>
                <button id="audit">Load audit log</button>
                <button id="metrics">Load metrics</button>
                <button id="toggle">Toggle agent</button>
            </div>
            <pre id="out" style="white-space:pre-wrap;margin-top:12px;background:#f7f7f7;padding:12px;border-radius:6px"></pre>
            <script>
                const out = document.getElementById('out')
                function log(v){ out.textContent = JSON.stringify(v, null, 2) }
                document.getElementById('run').onclick = async () => {
                    log({status:'running'})
                    const cart = [{name:'Hand-block printed kurta', price:2499, qty:1},{name:'Chanderi silk dupatta', price:1299, qty:1}]
                    const customer = {name:'Sim Buyer', email:'sim@zephyr.com', contact:'9999999999'}
                    const res = await fetch('/api/checkout',{method:'POST',headers:{'content-type':'application/json'},body:JSON.stringify({cart,customer})})
                    log(await res.json())
                }
                document.getElementById('audit').onclick = async () => { const res = await fetch('/api/audit-log'); log(await res.json()) }
                document.getElementById('metrics').onclick = async () => { const res = await fetch('/api/metrics'); log(await res.json()) }
                document.getElementById('toggle').onclick = async () => {
                    const action = confirm('Pause agent? OK = pause, Cancel = resume') ? 'pause' : 'resume'
                    const res = await fetch('/api/agent/toggle', {method:'POST',headers:{'content-type':'application/json'},body:JSON.stringify({action})})
                    log(await res.json())
                }
            </script>
        </body>
        </html>
        """
        return HTMLResponse(content=html)
