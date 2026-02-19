#!/usr/bin/env python3
"""
Payment Gateway Module
Handles credit card and standing order (הוראת קבע) payment processing

This is a mock implementation that simulates payment processing.
In production, replace with actual payment provider integration:
- For credit cards: PayPal, Stripe, CreditGuard, etc.
- For standing orders: Banks API integration
"""

import random
import string
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

class PaymentStatus(Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    REFUNDED = "refunded"

class PaymentType(Enum):
    CREDIT_CARD = "credit_card"
    STANDING_ORDER = "standing_order"

@dataclass
class PaymentResult:
    success: bool
    transaction_id: Optional[str] = None
    authorization_code: Optional[str] = None
    status: str = "failed"
    message: str = ""
    timestamp: str = ""

def __init__(self):
    """Initialize payment gateway configuration"""
    self.config = {
        "merchant_id": "OLAM_HAYELED_2024",
        "currency": "ILS",
        "country": "IL",
        "environment": "sandbox"  # Change to "production" for live
    }

def generate_transaction_id() -> str:
    """Generate a unique transaction ID"""
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    random_suffix = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
    return f"TXN-{timestamp}-{random_suffix}"

def generate_authorization_code() -> str:
    """Generate an authorization code"""
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=12))

def validate_credit_card(card_number: str, expiry_month: str, expiry_year: str, cvv: str) -> Tuple[bool, str]:
    """
    Validate credit card details
    
    Returns: (is_valid, error_message)
    """
    # Remove spaces and dashes
    card_number = card_number.replace(" ", "").replace("-", "")
    
    # Check if card number is all digits
    if not card_number.isdigit():
        return False, "מספר כרטיס חייב להכיל ספרות בלבד"
    
    # Check card number length (13-19 digits)
    if len(card_number) < 13 or len(card_number) > 19:
        return False, "מספר כרטיס לא תקין"
    
    # Luhn algorithm validation
    if not luhn_check(card_number):
        return False, "מספר כרטיס לא תקין - בדיקת Luhn נכשלה"
    
    # Validate expiry date
    try:
        exp_month = int(expiry_month)
        exp_year = int(expiry_year)
        
        if exp_month < 1 or exp_month > 12:
            return False, "חודש תפוגה לא תקין"
        
        # Convert 2-digit year to 4-digit
        if exp_year < 100:
            exp_year += 2000
        
        # Check if card is expired
        now = datetime.now()
        exp_date = datetime(exp_year, exp_month, 1)
        # Card expires at end of expiry month
        if exp_date < now.replace(day=1):
            return False, "כרטיס אשראי פג תוקף"
        
    except ValueError:
        return False, "תאריך תפוגה לא תקין"
    
    # Validate CVV
    if not cvv.isdigit() or len(cvv) not in [3, 4]:
        return False, "קוד CVV לא תקין"
    
    return True, ""

def luhn_check(card_number: str) -> bool:
    """Validate card number using Luhn algorithm"""
    digits = [int(d) for d in card_number]
    # Reverse the digits
    digits = digits[::-1]
    
    # Double every second digit
    for i in range(1, len(digits), 2):
        digits[i] *= 2
        if digits[i] > 9:
            digits[i] -= 9
    
    # Sum all digits
    total = sum(digits)
    
    return total % 10 == 0

def validate_standing_order(bank_code: str, branch_code: str, 
                           account_number: str, account_holder_name: str) -> Tuple[bool, str]:
    """
    Validate standing order (הוראת קבע) details
    
    Israeli bank account validation:
    - Bank code: 3 digits
    - Branch code: 3 digits
    - Account number: up to 9 digits
    """
    
    # Validate bank code (3 digits)
    if not bank_code.isdigit() or len(bank_code) != 3:
        return False, "קוד בנק לא תקין (3 ספרות)"
    
    # Validate branch code (3 digits)
    if not branch_code.isdigit() or len(branch_code) != 3:
        return False, "קוד סניף לא תקין (3 ספרות)"
    
    # Validate account number (up to 9 digits)
    if not account_number.isdigit() or len(account_number) < 4 or len(account_number) > 9:
        return False, "מספר חשבון לא תקין (4-9 ספרות)"
    
    # Validate account holder name
    if not account_holder_name or len(account_holder_name.strip()) < 2:
        return False, "שם בעל החשבון לא תקין"
    
    # Israeli bank codes (common ones)
    valid_banks = ['001', '002', '004', '007', '009', '010', '011', '012', '013', '014', '017', '020', '022', '023', '025', '026', '027', '029', '030', '031', '032', '033', '034', '035', '036', '037', '038', '039', '040', '041', '042', '043', '044', '045', '046', '047', '048', '049', '050', '051', '052', '053', '054', '055', '056', '057', '058', '059', '060', '061', '062', '063', '064', '065', '066', '067', '068', '069', '070', '071', '072', '073', '074', '075', '076', '077', '078', '079', '080', '081', '082', '083', '084', '085', '086', '087', '088', '089', '090', '091', '092', '093', '094', '095', '096', '097', '098', '099']
    
    if bank_code not in valid_banks:
        return False, f"קוד בנק {bank_code} לא מוכר"
    
    return True, ""

