# Django Stripe Shop

A Django application that allows users to purchase products using Stripe payment processing.

## Features

- Display of three fixed products
- Shopping cart functionality
- Stripe Checkout integration (test mode)
- Order management and display
- Prevention of double-submission and refresh issues
- PostgreSQL database backend

## Assumptions Made

1. **User Authentication**: The application supports both authenticated and anonymous users. Anonymous users are tracked via Django session keys.
2. **Product Catalog**: Products are fixed and managed through Django admin. The application assumes three products will be created.
3. **Payment Flow**: Single-page application where users add items to cart, checkout via Stripe, and return to see their orders.
4. **Order Status**: Orders can be pending, paid, failed, or cancelled.
5. **Currency**: All prices are in USD.
6. **Environment**: Development environment with debug mode enabled.

## Stripe Flow Chosen

**Stripe Checkout Session** was chosen over Payment Intents for the following reasons:

1. **Simplicity**: Checkout Sessions handle the entire payment flow automatically, including redirecting users to Stripe's hosted checkout page.
2. **Security**: Stripe manages sensitive payment information on their servers, reducing PCI compliance requirements.
3. **User Experience**: Provides a consistent, professional checkout experience that users trust.
4. **Webhook Integration**: Supports webhooks for payment confirmation, ensuring order status is updated even if users close the browser.
5. **Session Management**: Each checkout session is uniquely tied to an order, preventing double charges.

## Double Charge Prevention

Several mechanisms prevent double charges and inconsistent states:

1. **Database Transactions**: Order creation and item processing are wrapped in atomic transactions.
2. **Unique Session IDs**: Each Stripe checkout session is uniquely linked to one order via `stripe_checkout_session_id`.
3. **Status Checks**: Orders are only marked as paid if Stripe confirms payment and the order isn't already paid.
4. **Webhook Verification**: Webhooks verify payment completion server-side, independent of user actions.
5. **CSRF Protection**: POST requests are protected against cross-site request forgery.
6. **Session-Based Tracking**: Anonymous users are tracked by session, preventing order confusion.

## Setup and Run Steps

### Prerequisites

- Python 3.8+
- PostgreSQL (running locally for non-Docker setup)
- Stripe account with test keys

### Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd code_assignment
   ```

2. **Create virtual environment**
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Environment setup**
   ```bash
   cp .env.example .env
   # Edit .env with your actual values
   ```

5. **Database setup**
   ```bash
   # Create PostgreSQL database
   createdb stripe_shop

   # Run migrations
   python manage.py migrate
   ```

6. **Create products**
   ```bash
   python populate_products.py
   ```
   Or manually:
   ```bash
   python manage.py shell
   ```
   ```python
   from product.models import Product
   from decimal import Decimal
   Product.objects.create(name="Wireless Bluetooth Headphones", description="High-quality wireless headphones with noise cancellation and 30-hour battery life.", price=Decimal('99.99'))
   Product.objects.create(name="Smart Fitness Watch", description="Track your workouts, heart rate, and sleep with this advanced fitness watch.", price=Decimal('199.99'))
   Product.objects.create(name="Portable Power Bank", description="20000mAh power bank with fast charging and multiple USB ports.", price=Decimal('49.99'))
   exit()
   ```

7. **Run the application**
   ```bash
   python manage.py runserver
   ```

8. **Access the application**
   - Open http://localhost:8000 in your browser

9. **Optional: Setup webhooks for payment confirmation**
   - See "Webhook Configuration for Development" section below

### Docker Setup (Optional)

If you prefer using Docker:

1. **Ensure Docker and Docker Compose are installed**

2. **Create environment file for Docker**
   ```bash
   cp .env.example .env
   # Edit .env with your Stripe keys (DB_* variables will be overridden by docker-compose)
   ```

3. **Build and run with Docker Compose**
   ```bash
   docker-compose up --build
   ```

4. **Access the application**
   - Open http://localhost:8000 in your browser
   - Sample products are automatically created on first run

5. **Optional: Create admin user for testing**
   ```bash
   python manage.py createsuperuser
   ```
   Access admin at http://localhost:8000/admin/

## Code Quality Notes

- **Separation of Concerns**: Views handle HTTP logic, models manage data, templates handle presentation.
- **Error Handling**: Comprehensive try-catch blocks with appropriate HTTP status codes.
- **Security**: CSRF protection, secure key management via environment variables.
- **Database Design**: Proper relationships between Order, OrderItem, and Product models.
- **Frontend**: Bootstrap for responsive design, vanilla JavaScript for cart functionality.
- **Stripe Integration**: Proper error handling and webhook verification.
- **Code Style**: Follows Django conventions and PEP 8 standards.

## API Endpoints

- `GET /` - Main page with products and orders
- `POST /create-checkout-session/` - Create Stripe checkout session
- `GET /success/` - Payment success handler
- `POST /webhook/` - Stripe webhook handler

## Testing Stripe Payments

Use Stripe test card numbers:
- Success: `4242 4242 4242 4242`
- Declined: `4000 0000 0000 0002`

## Webhook Configuration for Development

Since the application runs in Docker containers, webhooks won't work out-of-the-box because Stripe can't reach your local containers. Here are several solutions:

### Option 1: Use Stripe CLI (Recommended)

1. **Install Stripe CLI**:
   ```bash
   # Download from https://stripe.com/docs/stripe-cli
   # Or use npm: npm install -g stripe
   ```

2. **Login to Stripe**:
   ```bash
   stripe login
   ```

3. **Forward webhooks to your Docker container**:
   ```bash
   stripe listen --forward-to localhost:8000/webhook/
   ```

4. **Copy the webhook signing secret** from the CLI output and update your `.env` file:
   ```
   STRIPE_WEBHOOK_SECRET=whsec_...
   ```

### Option 2: Use ngrok

1. **Install ngrok**:
   ```bash
   # Download from https://ngrok.com/download
   ```

2. **Start ngrok tunnel**:
   ```bash
   ngrok http 8000
   ```

3. **Copy the ngrok URL** (e.g., `https://abc123.ngrok.io`) and configure it in your Stripe Dashboard webhook settings.

4. **Update ALLOWED_HOSTS** in your `.env`:
   ```
   ALLOWED_HOSTS=localhost,127.0.0.1,web,abc123.ngrok.io
   ```

### Option 3: Run Webhook Handler Outside Docker

For testing webhooks, you can run the Django development server outside Docker:

1. **Start only the database with Docker**:
   ```bash
   docker-compose up db
   ```

2. **Run Django locally**:
   ```bash
   python manage.py runserver
   ```

3. **Use ngrok or Stripe CLI** as above to expose port 8000.

### Option 4: Manual Webhook Testing (Basic)

For basic testing without external tools, you can manually update order status:

1. **After successful payment**, check the order status in Django admin
2. **Access Django admin**: http://localhost:8000/admin/
3. **Login credentials**: Create a superuser first with `python manage.py createsuperuser`
4. **Manually mark orders as paid** if needed for testing

**Note**: This method doesn't test actual webhook delivery but allows you to verify the webhook handler logic.

### Option 5: Simulate Webhooks with Script

Use the included simulation script for testing webhook logic:

1. **After a successful payment**, note the order ID from the success page
2. **Run the simulation script**:
   ```bash
   python simulate_webhook.py <order_id>
   ```
3. **Check that the order status updates** to "paid"

This simulates the webhook payload that Stripe would send, allowing you to test the webhook handler without external tools.

## Production Deployment

For production deployment:
1. Set `DEBUG=False`
2. Use production Stripe keys
3. Configure proper `ALLOWED_HOSTS`
4. Set up proper database credentials
5. Use a production WSGI server (gunicorn)
6. Configure HTTPS
7. Set up proper logging