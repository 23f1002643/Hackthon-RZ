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

export async function fetchConfig() { return request('/api/config'); }

export async function fetchCustomers() { return request('/api/customers'); }
export async function fetchOrders() { return request('/api/orders'); }
export async function fetchProducts(query = '') { return request(`/api/products?q=${encodeURIComponent(query)}&limit=100`); }
export async function importCatalog(source: 'dummyjson' | 'brightdata' = 'brightdata') { return request(`/api/catalog/import?source=${source}`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({}) }); }
export async function createProduct(product: Record<string, unknown>) { return request('/api/products', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(product) }); }

async function request(path: string, init?: RequestInit) {
  const res = await fetch(`${BASE}${path}`, init);
  const payload = await res.json().catch(() => ({}));
  if (!res.ok || payload.success === false) throw new Error(payload?.error?.message || 'Request failed');
  return payload;
}

export async function createCart(budget?: number, aiAssisted = false, customerId?: number) {
  return request('/api/cart', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ budget, ai_assisted: aiAssisted, customer_id: customerId }),
  });
}

export async function getCart(cartId: number) {
  return request(`/api/cart/${cartId}`);
}

export async function getOrCreateCustomer(customer: { name: string; email: string; contact?: string }) {
  return request('/api/customers', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(customer) });
}

export async function fetchCustomerOrders(customerId: number) {
  return request(`/api/customers/${customerId}/orders`);
}

export async function searchShop(query: string, context: string[] = []) {
  return request('/api/shop/search', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ query, context }),
  });
}

export async function addCartItem(cartId: number, productId: number, isUpsell = false) {
  return request(`/api/cart/${cartId}/items`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ product_id: productId, quantity: 1, is_upsell: isUpsell }) });
}

export async function removeCartItem(cartId: number, itemId: number) {
  return request(`/api/cart/${cartId}/items/${itemId}`, { method: 'DELETE' });
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

export default { fetchAuditLogs, fetchMetrics, fetchChartData, fetchNotifications, fetchConfig, fetchCustomers, fetchOrders, fetchProducts, importCatalog, createProduct, createCart, getCart, getOrCreateCustomer, fetchCustomerOrders, searchShop, addCartItem, removeCartItem, createOrder, verifyPayment, markPaymentFailed, toggleAgent };
