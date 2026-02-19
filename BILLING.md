# מערכת תשלומים - עולם הילד
# Billing System - Olam Hayeled

## Overview
מערכת תשלומים אוטומטית לגבייה חודשית של 3,500 ₪ מהורי ילדי המשפחתון.

Automatic billing system for monthly collection of 3,500 ILS from parents.

## Payment Options / אפשרויות תשלום
1. **Credit Card** (כרטיס אשראי) - Visa, Mastercard, Isracard
2. **Standing Order** (הוראת קבע) - Direct debit from bank account

---

## Files Created / קבצים שנוצרו

### 1. database.py
מודול ניהול מסד הנתונים / Database management module

**Tables:**
- `customers` - לקוחות
- `payment_methods` - אמצעי תשלום
- `payments` - תשלומים
- `recurring_payments` - תשלומים חוזרים
- `payment_log` - יומן פעולות

### 2. payment_gateway.py
מודול עיבוד תשלומים / Payment processing module

**Functions:**
- `validate_credit_card()` - בדיקת תקינות כרטיס אשראי
- `validate_standing_order()` - בדיקת תקינות הוראת קבע
- `process_credit_card()` - עיבוד תשלום בכרטיס אשראי
- `process_standing_order()` - יצירת הוראת קבע
- `detect_card_type()` - זיהוי סוג כרטיס

### 3. billing_server.py
שרת API לטיפול בתשלומים / API server

**Endpoints:**

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/register` | רישום לקוח חדש |
| POST | `/api/add-credit-card` | הוספת כרטיס אשראי |
| POST | `/api/add-standing-order` | הוספת הוראת קבע |
| POST | `/api/create-recurring` | יצירת תשלום חוזר |
| POST | `/api/cancel-recurring` | ביטול תשלום חוזר |
| POST | `/api/pause-recurring` | השהיית תשלום חוזר |
| POST | `/api/resume-recurring` | המשך תשלום חוזר |
| POST | `/api/payment-history` | היסטוריית תשלומים |
| GET | `/api/config` | קבלת הגדרות |

### 4. billing.html
דף תשלום ללקוחות / Customer payment page

---

## How to Run / איך להפעיל

```bash
cd /Users/shirlevyzinger/shira
python billing_server.py
```

The server will start at: http://localhost:8000

---

## API Usage Examples / דוגמאות שימוש ב-API

### 1. Register Customer / רישום לקוח
```json
POST /api/register
{
  "parent_name": "ישראל ישראלי",
  "phone": "050-1234567",
  "email": "israel@example.com",
  "child_name": "דוד",
  "child_age": "2",
  "allergies": "אלרגיות",
  "notes": "הערות"
}
```

### 2. Add Credit Card / הוספת כרטיס אשראי
```json
POST /api/add-credit-card
{
  "customer_id": 1,
  "card_number": "4532015112830366",
  "card_holder_name": "ישראל ישראלי",
  "expiry_month": "12",
  "expiry_year": "2025",
  "cvv": "123",
  "is_default": true
}
```

### 3. Add Standing Order / הוספת הוראת קבע
```json
POST /api/add-standing-order
{
  "customer_id": 1,
  "bank_code": "001",
  "branch_code": "123",
  "account_number": "123456",
  "account_holder_name": "ישראל ישראלי",
  "is_default": true
}
```

### 4. Create Recurring Payment / יצירת תשלום חוזר
```json
POST /api/create-recurring
{
  "customer_id": 1,
  "payment_method_id": 1,
  "amount": 3500,
  "start_date": "2024-01-01",
  "frequency": "monthly"
}
```

---

## Security / אבטחה

### PCI Compliance
1. לא נשמר מספר כרטיס מלא / Full card number not stored
2. שמירת 4 ספרות אחרונות בלבד / Only last 4 digits stored
3. הצפנת נתונים רגישים / Sensitive data encryption
4. שימוש ב-Luhn algorithm לבדיקת תקינות / Luhn algorithm validation

### Best Practices / שיטות עבודה מומלצות
- שימוש ב-SSL/HTTPS בייצור / Use SSL/HTTPS in production
- אחסון מפתחות הצפנה במשתני סביבה / Store encryption keys in environment variables
- שימוש ב-payment provider מאושר (Stripe, PayPal, CreditGuard) / Use approved payment provider

---

## Production Deployment / הפעלה בייצור

### Required Changes / שינויים נדרשים

1. **החלפת מודול תשלומים** / Replace payment module:
   ```python
   # In payment_gateway.py, replace mock with real provider:
   # - Stripe: https://stripe.com/docs
   # - PayPal: https://developer.paypal.com
   # - CreditGuard: https://www.creditguard.co.il
   ```

2. **הגדרת משתני סביבה** / Set environment variables:
   ```bash
   export STRIPE_API_KEY="sk_live_..."
   export PAYPAL_CLIENT_ID="..."
   export PAYPAL_CLIENT_SECRET="..."
   ```

3. **הפעלת HTTPS** / Enable HTTPS:
   ```bash
   # Using Let's Encrypt
   certbot certonly --webroot -w /path/to/shira -d yourdomain.com
   ```

4. **גיבוי מסד נתונים** / Database backup:
   ```bash
   # Regular backup
   sqlite3 billing.db ".backup billing_backup.db"
   ```

---

## Monthly Payment Flow / תהליך תשלום חודשי

1. **Customer registers** → Customer details saved
2. **Payment method added** → Card or standing order stored
3. **Recurring payment created** → Monthly schedule set
4. **Payment processed** → Auto-charge on scheduled date
5. **Notification sent** → Parent notified of payment

---

## Support / תמיכה

For questions or issues, contact the developer.

---

## License / רישיון
All rights reserved © 2024 עולם הילד
