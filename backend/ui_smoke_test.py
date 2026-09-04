import requests
import json

BASE = "http://127.0.0.1:8000"

def get_demo():
    r = requests.get(BASE + "/demo")
    return r.status_code, r.text[:200]

def run_checkout():
    payload={
        "cart":[{"name":"Hand-block printed kurta","price":2499,"qty":1},{"name":"Chanderi silk dupatta","price":1299,"qty":1}],
        "customer":{"name":"Sim Buyer","email":"sim@zephyr.com","contact":"9999999999"}
    }
    r = requests.post(BASE + "/api/checkout", json=payload, timeout=30)
    return r.status_code, r.json()

def get_audit():
    r = requests.get(BASE + "/api/audit-log")
    return r.status_code, r.json()

def get_metrics():
    r = requests.get(BASE + "/api/metrics")
    return r.status_code, r.json()

def toggle_agent(action):
    r = requests.post(BASE + "/api/agent/toggle", json={"action": action})
    return r.status_code, r.json()

def main():
    out = {}
    out['demo'] = get_demo()
    out['checkout'] = run_checkout()
    out['audit'] = get_audit()
    out['metrics'] = get_metrics()
    out['pause'] = toggle_agent('pause')
    out['resume'] = toggle_agent('resume')
    print(json.dumps(out, indent=2, default=str))

if __name__ == '__main__':
    main()
