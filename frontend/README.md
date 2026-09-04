Integration snippets — import functions from `api.js` into your React components.

Agent Activity Feed (poll every 5s):

```js
import { useEffect, useState } from 'react';
import { fetchAuditLogs } from './api';

function ActivityFeed() {
  const [logs, setLogs] = useState([]);

  useEffect(() => {
    let mounted = true;
    async function poll() {
      try {
        const data = await fetchAuditLogs();
        if (mounted) setLogs(data.logs || []);
      } catch (e) {
        console.error(e);
      }
    }
    poll();
    const id = setInterval(poll, 5000);
    return () => { mounted = false; clearInterval(id); };
  }, []);

  return (
    <div>
      {logs.map((l, i) => (
        <div key={i}>{l.timestamp} — {l.action} — {l.reason}</div>
      ))}
    </div>
  );
}
```

KPI strip (fetch on mount):

```js
import { useEffect, useState } from 'react';
import { fetchMetrics } from './api';

function KPIStrip() {
  const [metrics, setMetrics] = useState({ revenue: 0, order_count: 0, upsell_acceptance_rate: 0});

  useEffect(() => {
    async function load() {
      const m = await fetchMetrics();
      setMetrics(m);
    }
    load();
  }, []);

  return (
    <div>
      <span>Revenue: ₹{metrics.revenue}</span>
      <span>Orders: {metrics.order_count}</span>
      <span>Upsell rate: {metrics.upsell_acceptance_rate}%</span>
    </div>
  );
}
```

Checkout Simulation (call on button click):

```js
import { postCheckout } from './api';

async function simulateCheckout(cart) {
  const customer = { name: 'Test Buyer', email: 'test@example.com', contact: '9999999999' };
  const result = await postCheckout(cart, customer, null, false);
  console.log(result);
}
```

Agent Toggle button:

```js
import { toggleAgent } from './api';

async function toggle(action) {
  const res = await toggleAgent(action); // action = 'pause'|'resume'
  console.log(res);
}
```

Add `REACT_APP_API_BASE` to your `.env` for dev if your backend runs on a different host/port.
