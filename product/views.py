import stripe
import json
from decimal import Decimal
from django.conf import settings
from django.shortcuts import render, redirect
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.contrib import messages
from django.db import transaction
from .models import Product, Order, OrderItem

stripe.api_key = settings.STRIPE_SECRET_KEY


def index(request):
    """Main page showing products and user's paid orders"""
    products = Product.objects.all()

    # Get user's paid orders (by session for anonymous users)
    if request.user.is_authenticated:
        paid_orders = Order.objects.filter(user=request.user, status='paid')
    else:
        session_key = request.session.session_key
        if not session_key:
            request.session.create()
            session_key = request.session.session_key
        paid_orders = Order.objects.filter(session_key=session_key, status='paid')

    context = {
        'products': products,
        'paid_orders': paid_orders,
        'stripe_publishable_key': settings.STRIPE_PUBLISHABLE_KEY,
    }
    return render(request, 'products/index.html', context)




@require_POST
def create_checkout_session(request):
    """Create a Stripe Checkout Session"""
    try:
        # Parse the submitted data
        data = json.loads(request.body)
        cart_items = data.get('items', [])
        
        if not cart_items:
            return JsonResponse({'error': 'Cart is empty'}, status=400)
        
        # Build line items and calculate total
        line_items = []
        total_amount = Decimal('0.00')
        
        with transaction.atomic():
            # Create pending order
            
            if not request.session.session_key:
                request.session.create()

            order = Order.objects.create(
                session_key=request.session.session_key,
                user=request.user if request.user.is_authenticated else None,
                status='pending',
                total_amount=0  # Will update after calculating
            )
            
            # Process each cart item
            for item in cart_items:
                product_id = item.get('product_id')
                quantity = int(item.get('quantity', 0))
                
                if quantity <= 0:
                    continue
                
                try:
                    product = Product.objects.get(id=product_id)
                except Product.DoesNotExist:
                    order.delete()
                    return JsonResponse({'error': f'Product {product_id} not found'}, status=404)
                
                # Create order item
                OrderItem.objects.create(
                    order=order,
                    product=product,
                    quantity=quantity,
                    price=product.price
                )
                
                # Add to Stripe line items
                line_items.append({
                    'price_data': {
                        'currency': 'usd',
                        'unit_amount': product.price_in_cents,
                        'product_data': {
                            'name': product.name,
                            'description': product.description,
                        },
                    },
                    'quantity': quantity,
                })
                
                total_amount += product.price * quantity
            
            # Update order total
            order.total_amount = total_amount
            order.save()
            
            # Create Stripe Checkout Session
            checkout_session = stripe.checkout.Session.create(
                payment_method_types=['card'],
                line_items=line_items,
                mode='payment',
                success_url=request.build_absolute_uri('/success/') + '?session_id={CHECKOUT_SESSION_ID}',
                cancel_url=request.build_absolute_uri('/') + '?cancelled=true',
                client_reference_id=str(order.id),
                metadata={
                    'order_id': order.id,
                }
            )
            
            # Save session ID to order
            order.stripe_checkout_session_id = checkout_session.id
            order.save()
            
            return JsonResponse({'sessionId': checkout_session.id})
            
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


def success(request):
    """Handle successful payment"""
    session_id = request.GET.get('session_id')
    
    if not session_id:
        messages.error(request, 'Invalid session')
        return redirect('index')
    
    try:
        # Retrieve the session from Stripe
        checkout_session = stripe.checkout.Session.retrieve(session_id)
        
        # Find the order
        order = Order.objects.get(stripe_checkout_session_id=session_id)
        
        # Update order status if payment succeeded
        if checkout_session.payment_status == 'paid' and order.status != 'paid':
            order.status = 'paid'
            order.stripe_payment_intent_id = checkout_session.payment_intent
            order.save()
            messages.success(request, f'Payment successful! Order #{order.id} confirmed.')
        
        return redirect('index')
        
    except Order.DoesNotExist:
        messages.error(request, 'Order not found')
        return redirect('index')
    except stripe.error.StripeError as e:
        messages.error(request, f'Stripe error: {str(e)}')
        return redirect('index')


@csrf_exempt
@require_POST
def stripe_webhook(request):
    """Handle Stripe webhooks for payment events"""
    payload = request.body
    sig_header = request.META.get('HTTP_STRIPE_SIGNATURE')

    # In development, allow unsigned webhooks for testing
    if settings.DEBUG and not sig_header:
        # Parse the payload directly for testing
        try:
            event = json.loads(payload)
        except json.JSONDecodeError:
            return HttpResponse(status=400)
    else:
        # Production: verify signature
        try:
            event = stripe.Webhook.construct_event(
                payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
            )
        except ValueError:
            return HttpResponse(status=400)
        except stripe.error.SignatureVerificationError:
            return HttpResponse(status=400)

    # Handle the checkout.session.completed event
    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']

        # Fulfill the purchase
        try:
            order = Order.objects.get(stripe_checkout_session_id=session['id'])
            if order.status != 'paid':
                order.status = 'paid'
                order.stripe_payment_intent_id = session.get('payment_intent')
                order.save()
        except Order.DoesNotExist:
            pass

    return HttpResponse(status=200)