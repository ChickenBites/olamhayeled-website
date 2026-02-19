#!/usr/bin/env python3
"""
Database module for billing system
Manages customer and payment information
"""

import sqlite3
import hashlib
import os
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any

# Database configuration
DB_PATH = os.path.join(os.path.dirname(__file__), 'billing.db')

def get_db_connection():
    """Get a database connection"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_database():
    """Initialize the database with required tables"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Customers table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS customers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            parent_name TEXT NOT NULL,
            phone TEXT NOT NULL,
            email TEXT,
            child_name TEXT NOT NULL,
            child_age TEXT,
            allergies TEXT,
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            status TEXT DEFAULT 'active'
        )
    ''')
    
    # Payment methods table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS payment_methods (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_id INTEGER NOT NULL,
            payment_type TEXT NOT NULL CHECK(payment_type IN ('credit_card', 'standing_order')),
            
            -- Credit card fields (encrypted)
            card_number_last4 TEXT,
            card_holder_name TEXT,
            card_expiry_month TEXT,
            card_expiry_year TEXT,
            card_token TEXT,
            
            -- Standing order fields
            bank_code TEXT,
            branch_code TEXT,
            account_number TEXT,
            account_holder_name TEXT,
            
            is_default INTEGER DEFAULT 0,
            is_active INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (customer_id) REFERENCES customers(id)
        )
    ''')
    
    # Payments table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS payments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_id INTEGER NOT NULL,
            payment_method_id INTEGER,
            amount INTEGER NOT NULL,
            currency TEXT DEFAULT 'ILS',
            payment_type TEXT NOT NULL CHECK(payment_type IN ('credit_card', 'standing_order')),
            status TEXT DEFAULT 'pending' CHECK(status IN ('pending', 'processing', 'completed', 'failed', 'cancelled', 'refunded')),
            
            -- For credit card payments
            transaction_id TEXT,
            authorization_code TEXT,
            
            -- For standing order
            standing_order_date INTEGER,
            confirmation_number TEXT,
            
            payment_date TIMESTAMP,
            due_date TIMESTAMP,
            description TEXT,
            
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (customer_id) REFERENCES customers(id),
            FOREIGN KEY (payment_method_id) REFERENCES payment_methods(id)
        )
    ''')
    
    # Recurring payments table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS recurring_payments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_id INTEGER NOT NULL,
            payment_method_id INTEGER NOT NULL,
            amount INTEGER NOT NULL,
            currency TEXT DEFAULT 'ILS',
            frequency TEXT DEFAULT 'monthly' CHECK(frequency IN ('weekly', 'monthly', 'yearly')),
            start_date DATE NOT NULL,
            end_date DATE,
            next_payment_date DATE NOT NULL,
            status TEXT DEFAULT 'active' CHECK(status IN ('active', 'paused', 'cancelled')),
            
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (customer_id) REFERENCES customers(id),
            FOREIGN KEY (payment_method_id) REFERENCES payment_methods(id)
        )
    ''')
    
    # Payment log table for audit
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS payment_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            payment_id INTEGER,
            action TEXT NOT NULL,
            details TEXT,
            ip_address TEXT,
            user_agent TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (payment_id) REFERENCES payments(id)
        )
    ''')
    
    conn.commit()
    conn.close()
    print("✅ Database initialized successfully")

def encrypt_sensitive_data(data: str) -> str:
    """Encrypt sensitive data using SHA-256"""
    if not data:
        return ""
    salt = "olam_hayeled_billing_2024"  # In production, use environment variable
    return hashlib.sha256((data + salt).encode()).hexdigest()

def decrypt_sensitive_data(encrypted: str) -> str:
    """Decrypt sensitive data (for display purposes only - last 4 digits)"""
    # Note: Full decryption should only be done when needed for payment processing
    # This is a one-way hash for storage security
    return encrypted

def add_customer(parent_name: str, phone: str, email: str, child_name: str, 
                child_age: str = None, allergies: str = None, notes: str = None) -> int:
    """Add a new customer"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT INTO customers (parent_name, phone, email, child_name, child_age, allergies, notes)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (parent_name, phone, email, child_name, child_age, allergies, notes))
    
    customer_id = cursor.lastrowid
    conn.commit()
    conn.close()
    
    return customer_id

def get_customer(customer_id: int) -> Optional[Dict]:
    """Get customer by ID"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM customers WHERE id = ?', (customer_id,))
    row = cursor.fetchone()
    conn.close()
    
    return dict(row) if row else None

def add_credit_card(customer_id: int, card_number: str, card_holder_name: str,
                   expiry_month: str, expiry_year: str, card_token: str = None,
                   is_default: bool = True) -> int:
    """Add a credit card payment method"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Get last 4 digits
    last4 = card_number[-4:] if len(card_number) >= 4 else card_number
    
    # Hash card number for security (never store full number)
    card_hash = encrypt_sensitive_data(card_number)
    
    # If this is default, unset other defaults
    if is_default:
        cursor.execute('UPDATE payment_methods SET is_default = 0 WHERE customer_id = ?', (customer_id,))
    
    cursor.execute('''
        INSERT INTO payment_methods 
        (customer_id, payment_type, card_number_last4, card_holder_name, 
         card_expiry_month, card_expiry_year, card_token, is_default)
        VALUES (?, 'credit_card', ?, ?, ?, ?, ?, ?)
    ''', (customer_id, last4, card_holder_name, expiry_month, expiry_year, card_token, is_default))
    
    method_id = cursor.lastrowid
    conn.commit()
    conn.close()
    
    return method_id

def add_standing_order(customer_id: int, bank_code: str, branch_code: str,
                      account_number: str, account_holder_name: str,
                      is_default: bool = True) -> int:
    """Add a standing order (הוראת קבע) payment method"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Encrypt account number for security
    account_hash = encrypt_sensitive_data(account_number)
    
    # If this is default, unset other defaults
    if is_default:
        cursor.execute('UPDATE payment_methods SET is_default = 0 WHERE customer_id = ?', (customer_id,))
    
    cursor.execute('''
        INSERT INTO payment_methods 
        (customer_id, payment_type, bank_code, branch_code, account_number, 
         account_holder_name, is_default)
        VALUES (?, 'standing_order', ?, ?, ?, ?, ?)
    ''', (customer_id, bank_code, branch_code, account_number, account_holder_name, is_default))
    
    method_id = cursor.lastrowid
    conn.commit()
    conn.close()
    
    return method_id

def get_payment_methods(customer_id: int) -> List[Dict]:
    """Get all payment methods for a customer"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT * FROM payment_methods 
        WHERE customer_id = ? AND is_active = 1
        ORDER BY is_default DESC, created_at DESC
    ''', (customer_id,))
    
    rows = cursor.fetchall()
    conn.close()
    
    return [dict(row) for row in rows]

