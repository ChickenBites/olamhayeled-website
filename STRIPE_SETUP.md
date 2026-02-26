# Stripe & Supabase Setup Guide

## Cheapest Way to Add Billing to Your Netlify Site

**Cost:**
- Netlify: Free (your current hosting)
- Stripe: Free to set up, ~3.4% per transaction
- Supabase: Free tier (500MB database)

---

## Payment Options Explained

### 1. Credit Card (כרטיס אשראי) ✅
**Status**: Fully supported with Stripe
- Works with all Israeli cards (Visa, Mastercard, Isracard)
- Automatic monthly recurring payments
- ~3.4% + ₪1.20 per transaction

### 2. Standing Order (הוראת קבע) ⚠️
**Status**: Manual process (no direct bank integration)

Stripe doesn't support Israeli direct debit (הוראת קבע). **Options:**

#### Option A: Keep as Manual Sign-Up (Recommended for Free)
1. Parent fills bank details on your site
2. You receive the details via email/WhatsApp
3. You manually set up standing order in your bank
4. Parent confirms when they receive bank notification

#### Option B: Use PayPal Instead (Free, Supports Recurring)
- PayPal supports standing orders in Israel
- Free to set up
- ~3.4% + fixed fee per transaction
- Alternative to Stripe for credit cards

#### Option C: Use Israeli Payment Gateway (CreditGuard/Tranzila)
- Full Israeli payment support
- Usually requires business registration
- Monthly fees may apply
- Supports credit cards + direct debit

---

## Step 1: Set Up Stripe Account (for Credit Cards)

