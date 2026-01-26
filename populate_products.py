#!/usr/bin/env python
"""
Script to populate the database with sample products.
Run this after migrations: python populate_products.py
"""

import os
import django
from decimal import Decimal

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from product.models import Product

def create_sample_products():
    """Create three sample products for the store"""
    products_data = [
        {
            'name': 'Wireless Bluetooth Headphones',
            'description': 'High-quality wireless headphones with noise cancellation and 30-hour battery life.',
            'price': Decimal('99.99')
        },
        {
            'name': 'Smart Fitness Watch',
            'description': 'Track your workouts, heart rate, and sleep with this advanced fitness watch.',
            'price': Decimal('199.99')
        },
        {
            'name': 'Portable Power Bank',
            'description': '20000mAh power bank with fast charging and multiple USB ports.',
            'price': Decimal('49.99')
        }
    ]

    for product_data in products_data:
        product, created = Product.objects.get_or_create(
            name=product_data['name'],
            defaults=product_data
        )
        if created:
            print(f"Created product: {product.name}")
        else:
            print(f"Product already exists: {product.name}")

if __name__ == '__main__':
    create_sample_products()
    print("Sample products created successfully!")