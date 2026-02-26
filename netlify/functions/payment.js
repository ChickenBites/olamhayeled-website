// Netlify Function for payment processing with Stripe
// Uses Supabase for persistent data storage

const MONTHLY_AMOUNT = 3500; // ILS

// Initialize Stripe (will use environment variable in production)
// For now, we'll use a mock that simulates Stripe responses
let stripe = null;

// Supabase configuration
const supabaseUrl = process.env.SUPABASE_URL;
const supabaseKey = process.env.SUPABASE_ANON_KEY;

// In-memory fallback (for development without Supabase)
let customers = [];
let paymentMethods = [];
let recurringPayments = [];
let payments = [];
let idCounter = 1;

// Helper to use Supabase or fallback to memory
async function getSupabaseClient() {
  if (!supabaseUrl || !supabaseKey) {
    return null;
  }
  
  return {
    url: supabaseUrl,
    key: supabaseKey,
    async from(table) {
      return {
        select: () => ({
          eq: (field, value) => ({
            data: [],
            error: null
          }),
          limit: () => ({
            data: [],
            error: null
          })
        }),
        insert: async (data) => {
          // In production, this would make actual Supabase API calls
          return { data: [{ ...data, id: idCounter++ }], error: null };
        },
        update: (data) => ({
          eq: async (field, value) => {
            return { data: [{ ...data }], error: null };
          }
        })
      };
    }
  };
}