def process_credit_card(card_number: str, card_holder_name: str,
                       expiry_month: str, expiry_year: str, cvv: str,
                       amount: int, currency: str = "ILS",
                       description: str = "") -> PaymentResult:
    """
    Process a credit card payment
    
    In production, this would integrate with a payment provider like:
    - PayPal
    - Stripe
    - CreditGuard
    - Tranzila
    
    Args:
        card_number: Full credit card number
        card_holder_name: Name on the card
        expiry_month: Expiry month (MM)
        expiry_year: Expiry year (YYYY or YY)
        cvv: CVV/CVC code
        amount: Amount in agorot (1 ILS = 100 agorot)
        currency: Currency code (default: ILS)
        description: Payment description
    
    Returns:
        PaymentResult with transaction details
    """
    # Validate card first
    is_valid, error_msg = validate_credit_card(card_number, expiry_month, expiry_year, cvv)
    if not is_valid:
        return PaymentResult(
            success=False,
            status="failed",
            message=error_msg,
            timestamp=datetime.now().isoformat()
        )
    
    # In sandbox mode, simulate payment processing
    if True:  # Change to check config in production
        # Simulate processing delay
        import time
        time.sleep(0.5)  # Simulate API call
        
        # Simulate success/failure (90% success rate in sandbox)
        if random.random() < 0.9:
            return PaymentResult(
                success=True,
                transaction_id=generate_transaction_id(),
                authorization_code=generate_authorization_code(),
                status="completed",
                message="התשלום בוצע בהצלחה",
                timestamp=datetime.now().isoformat()
            )
        else:
            return PaymentResult(
                success=False,
                status="failed",
                message="התשלום נכשל - אנא נסה שוב",
                timestamp=datetime.now().isoformat()
            )
    
    # Production code would look like:
    """
    # Example with CreditGuard (Israeli payment gateway)
    cg = CreditGuardGateway(merchant_id, username, password)
    
    result = cg.charge(
        card_number=card_number,
        card_holder_name=card_holder_name,
        expiry_month=expiry_month,
        expiry_year=expiry_year,
        cvv=cvv,
        amount=amount,
        currency=currency,
        description=description
    )
    
    return PaymentResult(
        success=result['success'],
        transaction_id=result.get('transaction_id'),
        authorization_code=result.get('auth_code'),
        status=result['status'],
        message=result.get('message', ''),
        timestamp=result['timestamp']
    )
    """

def process_standing_order(bank_code: str, branch_code: str,
                          account_number: str, account_holder_name: str,
                          amount: int, currency: str = "ILS",
                          payment_date: int = None,
                          description: str = "") -> PaymentResult:
    """
    Process a standing order (הוראת קבע) payment
    
    This creates a standing order instruction that will be collected
    automatically on a recurring basis.
    
    In production, this would integrate with:
    - Bank API (e.g., Mizrahi, Leumi, Hapoalim)
    - Payment service provider
    
    Args:
        bank_code: Bank code (3 digits)
        branch_code: Branch code (3 digits)
        account_number: Account number (4-9 digits)
        account_holder_name: Name on the account
        amount: Amount in agorot
        currency: Currency code
        payment_date: Day of month for standing order (1-28)
        description: Payment description
    
    Returns:
        PaymentResult with confirmation details
    """
    # Validate standing order details
    is_valid, error_msg = validate_standing_order(
        bank_code, branch_code, account_number, account_holder_name
    )
    if not is_valid:
        return PaymentResult(
            success=False,
            status="failed",
            message=error_msg,
            timestamp=datetime.now().isoformat()
        )
    
    # Validate payment date
    if payment_date is None:
        payment_date = datetime.now().day
    elif payment_date < 1 or payment_date > 28:
        return PaymentResult(
            success=False,
            status="failed",
            message="יום גבייה חייב להיות בין 1 ל-28",
            timestamp=datetime.now().isoformat()
        )
    
    # In production, this would submit the standing order to the bank
    # For now, simulate success
    confirmation_number = f"SO-{datetime.now().strftime('%Y%m%d')}-{''.join(random.choices(string.digits, k=6))}"
    
    return PaymentResult(
        success=True,
        transaction_id=confirmation_number,
        authorization_code=None,  # Standing orders don't use auth codes
        status="completed",
        message=f"הוראת קבע נוצרה בהצלחה. גבייה תתבצע ב-{payment_date} לכל חודש",
        timestamp=datetime.now().isoformat()
    )

