"""Demo: show graceful payment capture failure handling.

Run:
    python -m backend.demo_payment_failure

This script will run the agent flow with a simulated invalid payment id so capture_payment fails
and the agent logs the failure and stops.
"""
import json

from backend import agent, audit


def main():
    cart = [
        {"name": "Kurta", "price": 1200.0, "qty": 1},
        {"name": "Ethnic Wear", "price": 800.0, "qty": 1},
    ]
    customer = {
        "name": "Demo Buyer",
        "email": "demo@zephyr.com",
        "contact": "9999999999",
        # use an invalid payment id to force capture failure in Razorpay SDK
        "simulate_payment_id": "invalid_payment_demo_123",
        "accept_upsell": True,
    }

    print("Running demo checkout flow (expect capture failure)...")
    res = agent.agent.run_full_flow(cart, customer)
    print(json.dumps(res, indent=2))

    print("\nRecent audit logs (last 10):")
    for e in audit.get_recent(10):
        print(json.dumps(e, indent=2))


if __name__ == "__main__":
    main()