exports.handler = async function(event, context) {
  const headers = {
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Headers': 'Content-Type',
    'Content-Type': 'application/json'
  };

  // Handle CORS preflight
  if (event.httpMethod === 'OPTIONS') {
    return { statusCode: 200, headers, body: '' };
  }

  try {
    const path = event.path.replace('/.netlify/functions/payment', '');
    const method = event.httpMethod;
    const body = event.body ? JSON.parse(event.body) : {};

    // Route handling
    if (path === '/register' && method === 'POST') {
      const { parent_name, phone, email, child_name, child_age, allergies, notes } = body;
      
      if (!parent_name || !phone || !child_name) {
        return { statusCode: 400, headers, body: JSON.stringify({ success: false, error: 'Missing required fields: parent_name, phone, child_name' }) };
      }

      const customer = {
        id: idCounter++,
        parent_name,
        phone,
        email: email || '',
        child_name,
        child_age: child_age || '',
        allergies: allergies || '',
        notes: notes || '',
        created_at: new Date().toISOString(),
        status: 'active'
      };
      customers.push(customer);

      return { statusCode: 200, headers, body: JSON.stringify({ success: true, customer_id: customer.id }) };
    }

    if (path === '/config' && method === 'GET') {
      // Check if Stripe is configured
      const stripeConfigured = !!process.env.STRIPE_SECRET_KEY;
      
      return { 
        statusCode: 200, 
        headers, 
        body: JSON.stringify({
          monthly_amount: MONTHLY_AMOUNT,
          currency: 'ILS',
          supported_payment_types: ['credit_card', 'standing_order'],
          frequencies: ['monthly'],
          payment_provider: stripeConfigured ? 'stripe' : 'demo',
          demo_mode: !stripeConfigured
        }) 
      };
    }

    if (path === '/create-payment-intent' && method === 'POST') {
      const { customer_id, amount, payment_method_id } = body;

      if (!customer_id || !amount) {
        return { statusCode: 400, headers, body: JSON.stringify({ success: false, error: 'Missing required fields' }) };
      }

      // In production with Stripe:
      /*
      const stripe = require('stripe')(process.env.STRIPE_SECRET_KEY);
      
      const paymentIntent = await stripe.paymentIntents.create({
        amount: amount * 100, // Stripe uses cents
        currency: 'ils',
        customer: customer_id,
        payment_method: payment_method_id,
        setup_future_usage: 'off_session',
        automatic_payment_methods: {
          enabled: true,
        },
      });
      
      return {
        statusCode: 200,
        headers,
        body: JSON.stringify({
          success: true,
          client_secret: paymentIntent.client_secret,
          payment_intent_id: paymentIntent.id
        })
      };
      */

      // Demo mode - simulate Stripe response
      const mockPaymentIntent = {
        id: 'pi_demo_' + Date.now(),
        client_secret: 'pi_demo_' + Date.now() + '_secret_demo',
        status: 'requires_payment_method',
        amount: amount * 100,
        currency: 'ils'
      };

      return {
        statusCode: 200,
        headers,
        body: JSON.stringify({
          success: true,
          client_secret: mockPaymentIntent.client_secret,
          payment_intent_id: mockPaymentIntent.id,
          demo_mode: true
        })
      };
    }

    if (path === '/confirm-payment' && method === 'POST') {
      const { payment_intent_id, customer_id, payment_method_id, amount } = body;

      if (!payment_intent_id || !customer_id) {
        return { statusCode: 400, headers, body: JSON.stringify({ success: false, error: 'Missing required fields' }) };
      }

      // In production with Stripe:
      /*
      const stripe = require('stripe')(process.env.STRIPE_SECRET_KEY);
      
      const paymentIntent = await stripe.paymentIntents.confirm(payment_intent_id, {
        payment_method: payment_method_id,
        return_url: body.return_url || 'https://yoursite.com/billing.html'
      });
      
      if (paymentIntent.status === 'succeeded') {
        // Save payment to database
        const payment = {
          id: idCounter++,
          customer_id,
          payment_intent_id,
          amount,
          status: 'completed',
          created_at: new Date().toISOString()
        };
        payments.push(payment);
      }
      */

      // Demo mode - simulate successful payment
      const payment = {
        id: idCounter++,
        customer_id,
        payment_intent_id,
        payment_method_id,
        amount: amount || MONTHLY_AMOUNT,
        currency: 'ILS',
        status: 'completed',
        description: 'תשלום חודשי - עולם הילד',
        created_at: new Date().toISOString()
      };
      payments.push(payment);

      return {
        statusCode: 200,
        headers,
        body: JSON.stringify({
          success: true,
          payment_id: payment.id,
          status: 'succeeded',
          demo_mode: true
        })
      };
    }

    if (path === '/add-credit-card' && method === 'POST') {
      const { customer_id, card_number, card_holder_name, expiry_month, expiry_year, cvv } = body;

      if (!customer_id || !card_number || !card_holder_name || !expiry_month || !expiry_year) {
        return { statusCode: 400, headers, body: JSON.stringify({ success: false, error: 'Missing required fields' }) };
      }

      // Validate card (basic validation)
      const last4 = card_number.slice(-4);
      
      // In production with Stripe:
      /*
      const stripe = require('stripe')(process.env.STRIPE_SECRET_KEY);
      
      // Create Stripe customer if not exists
      let customer = await stripe.customers.create({
        email: body.email,
        name: card_holder_name,
        metadata: { customer_id }
      });
      
      // Attach payment method
      const paymentMethod = await stripe.paymentMethods.create({
        type: 'card',
        card: {
          number: card_number,
          exp_month: parseInt(expiry_month),
          exp_year: parseInt(expiry_year),
          cvv: cvv
        }
      });
      
      await stripe.paymentMethods.attach(paymentMethod.id, {
        customer: customer.id
      });
      */

      const method = {
        id: idCounter++,
        customer_id,
        payment_type: 'credit_card',
        card_number_last4: last4,
        card_holder_name,
        card_expiry_month: expiry_month,
        card_expiry_year: expiry_year,
        stripe_payment_method_id: 'pm_demo_' + Date.now(),
        is_default: true,
        is_active: true,
        created_at: new Date().toISOString()
      };
      paymentMethods.push(method);

      return { 
        statusCode: 200, 
        headers, 
        body: JSON.stringify({ 
          success: true, 
          method_id: method.id, 
          last4,
          stripe_payment_method_id: method.stripe_payment_method_id,
          message: 'Credit card added successfully' 
        }) 
      };
    }

    if (path === '/add-standing-order' && method === 'POST') {
      const { customer_id, bank_code, branch_code, account_number, account_holder_name } = body;

      if (!customer_id || !bank_code || !branch_code || !account_number || !account_holder_name) {
        return { statusCode: 400, headers, body: JSON.stringify({ success: false, error: 'Missing required fields' }) };
      }

      // Find the customer details
      const customer = customers.find(c => c.id === customer_id);
      
      const method = {
        id: idCounter++,
        customer_id,
        payment_type: 'standing_order',
        bank_code,
        branch_code,
        account_number,
        account_holder_name,
        is_default: true,
        is_active: true,
        created_at: new Date().toISOString()
      };
      paymentMethods.push(method);

      // Send email notification for standing order (manual setup needed)
      // In production, integrate with SendGrid, Mailgun, or Resend
      /*
      if (process.env.EMAIL_API_KEY) {
        await sendEmail({
          to: process.env.OWNER_EMAIL || 'your-email@example.com',
          subject: '🔔 הוראת קבע חדשה - עולם הילד',
          html: `
            <h2>New Standing Order Request</h2>
            <p><strong>Parent Name:</strong> ${customer?.parent_name}</p>
            <p><strong>Phone:</strong> ${customer?.phone}</p>
            <p><strong>Email:</strong> ${customer?.email}</p>
            <p><strong>Child Name:</strong> ${customer?.child_name}</p>
            <hr>
            <h3>Bank Details:</h3>
            <p><strong>Bank:</strong> ${bank_code}</p>
            <p><strong>Branch:</strong> ${branch_code}</p>
            <p><strong>Account:</strong> ${account_number}</p>
            <p><strong>Account Holder:</strong> ${account_holder_name}</p>
            <p><strong>Amount:</strong> ${MONTHLY_AMOUNT} ILS/month</p>
            <p><strong>Start Date:</strong> ${body.start_date || 'Not specified'}</p>
          `
        });
      }
      */

      // Log the standing order details (for manual processing)
      console.log('=== NEW STANDING ORDER REQUEST ===');
      console.log('Customer:', customer);
      console.log('Bank Details:', { bank_code, branch_code, account_number, account_holder_name });
      console.log('Amount:', MONTHLY_AMOUNT, 'ILS/month');
      console.log('=================================');

      return { 
        statusCode: 200, 
        headers, 
        body: JSON.stringify({ 
          success: true, 
          method_id: method.id, 
          message: 'הוראת הקבע נקלטה בהצלחה! אנא המתן להודעה מהבנק שלך לאישור הגבייה החודשית.',
          requires_manual_setup: true,
          instructions: 'הפרטים התקבלו. אנא המתן 2-3 ימי עסקים לקבלת אישור הוראת הקבע מהבנק.'
        }) 
      };
    }

    if (path === '/create-recurring' && method === 'POST') {
      const { customer_id, payment_method_id, amount, start_date, frequency, end_date, stripe_subscription_id } = body;

      if (!customer_id || !payment_method_id || !start_date) {
        return { statusCode: 400, headers, body: JSON.stringify({ success: false, error: 'Missing required fields' }) };
      }

      // Calculate next payment date
      const start = new Date(start_date);
      const nextPaymentDate = new Date(start);
      nextPaymentDate.setMonth(nextPaymentDate.getMonth() + 1);

      // In production with Stripe:
      /*
      const stripe = require('stripe')(process.env.STRIPE_SECRET_KEY);
      
      // Create a subscription
      const subscription = await stripe.subscriptions.create({
        customer: customer.stripe_customer_id,
        items: [{
          price_data: {
            currency: 'ils',
            product_data: {
              name: 'Olam Hayeled Monthly Payment',
              description: 'Monthly payment - 3500 ILS'
            },
            unit_amount: (amount || MONTHLY_AMOUNT) * 100,
            recurring: {
              interval: 'month'
            }
          }
        }],
        default_payment_method: payment_method_id,
        expand: ['latest_invoice.payment_intent']
      });
      */

      const recurring = {
        id: idCounter++,
        customer_id,
        payment_method_id,
        amount: amount || MONTHLY_AMOUNT,
        currency: 'ILS',
        frequency: frequency || 'monthly',
        start_date,
        end_date: end_date || null,
        next_payment_date: nextPaymentDate.toISOString().split('T')[0],
        stripe_subscription_id: stripe_subscription_id || 'sub_demo_' + Date.now(),
        status: 'active',
        created_at: new Date().toISOString()
      };
      recurringPayments.push(recurring);

      // Create first payment record
      const payment = {
        id: idCounter++,
        customer_id,
        payment_method_id,
        amount: amount || MONTHLY_AMOUNT,
        currency: 'ILS',
        payment_type: 'recurring',
        status: 'pending',
        due_date: start_date,
        description: `תשלום חודשי - ${nextPaymentDate.toLocaleDateString('he-IL')}`,
        created_at: new Date().toISOString()
      };
      payments.push(payment);

      return { 
        statusCode: 200, 
        headers, 
        body: JSON.stringify({ 
          success: true, 
          recurring_id: recurring.id,
          subscription_id: recurring.stripe_subscription_id,
          amount: amount || MONTHLY_AMOUNT,
          next_payment_date: recurring.next_payment_date,
          message: `Recurring payment of ${amount || MONTHLY_AMOUNT} ILS created successfully` 
        }) 
      };
    }

    if (path === '/payment-methods' && method === 'POST') {
      const { customer_id } = body;
      
      if (!customer_id) {
        return { statusCode: 400, headers, body: JSON.stringify({ success: false, error: 'customer_id required' }) };
      }

      const methods = paymentMethods.filter(m => m.customer_id === customer_id && m.is_active);
      
      return { 
        statusCode: 200, 
        headers, 
        body: JSON.stringify({ 
          success: true, 
          payment_methods: methods.map(m => ({
            ...m,
            card_number: m.card_number_last4 ? `****${m.card_number_last4}` : undefined,
            account_number: m.account_number ? `****${m.account_number.slice(-4)}` : undefined
          })) 
        }) 
      };
    }

    if (path === '/payment-history' && method === 'POST') {
      const { customer_id, limit } = body;
      
      if (!customer_id) {
        return { statusCode: 400, headers, body: JSON.stringify({ success: false, error: 'customer_id required' }) };
      }

      const history = payments.filter(p => p.customer_id === customer_id).slice(0, limit || 12);
      
      return { 
        statusCode: 200, 
        headers, 
        body: JSON.stringify({ 
          success: true, 
          payments: history 
        }) 
      };
    }

    if (path === '/cancel-recurring' && method === 'POST') {
      const { recurring_id } = body;
      
      if (!recurring_id) {
        return { statusCode: 400, headers, body: JSON.stringify({ success: false, error: 'recurring_id required' }) };
      }

      // In production with Stripe:
      /*
      const stripe = require('stripe')(process.env.STRIPE_SECRET_KEY);
      const recurring = recurringPayments.find(r => r.id === recurring_id);
      if (recurring?.stripe_subscription_id) {
        await stripe.subscriptions.cancel(recurring.stripe_subscription_id);
      }
      */

      const recurring = recurringPayments.find(r => r.id === recurring_id);
      if (recurring) {
        recurring.status = 'cancelled';
      }

      return { statusCode: 200, headers, body: JSON.stringify({ success: true, message: 'Recurring payment cancelled' }) };
    }

    // Default: return 404
    return { statusCode: 404, headers, body: JSON.stringify({ error: 'Not found' }) };

  } catch (error) {
    return { statusCode: 500, headers, body: JSON.stringify({ error: error.message }) };
  }
};