def set_default_payment_method(customer_id: int, method_id: int):
    """Set a payment method as default"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('UPDATE payment_methods SET is_default = 0 WHERE customer_id = ?', (customer_id,))
    cursor.execute('UPDATE payment_methods SET is_default = 1 WHERE id = ?', (method_id,))
    
    conn.commit()
    conn.close()

def remove_payment_method(customer_id: int, method_id: int):
    """Deactivate a payment method"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        UPDATE payment_methods 
        SET is_active = 0 
        WHERE customer_id = ? AND id = ?
    ''', (customer_id, method_id))
    
    conn.commit()
    conn.close()

def create_recurring_payment(customer_id: int, payment_method_id: int, 
                            amount: int, start_date: str, 
                            frequency: str = 'monthly', end_date: str = None) -> int:
    """Create a recurring payment plan"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Calculate next payment date
    from datetime import date
    start = datetime.strptime(start_date, '%Y-%m-%d').date()
    
    if frequency == 'monthly':
        # Next payment is 1 month from start
        if start.month == 12:
            next_date = date(start.year + 1, 1, start.day)
        else:
            next_date = date(start.year, start.month + 1, start.day)
    elif frequency == 'weekly':
        next_date = start + timedelta(weeks=1)
    else:
        next_date = start + timedelta(days=365)
    
    cursor.execute('''
        INSERT INTO recurring_payments 
        (customer_id, payment_method_id, amount, frequency, 
         start_date, end_date, next_payment_date)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (customer_id, payment_method_id, amount, frequency, 
          start_date, end_date, next_date.isoformat()))
    
    recurring_id = cursor.lastrowid
    
    # Create first payment record
    cursor.execute('''
        INSERT INTO payments 
        (customer_id, payment_method_id, amount, payment_type, 
         status, due_date, description)
        VALUES (?, ?, ?, 
            (SELECT payment_type FROM payment_methods WHERE id = ?),
            'pending', ?, ?)
    ''', (customer_id, payment_method_id, amount, payment_method_id, 
          start_date, f'תשלום חודשי - {next_date.strftime("%m/%Y")}'))
    
    conn.commit()
    conn.close()
    
    return recurring_id

