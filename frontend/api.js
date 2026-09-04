const BASE = process.env.REACT_APP_API_BASE || 'http://localhost:8000';

export async function fetchAuditLogs() {
  const res = await fetch(`${BASE}/api/audit-log`);
  if (!res.ok) throw new Error('Failed to fetch audit logs');
  return res.json();
}

export async function fetchMetrics() {
  const res = await fetch(`${BASE}/api/metrics`);
  if (!res.ok) throw new Error('Failed to fetch metrics');
  return res.json();
}

export async function postCheckout(cart, customer, simulate_payment_id=null, accept_upsell=false) {
  const payload = { cart, customer: { ...customer, simulate_payment_id, accept_upsell } };
  const res = await fetch(`${BASE}/api/checkout`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const err = await res.text();
    throw new Error(`Checkout failed: ${err}`);
  }
  return res.json();
}

export async function toggleAgent(action) {
  const res = await fetch(`${BASE}/api/agent/toggle`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ action }),
  });
  if (!res.ok) {
    const err = await res.text();
    throw new Error(`Toggle failed: ${err}`);
  }
  return res.json();
}
