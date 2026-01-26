#!/usr/bin/env python
"""
Development script to simulate Stripe webhooks for testing.
Run this after a successful payment to test webhook functionality.

Usage: python simulate_webhook.py <order_id>
"""

import os
import sys
import json
import requests
from datetime import datetime

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
sys.path.insert(0, os.path.dirname(__file__))

import django
django.setup()

from product.models import Order

def simulate_webhook(order_id):
    """Simulate a Stripe webhook for testing"""
    try:
        order = Order.objects.get(id=order_id)
    except Order.DoesNotExist:
        print(f"Order {order_id} not found")
        return

    if not order.stripe_checkout_session_id:
        print(f"Order {order_id} has no Stripe session ID")
        return

    # Simulate Stripe webhook payload
    webhook_payload = {
        "id": f"evt_test_webhook_{order_id}",
        "object": "event",
        "api_version": "2020-08-27",
        "created": int(datetime.now().timestamp()),
        "data": {
            "object": {
                "id": order.stripe_checkout_session_id,
                "object": "checkout.session",
                "payment_status": "paid",
                "payment_intent": f"pi_test_{order_id}"
            }
        },
        "livemode": False,
        "pending_webhooks": 1,
        "request": {
            "id": f"req_test_{order_id}",
            "idempotency_key": None
        },
        "type": "checkout.session.completed"
    }

    # For local testing, we'll call the webhook endpoint directly
    # In production, Stripe would call this
    try:
        response = requests.post(
            'http://localhost:8000/webhook/',
            json=webhook_payload,
            headers={
                'Content-Type': 'application/json',
                # Note: In real webhooks, Stripe includes a signature header
                # For testing, we're skipping signature verification
            }
        )

        if response.status_code == 200:
            print(f"✅ Webhook simulation successful for order {order_id}")
            # Refresh order from database
            order.refresh_from_db()
            print(f"Order status: {order.status}")
        else:
            print(f"❌ Webhook simulation failed: {response.status_code} - {response.text}")

    except requests.exceptions.RequestException as e:
        print(f"❌ Error calling webhook endpoint: {e}")
        print("Make sure the Django server is running on http://localhost:8000")

if __name__ == '__main__':
    if len(sys.argv) != 2:
        print("Usage: python simulate_webhook.py <order_id>")
        print("Example: python simulate_webhook.py 1")
        sys.exit(1)

    try:
        order_id = int(sys.argv[1])
        simulate_webhook(order_id)
    except ValueError:
        print("Order ID must be a number")
        sys.exit(1)