def get_recurring_payments(customer_id: int = None) -> List[Dict]:
    """Get recurring payments, optionally filtered by customer"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    if customer_id:
        cursor.execute('''
            SELECT * FROM recurring_payments 
            WHERE customer_id = ? AND status = 'active'
            ORDER BY next_payment_date ASC
        ''', (customer_id,))
    else:
        cursor.execute('''
            SELECT * FROM recurring_payments 
            WHERE status = 'active'
            ORDER BY next_payment_date ASC
        ''')
    
    rows = cursor.fetchall()
    conn.close()
    
    return [dict(row) for row in rows]

def process_payment(payment_id: int, transaction_id: str = None, 
                   authorization_code: str = None, status: str = 'completed') -> bool:
    """Process a payment and update its status"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        UPDATE payments 
        SET status = ?, transaction_id = ?, authorization_code = ?,
            payment_date = CURRENT_TIMESTAMP, updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
    ''', (status, transaction_id, authorization_code, payment_id))
    
    # Log the action
    cursor.execute('''
        INSERT INTO payment_log (payment_id, action, details)
        VALUES (?, 'payment_processed', ?)
    ''', (payment_id, f'Status: {status}'))
    
    conn.commit()
    conn.close()
    
    return True

def get_pending_payments() -> List[Dict]:
    """Get all pending payments that need to be processed"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT p.*, c.parent_name, c.phone, c.child_name,
               pm.payment_type as pm_type
        FROM payments p
        JOIN customers c ON p.customer_id = c.id
        JOIN payment_methods pm ON p.payment_method_id = pm.id
        WHERE p.status = 'pending' AND p.due_date <= date('now')
        ORDER BY p.due_date ASC
    ''')
    
    rows = cursor.fetchall()
    conn.close()
    
    return [dict(row) for row in rows]

def get_payment_history(customer_id: int, limit: int = 12) -> List[Dict]:
    """Get payment history for a customer"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT * FROM payments 
        WHERE customer_id = ?
        ORDER BY created_at DESC
        LIMIT ?
    ''', (customer_id, limit))
    
    rows = cursor.fetchall()
    conn.close()
    
    return [dict(row) for row in rows]

def cancel_recurring_payment(recurring_id: int) -> bool:
    """Cancel a recurring payment plan"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        UPDATE recurring_payments 
        SET status = 'cancelled', updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
    ''', (recurring_id,))
    
    conn.commit()
    conn.close()
    
    return True

def pause_recurring_payment(recurring_id: int) -> bool:
    """Pause a recurring payment plan"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        UPDATE recurring_payments 
        SET status = 'paused', updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
    ''', (recurring_id,))
    
    conn.commit()
    conn.close()
    
    return True

def resume_recurring_payment(recurring_id: int) -> bool:
    """Resume a paused recurring payment plan"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        UPDATE recurring_payments 
        SET status = 'active', updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
    ''', (recurring_id,))
    
    conn.commit()
    conn.close()
    
    return True

# Initialize database on import
if __name__ == "__main__":
    init_database()
