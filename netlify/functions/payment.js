// Netlify Function for payment processing
// This handles recurring payments via Stripe or similar

const MONTHLY_AMOUNT = 3500; // ILS

// In-memory storage (use database in production)
// For Netlify, you'd typically use a database service like Supabase, Airtable, or Firebase

let customers = [];
let paymentMethods = [];
let recurringPayments = [];
let payments = [];
let idCounter = 1;

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
        return { statusCode: 400, headers, body: JSON.stringify({ success: false, error: 'Missing required fields' }) };
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
      return { 
        statusCode: 200, 
        headers, 
        body: JSON.stringify({
          monthly_amount: MONTHLY_AMOUNT,
          currency: 'ILS',
          supported_payment_types: ['credit_card', 'standing_order'],
          frequencies: ['monthly']
        }) 
      };
    }

    if (path === '/add-credit-card' && method === 'POST') {
      const { customer_id, card_number, card_holder_name, expiry_month, expiry_year, cvv } = body;

      if (!customer_id || !card_number || !card_holder_name || !expiry_month || !expiry_year) {
        return { statusCode: 400, headers, body: JSON.stringify({ success: false, error: 'Missing required fields' }) };
      }

      // Validate card (basic validation - in production use Stripe's validation)
      const last4 = card_number.slice(-4);
      
      const method = {
        id: idCounter++,
        customer_id,
        payment_type: 'credit_card',
        card_number_last4: last4,
        card_holder_name,
        card_expiry_month: expiry_month,
        card_expiry_year: expiry_year,
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
          message: 'Credit card added successfully' 
        }) 
      };
    }

    if (path === '/add-standing-order' && method === 'POST') {
      const { customer_id, bank_code, branch_code, account_number, account_holder_name } = body;

      if (!customer_id || !bank_code || !branch_code || !account_number || !account_holder_name) {
        return { statusCode: 400, headers, body: JSON.stringify({ success: false, error: 'Missing required fields' }) };
      }

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

      return { 
        statusCode: 200, 
        headers, 
        body: JSON.stringify({ 
          success: true, 
          method_id: method.id, 
          message: 'Standing order added successfully' 
        }) 
      };
    }

    if (path === '/create-recurring' && method === 'POST') {
      const { customer_id, payment_method_id, amount, start_date, frequency, end_date } = body;

      if (!customer_id || !payment_method_id || !start_date) {
        return { statusCode: 400, headers, body: JSON.stringify({ success: false, error: 'Missing required fields' }) };
      }

      // Calculate next payment date
      const start = new Date(start_date);
      const nextPaymentDate = new Date(start);
      nextPaymentDate.setMonth(nextPaymentDate.getMonth() + 1);

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
          amount: amount || MONTHLY_AMOUNT,
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
