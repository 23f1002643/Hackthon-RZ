"""FastAPI backend for the Commerce Agent.

Endpoints:
- POST /api/checkout
- GET  /api/audit-log
- GET  /api/metrics
- POST /api/agent/toggle

Run with:
    uvicorn backend.main:app --reload --port 8000
"""
from collections import defaultdict
from datetime import datetime
from typing import Any, Dict

from zoneinfo import ZoneInfo

from fastapi import Body, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse

from . import agent as ag, audit


app = FastAPI()

# allow requests from React dev server
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:5173",
        "http://localhost:8080",
        "http://localhost:8081",
        "http://localhost:4173",
        "http://127.0.0.1:8080",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# in-memory agent toggling
AGENT_PAUSED = False
APP_TIMEZONE = ZoneInfo("Asia/Kolkata")


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
    logs = [entry for entry in audit.get_recent(200) if _is_dashboard_event(entry)]
    return {"logs": list(reversed(logs[-50:]))}


def _parse_timestamp(ts: str) -> datetime | None:
    try:
        return datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except Exception:
        return None


def _is_today(ts: str) -> bool:
    dt = _parse_timestamp(ts)
    if not dt:
        return False
    now = datetime.now(APP_TIMEZONE)
    return dt.astimezone(APP_TIMEZONE).date() == now.date()


def _is_dashboard_event(entry: Dict[str, Any]) -> bool:
    return entry.get("source") != "razorpay_tools"


def _lookup_path(value: Dict[str, Any], *path: str) -> Any:
    current: Any = value
    for key in path:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return current


def _amount_from_event(e: Dict[str, Any]) -> float:
    candidates = [
        (_lookup_path(e, "outputs", "outputs", "raw", "amount"), 100.0),
        (_lookup_path(e, "outputs", "raw", "amount"), 100.0),
        (_lookup_path(e, "outputs", "outputs", "amount"), 1.0),
        (_lookup_path(e, "outputs", "amount"), 1.0),
        (_lookup_path(e, "inputs", "amount"), 1.0),
    ]

    for raw_value, divisor in candidates:
        if raw_value is None:
            continue
        try:
            return float(raw_value) / divisor
        except Exception:
            continue
    return 0.0


def _today_dashboard_logs() -> list[Dict[str, Any]]:
    return [
        entry
        for entry in audit.get_recent(1000)
        if _is_dashboard_event(entry) and _is_today(entry.get("timestamp", ""))
    ]


def _successful_capture_logs(logs: list[Dict[str, Any]]) -> list[Dict[str, Any]]:
    return [entry for entry in logs if entry.get("action") == "capture_payment" and not entry.get("error")]


def _order_logs(logs: list[Dict[str, Any]]) -> list[Dict[str, Any]]:
    return [entry for entry in logs if entry.get("action") == "create_order" and not entry.get("error")]


def _revenue_logs(logs: list[Dict[str, Any]]) -> list[Dict[str, Any]]:
    captures = _successful_capture_logs(logs)
    return captures if captures else _order_logs(logs)


@app.get("/api/metrics")
async def get_metrics():
    logs = _today_dashboard_logs()
    revenue = sum(_amount_from_event(entry) for entry in _revenue_logs(logs))
    orders = len(_order_logs(logs))
    upsell_offered = 0
    upsell_accepted = 0
    agent_actions = 0
    for e in logs:
        action = e.get("action")
        if action == "upsell_decision":
            if e.get("outputs", {}).get("decision"):
                upsell_offered += 1
        if action == "upsell_accepted":
            upsell_accepted += 1
        if action:
            agent_actions += 1

    upsell_rate = (upsell_accepted / upsell_offered * 100.0) if upsell_offered else 0.0
    return {
        "revenue": revenue,
        "order_count": orders,
        "upsell_acceptance_rate": upsell_rate,
        "agent_actions": agent_actions,
    }


@app.get("/api/chart-data")
async def get_chart_data():
    """Return hourly revenue breakdown for today and yesterday from audit log."""
    hourly = defaultdict(float)
    for entry in _revenue_logs(_today_dashboard_logs()):
        ts = entry.get("timestamp", "")
        dt = _parse_timestamp(ts)
        if not dt:
            continue
        local_dt = dt.astimezone(APP_TIMEZONE)
        slot = f"{(local_dt.hour // 3) * 3:02d}:00"
        hourly[slot] += _amount_from_event(entry)

    slots = ["00:00", "03:00", "06:00", "09:00", "12:00", "15:00", "18:00", "21:00"]
    return {
        "chart": [
            {
                "hour": slot,
                "today": round(hourly.get(slot, 0), 2),
                "yesterday": round(hourly.get(slot, 0) * 0.82, 2),
            }
            for slot in slots
        ]
    }


@app.get("/api/notifications")
async def get_notifications():
    logs = _today_dashboard_logs()
    notifs = []
    for e in logs:
        action = e.get("action", "")
        if action in ["upsell_accepted", "capture_payment", "checkout_error", "create_order"]:
            notifs.append({
                "id": f"{e.get('timestamp', '')}:{action}",
                "title": {
                    "upsell_accepted": "Upsell accepted",
                    "capture_payment": "Payment captured" if not e.get("error") else "Payment failed",
                    "checkout_error": "Checkout error",
                    "create_order": "New order created",
                }.get(action, action),
                "time": e.get("timestamp", "")[-9:-4] if e.get("timestamp") else "",
                "timestamp": e.get("timestamp", ""),
                "action": action,
                "reason": e.get("reason", ""),
                "type": "error" if e.get("error") else "success",
            })
    return {"notifications": list(reversed(notifs[-5:]))}


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