1. Go to [stripe.com](https://stripe.com) and create a free account
2. Complete account verification (required for Israeli accounts)
3. Go to **Developers → API Keys**
4. Copy your **Secret Key** (starts with `sk_live_` or `sk_test_`)

---

## Step 2: Set Up Supabase (Free Database)

1. Go to [supabase.com](https://supabase.com) and create a free account
2. Create a new project:
   - Name: `olam-hayeled-billing`
   - Database Password: Create a strong password
   - Region: `EU (Frankfurt)` or `US (Oregon)` - closest to Israel
3. Wait for the project to be created (1-2 minutes)
4. Go to **Settings → API**
5. Copy:
   - **Project URL** (e.g., `https://xxxxx.supabase.co`)
   - **anon public key** (starts with `eyJ...`)

---

## Step 3: Configure Netlify Environment Variables

1. Go to [app.netlify.com](https://app.netlify.com)
2. Select your site (olam-hayeled or similar)
3. Go to **Site settings → Environment Variables**
4. Add these variables:

| Variable | Value |
|----------|-------|
| `STRIPE_SECRET_KEY` | Your Stripe secret key (sk_live_...) |
| `SUPABASE_URL` | Your Supabase project URL |
| `SUPABASE_ANON_KEY` | Your Supabase anon key |

---

## Step 4: Deploy

The code is already in your project! Just push to GitHub:

```bash
cd /Users/shirlevyzinger/shira
git add .
git commit -m "Add Stripe billing integration"
git push origin main
```

Netlify will automatically deploy and pick up the environment variables.

---

## Step 5: Test It

### Testing Credit Cards:
1. Go to your site's billing page
2. Select "כרטיס אשראי" (Credit Card)
3. Fill in test card details:
   - Card number: `4242424242424242` (Stripe test card)
   - Expiry: Any future date
   - CVV: Any 3 digits
4. Complete the registration
5. Check your Stripe dashboard for the test payment

### Testing Standing Orders:
1. Select "הוראת קבע" (Standing Order)
2. Fill in bank details
3. Submit - you'll receive the details to set up manually

---

## Standing Order Workflow (How It Works Now)

The current implementation for standing orders:

1. **Parent fills bank details** on billing page:
   - Bank code (3 digits)
   - Branch code (3 digits)
   - Account number (4-9 digits)
   - Account holder name

2. **Details are saved** to the database (in memory or Supabase)

3. **You receive notification** (需 add email notification)

4. **You set up standing order** manually:
   - Log into your bank
   - Enter parent's bank details
   - Set up recurring payment

5. **Parent confirms** when they get bank notification

---

## Going Live (Production)

### 1. Switch to Live Stripe Keys
- In Netlify, change `STRIPE_SECRET_KEY` from test to live key

### 2. Enable Stripe Webhooks (for automatic payment confirmation)
Add this endpoint in Stripe Webhooks:
```
https://your-site.netlify.app/.netlify/functions/payment/webhook
```

Events to listen for:
- `invoice.payment_succeeded`
- `invoice.payment_failed`
- `customer.subscription.deleted`

### 3. Test with Real Cards
Use `4242424242424242` for Visa test, or real Israeli cards in live mode.

---

## Database Schema (Supabase)

Run this SQL in Supabase's SQL Editor:

```sql
-- Customers table
CREATE TABLE customers (
  id SERIAL PRIMARY KEY,
  parent_name TEXT NOT NULL,
  phone TEXT NOT NULL,
  email TEXT,
  child_name TEXT NOT NULL,
  child_age TEXT,
  allergies TEXT,
  notes TEXT,
  stripe_customer_id TEXT,
  created_at TIMESTAMP DEFAULT NOW(),
  status TEXT DEFAULT 'active'
);

-- Payment methods table
CREATE TABLE payment_methods (
  id SERIAL PRIMARY KEY,
  customer_id INTEGER REFERENCES customers(id),
  payment_type TEXT NOT NULL,
  card_number_last4 TEXT,
  card_holder_name TEXT,
  card_expiry_month TEXT,
  card_expiry_year TEXT,
  stripe_payment_method_id TEXT,
  bank_code TEXT,
  branch_code TEXT,
  account_number TEXT,
  account_holder_name TEXT,
  is_default BOOLEAN DEFAULT true,
  is_active BOOLEAN DEFAULT true,
  created_at TIMESTAMP DEFAULT NOW()
);

-- Payments table
CREATE TABLE payments (
  id SERIAL PRIMARY KEY,
  customer_id INTEGER REFERENCES customers(id),
  payment_method_id INTEGER REFERENCES payment_methods(id),
  payment_intent_id TEXT,
  amount INTEGER NOT NULL,
  currency TEXT DEFAULT 'ILS',
  status TEXT DEFAULT 'pending',
  description TEXT,
  due_date DATE,
  paid_at TIMESTAMP,
  created_at TIMESTAMP DEFAULT NOW()
);

-- Recurring payments table
CREATE TABLE recurring_payments (
  id SERIAL PRIMARY KEY,
  customer_id INTEGER REFERENCES customers(id),
  payment_method_id INTEGER REFERENCES payment_methods(id),
  amount INTEGER NOT NULL,
  currency TEXT DEFAULT 'ILS',
  frequency TEXT DEFAULT 'monthly',
  start_date DATE NOT NULL,
  end_date DATE,
  next_payment_date DATE NOT NULL,
  stripe_subscription_id TEXT,
  status TEXT DEFAULT 'active',
  created_at TIMESTAMP DEFAULT NOW()
);

-- Enable RLS (Row Level Security)
ALTER TABLE customers ENABLE ROW LEVEL SECURITY;
ALTER TABLE payment_methods ENABLE ROW LEVEL SECURITY;
ALTER TABLE payments ENABLE ROW LEVEL SECURITY;
ALTER TABLE recurring_payments ENABLE ROW LEVEL SECURITY;

-- Create policies (allow all for now - restrict in production)
CREATE POLICY "Allow all on customers" ON customers FOR ALL USING (true);
CREATE POLICY "Allow all on payment_methods" ON payment_methods FOR ALL USING (true);
CREATE POLICY "Allow all on payments" ON payments FOR ALL USING (true);
CREATE POLICY "Allow all on recurring_payments" ON recurring_payments FOR ALL USING (true);
```

---

## Transaction Fees

### Credit Card (Stripe):
- **Fee**: 3.4% + ₪1.20 per successful transaction
- **Example**: ₪120 per ₪3,500 payment

### Standing Order (Manual):
- **Fee**: Bank charges (usually ₪5-15 per transaction)
- You set up in your bank, they handle fees

---

## Support

- Stripe Documentation: [stripe.com/docs](https://stripe.com/docs)
- Supabase Documentation: [supabase.com/docs](https://supabase.com/docs)
- Netlify Functions: [docs.netlify.com/functions](https://docs.netlify.com/functions)

---

## Troubleshooting

### "Function not found" error
- Check netlify.toml has correct functions path
- Ensure file is in `netlify/functions/payment.js`

### "Environment variable not set" error
- Verify variables in Netlify dashboard
- Redeploy after adding variables

### Payments not working
- Check Stripe dashboard for errors
- Verify you're using test keys in test mode

### Standing order not processing
- Standing orders require manual setup in your bank
- Currently saves details but doesn't auto-charge

### Data not persisting
- Currently using in-memory storage (resets on function cold start)
- Set up Supabase using the SQL above for permanent storage
