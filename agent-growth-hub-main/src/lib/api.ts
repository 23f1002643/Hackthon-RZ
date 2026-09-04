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

async function request(path: string, init?: RequestInit) {
  const res = await fetch(`${BASE}${path}`, init);
  const payload = await res.json().catch(() => ({}));
  if (!res.ok || payload.success === false) throw new Error(payload?.error?.message || 'Request failed');
  return payload;
}

export async function createCart(budget?: number, aiAssisted = false) {
  return request('/api/cart', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ budget, ai_assisted: aiAssisted }),
  });
}

export async function searchShop(query: string) {
  return request('/api/shop/search', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ query }),
  });
}

export async function addCartItem(cartId: number, productId: number, isUpsell = false) {
  return request(`/api/cart/${cartId}/items`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ product_id: productId, quantity: 1, is_upsell: isUpsell }) });
}

export async function createOrder(cartId: number, confirmed: boolean) {
  return request('/api/orders/create', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ cart_id: cartId, confirmed }) });
}

export async function verifyPayment(orderId: number, payment: { razorpay_payment_id: string; razorpay_order_id: string; razorpay_signature: string }) {
  return request('/api/payments/verify', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ order_id: orderId, ...payment }) });
}

export async function markPaymentFailed(orderId: number, reason: string) {
  return request('/api/payments/failed', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ order_id: orderId, reason }) });
}

export async function toggleAgent(active: boolean) {
  return request('/api/agent/toggle', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ active }) });
}

export default { fetchAuditLogs, fetchMetrics, fetchChartData, fetchNotifications, createCart, searchShop, addCartItem, createOrder, verifyPayment, markPaymentFailed, toggleAgent };