def refund_payment(transaction_id: str, amount: int = None, 
                  reason: str = "") -> PaymentResult:
    """
    Refund a previous payment
    
    Args:
        transaction_id: Original transaction ID
        amount: Amount to refund (if None, refund full amount)
        reason: Refund reason
    
    Returns:
        PaymentResult with refund details
    """
    # In production, this would call the payment provider's refund API
    refund_id = f"REF-{datetime.now().strftime('%Y%m%d%H%M%S')}-{''.join(random.choices(string.digits, k=6))}"
    
    return PaymentResult(
        success=True,
        transaction_id=refund_id,
        authorization_code=transaction_id,  # Link to original transaction
        status="refunded",
        message="הזיכוי בוצע בהצלחה",
        timestamp=datetime.now().isoformat()
    )

def verify_payment(transaction_id: str) -> PaymentResult:
    """
    Verify the status of a previous payment
    
    Args:
        transaction_id: Transaction ID to verify
    
    Returns:
        PaymentResult with current status
    """
    # In production, this would query the payment provider
    # For now, return a mock response
    return PaymentResult(
        success=True,
        transaction_id=transaction_id,
        status="completed",
        message="התשלום אומת בהצלחה",
        timestamp=datetime.now().isoformat()
    )

# Card type detection
def detect_card_type(card_number: str) -> str:
    """Detect the type of credit card"""
    card_number = card_number.replace(" ", "").replace("-", "")
    
    if not card_number.isdigit():
        return "unknown"
    
    # Visa
    if card_number[0] == '4':
        return "Visa"
    
    # Mastercard
    if len(card_number) >= 2:
        prefix = int(card_number[:2])
        if prefix >= 51 and prefix <= 55:
            return "Mastercard"
        # Some Mastercard cards start with 2221-2720
        if len(card_number) >= 4:
            prefix4 = int(card_number[:4])
            if prefix4 >= 2221 and prefix4 <= 2720:
                return "Mastercard"
    
    # American Express
    if len(card_number) >= 2:
        prefix = card_number[:2]
        if prefix in ['34', '37']:
            return "American Express"
    
    # Diners Club
    if len(card_number) >= 2:
        prefix = card_number[:2]
        if prefix in ['36', '38']:
            return "Diners Club"
    
    # Discover
    if len(card_number) >= 4:
        prefix4 = card_number[:4]
        if prefix4 == '6011' or prefix4 == '6221':
            return "Discover"
    
    # Israeli cards
    if len(card_number) >= 2:
        prefix = card_number[:2]
        if prefix in ['45', '47', '52', '53']:
            return "Isracard"
    
    return "unknown"

# Format card number for display
def format_card_number(card_number: str) -> str:
    """Format card number with spaces for display"""
    card_number = card_number.replace(" ", "").replace("-", "")
    return ' '.join([card_number[i:i+4] for i in range(0, len(card_number), 4)])

def mask_card_number(card_number: str) -> str:
    """Mask card number showing only last 4 digits"""
    card_number = card_number.replace(" ", "").replace("-", "")
    if len(card_number) < 4:
        return "****"
    return f"**** **** **** {card_number[-4:]}"


if __name__ == "__main__":
    # Test the payment gateway
    print("Testing Credit Card Validation:")
    print(validate_credit_card("4532015112830366", "12", "2025", "123"))
    
    print("\nTesting Standing Order Validation:")
    print(validate_standing_order("001", "123", "123456", "John Doe"))
    
    print("\nTesting Card Type Detection:")
    print(detect_card_type("4532015112830366"))  # Visa
    print(detect_card_type("5425233430109903"))  # Mastercard
    print(detect_card_type("4539578763621486"))  # Isracard
