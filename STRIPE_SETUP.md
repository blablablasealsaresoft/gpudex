# Stripe Setup Guide for GPUDex

Complete guide to set up Stripe for your GPUDex platform - both subscriptions and one-time GPU rentals.

## 📋 **Step 1: Create Stripe Account**

1. Go to https://dashboard.stripe.com/register
2. Create your account and complete verification
3. Switch to **Live Mode** (top right toggle) for production

## 🔑 **Step 2: Get API Keys**

1. Go to **Developers > API keys**
2. Copy these values to your `.env` file:

```bash
# From Stripe Dashboard > API Keys
STRIPE_SECRET_KEY=sk_live_51ABC123...  # Secret key (starts with sk_live_)
STRIPE_PUBLISHABLE_KEY=pk_live_51ABC123...  # Publishable key (starts with pk_live_)
```

## 💰 **Step 3: Create Subscription Products**

### **Create Products in Stripe Dashboard:**

1. Go to **Products > Add Product**
2. Create these 3 subscription products:

#### **Starter Plan**
- **Name**: GPUDex Starter Plan
- **Price**: $29.00 USD / month
- **Billing**: Recurring monthly
- **Copy the Price ID**: `price_1ABC123...`

#### **Pro Plan**  
- **Name**: GPUDex Pro Plan
- **Price**: $99.00 USD / month
- **Billing**: Recurring monthly
- **Copy the Price ID**: `price_1ABC123...`

#### **Enterprise Plan**
- **Name**: GPUDex Enterprise Plan  
- **Price**: $499.00 USD / month
- **Billing**: Recurring monthly
- **Copy the Price ID**: `price_1ABC123...`

### **Add Price IDs to .env:**
```bash
STRIPE_STARTER_PRICE_ID=price_1ABC123_starter
STRIPE_PRO_PRICE_ID=price_1ABC123_pro
STRIPE_ENTERPRISE_PRICE_ID=price_1ABC123_enterprise
```

## 🖥️ **Step 4: Create GPU Rental Product**

1. **Products > Add Product**
2. **Name**: GPU Rental (Hourly)
3. **Pricing Model**: One-time payment
4. **Price**: $0.01 (we'll set dynamic pricing in code)
5. **Copy Product ID**: `prod_ABC123...`

```bash
STRIPE_GPU_RENTAL_PRODUCT_ID=prod_ABC123_gpu_rental
```

## 🪝 **Step 5: Set Up Webhooks**

1. Go to **Developers > Webhooks**
2. **Add endpoint**: `https://yourdomain.com/webhook/stripe`
3. **Select events**:
   - `invoice.payment_succeeded`
   - `invoice.payment_failed` 
   - `customer.subscription.created`
   - `customer.subscription.updated`
   - `customer.subscription.deleted`
   - `payment_intent.succeeded`
   - `payment_intent.payment_failed`

4. **Copy Webhook Secret**: `whsec_ABC123...`

```bash
STRIPE_WEBHOOK_SECRET=whsec_ABC123_your_webhook_secret
```

## 🧪 **Step 6: Test Your Setup**

### **Test with JavaScript (since Python not working):**

Create `test-stripe.js`:
```javascript
const stripe = require('stripe')('sk_test_your_test_key');

async function testStripe() {
  try {
    // Test creating a customer
    const customer = await stripe.customers.create({
      email: 'test@example.com',
      name: 'Test Customer'
    });
    console.log('✅ Customer created:', customer.id);
    
    // Test retrieving products
    const products = await stripe.products.list();
    console.log('✅ Products found:', products.data.length);
    
    console.log('🎉 Stripe setup working!');
  } catch (error) {
    console.error('❌ Stripe error:', error.message);
  }
}

testStripe();
```

Run: `node test-stripe.js`

## 📊 **Step 7: Configure Rate Limits**

In your Stripe Dashboard:

1. **Settings > Billing**
2. Set up usage-based billing for API calls:
   - **Free**: 1,000 requests/month
   - **Starter**: 10,000 requests/month  
   - **Pro**: 100,000 requests/month
   - **Enterprise**: Unlimited

## 🔒 **Step 8: Security Settings**

1. **Developers > API keys > Restricted keys**
2. Create restricted keys for production:
   - **Read/Write** access to: Customers, Subscriptions, Payment Intents
   - **Read only** access to: Products, Prices

## 💡 **Step 9: Tax Configuration (Optional)**

If you need to collect tax:

1. **Settings > Tax**
2. Enable **Stripe Tax**
3. Configure tax rates for your jurisdiction

## 🚀 **Step 10: Go Live!**

1. **Complete account verification** (if not done)
2. **Switch to Live mode** 
3. **Update your .env** with live keys
4. **Test a small transaction** ($1)
5. **Monitor the dashboard** for incoming payments

## 📈 **Expected Revenue Flow**

With your setup:
- **Subscription Revenue**: $29-$499/month per customer
- **GPU Rental Revenue**: 3% of each transaction (via smart contract)
- **Stripe Fees**: ~2.9% + $0.30 per transaction

## 🛠️ **Integration with GPUDex**

Your platform will automatically:

1. **Charge subscriptions** monthly via Stripe
2. **Process GPU rentals** via crypto (smart contract gets 3%)
3. **Handle fiat payments** for customers without crypto
4. **Manage upgrades/downgrades** automatically

## 📞 **Support**

- **Stripe Docs**: https://stripe.com/docs
- **Test Cards**: https://stripe.com/docs/testing#cards
- **Webhook Testing**: Use Stripe CLI or ngrok for local testing

---

**Your Stripe integration is ready when you see successful test transactions in your dashboard!** 🎉 