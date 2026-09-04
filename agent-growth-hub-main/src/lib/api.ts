const BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8000';

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

export async function fetchChartData() {
  const res = await fetch(`${BASE}/api/chart-data`);
  if (!res.ok) throw new Error('Failed to fetch chart data');
  return res.json();
}

export async function fetchNotifications() {
  const res = await fetch(`${BASE}/api/notifications`);
  if (!res.ok) throw new Error('Failed to fetch notifications');
  return res.json();
}

export async function postCheckout(cart: any[], customer: any) {
  const res = await fetch(`${BASE}/api/checkout`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ cart, customer }),
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(text || 'Checkout failed');
  }
  return res.json();
}

export async function toggleAgent(action: 'pause' | 'resume') {
  const res = await fetch(`${BASE}/api/agent/toggle`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ action }),
  });
  if (!res.ok) throw new Error('Toggle failed');
  return res.json();
}

export default { fetchAuditLogs, fetchMetrics, fetchChartData, fetchNotifications, postCheckout, toggleAgent };
