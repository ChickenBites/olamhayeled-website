#!/usr/bin/env python3
"""
Billing Server - REST API for payment processing
Handles recurring payments of 3500 NIS monthly via credit card or standing order
"""

import http.server
import socketserver
import json
import os
import sys
import urllib.parse
from pathlib import Path
from datetime import datetime, date
import webbrowser

# Import billing modules
import database
import payment_gateway

# Server configuration
PORT = 8000
HOST = "localhost"

# Amount in ILS (3500 NIS monthly)
MONTHLY_AMOUNT = 3500
CURRENCY = "ILS"

# MIME types for serving files
MIME_TYPES = {
    '.html': 'text/html',
    '.js': 'application/javascript',
    '.css': 'text/css',
    '.json': 'application/json',
    '.png': 'image/png',
    '.jpg': 'image/jpeg',
    '.jpeg': 'image/jpeg',
    '.gif': 'image/gif',
    '.svg': 'image/svg+xml',
    '.ico': 'image/x-icon'
}

class BillingRequestHandler(http.server.SimpleHTTPRequestHandler):
    """Custom HTTP request handler for billing API"""
    
    def __init__(self, *args, **kwargs):
        # Set the directory to serve
        self.directory = os.path.dirname(os.path.abspath(__file__))
        super().__init__(*args, directory=self.directory, **kwargs)
    
    def end_headers(self):
        """Add CORS and other headers"""
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        super().end_headers()
    
    def do_OPTIONS(self):
        """Handle CORS preflight requests"""
        self.send_response(200)
        self.end_headers()
    
    def do_POST(self):
        """Handle POST requests"""
        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length).decode('utf-8')
        
        try:
            data = json.loads(body) if body else {}
        except json.JSONDecodeError:
            self.send_error_response(400, "Invalid JSON")
            return
        
        # Route to appropriate handler
        if self.path == '/api/register':
            self.handle_register(data)
        elif self.path == '/api/payment-methods':
            self.handle_payment_methods(data)
        elif self.path == '/api/add-credit-card':
            self.handle_add_credit_card(data)
        elif self.path == '/api/add-standing-order':
            self.handle_add_standing_order(data)
        elif self.path == '/api/create-recurring':
            self.handle_create_recurring(data)
        elif self.path == '/api/process-payment':
            self.handle_process_payment(data)
        elif self.path == '/api/cancel-recurring':
            self.handle_cancel_recurring(data)
        elif self.path == '/api/pause-recurring':
            self.handle_pause_recurring(data)
        elif self.path == '/api/resume-recurring':
            self.handle_resume_recurring(data)
        elif self.path == '/api/payment-history':
            self.handle_payment_history(data)
        elif self.path == '/api/validate-card':
            self.handle_validate_card(data)
        elif self.path == '/api/validate-standing-order':
            self.handle_validate_standing_order(data)
        else:
            self.send_error_response(404, "Endpoint not found")
    
    def do_GET(self):
        """Handle GET requests"""
        if self.path == '/api/config':
            # Return billing configuration
            self.send_json_response({
                'monthly_amount': MONTHLY_AMOUNT,
                'currency': CURRENCY,
                'supported_payment_types': ['credit_card', 'standing_order'],
                'frequencies': ['monthly']
            })
        elif self.path.startswith('/api/'):
            self.send_error_response(404, "Endpoint not found")
        else:
            # Serve static files
            super().do_GET()
    
    def send_json_response(self, data, status=200):
        """Send JSON response"""
        self.send_response(status)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode('utf-8'))
    
    def send_error_response(self, code, message):
        """Send error response"""
        self.send_json_response({
            'success': False,
            'error': message
        }, code)
    
    # API Handlers
    
    def handle_register(self, data):
        """Register a new customer"""
        required_fields = ['parent_name', 'phone', 'child_name']
        
        for field in required_fields:
            if field not in data or not data[field]:
                self.send_error_response(400, f"Missing required field: {field}")
                return
        
        try:
            customer_id = database.add_customer(
                parent_name=data['parent_name'],
                phone=data['phone'],
                email=data.get('email', ''),
                child_name=data['child_name'],
                child_age=data.get('child_age', ''),
                allergies=data.get('allergies', ''),
                notes=data.get('notes', '')
            )
            
            self.send_json_response({
                'success': True,
                'customer_id': customer_id,
                'message': 'Customer registered successfully'
            })
        except Exception as e:
            self.send_error_response(500, f"Registration failed: {str(e)}")
    
    def handle_payment_methods(self, data):
        """Get payment methods for a customer"""
        customer_id = data.get('customer_id')
        
        if not customer_id:
            self.send_error_response(400, "customer_id is required")
            return
        
        try:
            methods = database.get_payment_methods(customer_id)
            
            # Mask sensitive data
            for method in methods:
                if method['payment_type'] == 'credit_card':
                    method['card_number'] = f"****{method.get('card_number_last4', '')}"
                    method['card_number_last4'] = f"****{method.get('card_number_last4', '')}"
                elif method['payment_type'] == 'standing_order':
                    acc = method.get('account_number', '')
                    method['account_number'] = f"****{acc[-4:]}" if len(acc) >= 4 else "****"
            
            self.send_json_response({
                'success': True,
                'payment_methods': methods
            })
        except Exception as e:
            self.send_error_response(500, str(e))
    
    def handle_add_credit_card(self, data):
        """Add a credit card payment method"""
        required_fields = ['customer_id', 'card_number', 'card_holder_name', 
                          'expiry_month', 'expiry_year']
        
        for field in required_fields:
            if field not in data:
                self.send_error_response(400, f"Missing required field: {field}")
                return
        
        # Validate card
        is_valid, error_msg = payment_gateway.validate_credit_card(
            data['card_number'],
            data['expiry_month'],
            data['expiry_year'],
            data.get('cvv', '000')
        )
        
        if not is_valid:
            self.send_error_response(400, error_msg)
            return
        
        try:
            method_id = database.add_credit_card(
                customer_id=data['customer_id'],
                card_number=data['card_number'],
                card_holder_name=data['card_holder_name'],
                expiry_month=data['expiry_month'],
                expiry_year=data['expiry_year'],
                card_token=None,
                is_default=data.get('is_default', True)
            )
            
            # Detect card type
            card_type = payment_gateway.detect_card_type(data['card_number'])
            
            self.send_json_response({
                'success': True,
                'method_id': method_id,
                'card_type': card_type,
                'last4': data['card_number'][-4:],
                'message': 'Credit card added successfully'
            })
        except Exception as e:
            self.send_error_response(500, f"Failed to add card: {str(e)}")
    
    def handle_add_standing_order(self, data):
        """Add a standing order (הוראת קבע) payment method"""
        required_fields = ['customer_id', 'bank_code', 'branch_code', 
                          'account_number', 'account_holder_name']
        
        for field in required_fields:
            if field not in data:
                self.send_error_response(400, f"Missing required field: {field}")
                return
        
        # Validate standing order
        is_valid, error_msg = payment_gateway.validate_standing_order(
            data['bank_code'],
            data['branch_code'],
            data['account_number'],
            data['account_holder_name']
        )
        
        if not is_valid:
            self.send_error_response(400, error_msg)
            return
        
        try:
            method_id = database.add_standing_order(
                customer_id=data['customer_id'],
                bank_code=data['bank_code'],
                branch_code=data['branch_code'],
                account_number=data['account_number'],
                account_holder_name=data['account_holder_name'],
                is_default=data.get('is_default', True)
            )
            
            self.send_json_response({
                'success': True,
                'method_id': method_id,
                'message': 'Standing order added successfully'
            })
        except Exception as e:
            self.send_error_response(500, f"Failed to add standing order: {str(e)}")
    
    def handle_create_recurring(self, data):
        """Create a recurring payment plan"""
        required_fields = ['customer_id', 'payment_method_id', 'start_date']
        
        for field in required_fields:
            if field not in data:
                self.send_error_response(400, f"Missing required field: {field}")
                return
        
        try:
            recurring_id = database.create_recurring_payment(
                customer_id=data['customer_id'],
                payment_method_id=data['payment_method_id'],
                amount=data.get('amount', MONTHLY_AMOUNT),
                start_date=data['start_date'],
                frequency=data.get('frequency', 'monthly'),
                end_date=data.get('end_date')
            )
            
            self.send_json_response({
                'success': True,
                'recurring_id': recurring_id,
                'amount': data.get('amount', MONTHLY_AMOUNT),
                'frequency': data.get('frequency', 'monthly'),
                'start_date': data['start_date'],
                'message': f'Recurring payment of {data.get("amount", MONTHLY_AMOUNT)} ILS created successfully'
            })
        except Exception as e:
            self.send_error_response(500, f"Failed to create recurring payment: {str(e)}")
    
    def handle_process_payment(self, data):
        """Process a single payment"""
        required_fields = ['payment_id']
        
        for field in required_fields:
            if field not in data:
                self.send_error_response(400, f"Missing required field: {field}")
                return
        
        try:
            # In production, this would actually process the payment
            # For now, we simulate success
            result = payment_gateway.process_credit_card(
                card_number="4532015112830366",  # Test card
                card_holder_name="Test",
                expiry_month="12",
                expiry_year="2025",
                cvv="123",
                amount=MONTHLY_AMOUNT * 100  # Convert to agorot
            )
            
            if result.success:
                database.process_payment(
                    payment_id=data['payment_id'],
                    transaction_id=result.transaction_id,
                    authorization_code=result.authorization_code,
                    status='completed'
                )
            
            self.send_json_response({
                'success': result.success,
                'transaction_id': result.transaction_id,
                'message': result.message
            })
        except Exception as e:
            self.send_error_response(500, f"Payment processing failed: {str(e)}")
    
    def handle_cancel_recurring(self, data):
        """Cancel a recurring payment"""
        recurring_id = data.get('recurring_id')
        
        if not recurring_id:
            self.send_error_response(400, "recurring_id is required")
            return
        
        try:
            database.cancel_recurring_payment(recurring_id)
            self.send_json_response({
                'success': True,
                'message': 'Recurring payment cancelled'
            })
        except Exception as e:
            self.send_error_response(500, str(e))
    
    def handle_pause_recurring(self, data):
        """Pause a recurring payment"""
        recurring_id = data.get('recurring_id')
        
        if not recurring_id:
            self.send_error_response(400, "recurring_id is required")
            return
        
        try:
            database.pause_recurring_payment(recurring_id)
            self.send_json_response({
                'success': True,
                'message': 'Recurring payment paused'
            })
        except Exception as e:
            self.send_error_response(500, str(e))
    
    def handle_resume_recurring(self, data):
        """Resume a paused recurring payment"""
        recurring_id = data.get('recurring_id')
        
        if not recurring_id:
            self.send_error_response(400, "recurring_id is required")
            return
        
        try:
            database.resume_recurring_payment(recurring_id)
            self.send_json_response({
                'success': True,
                'message': 'Recurring payment resumed'
            })
        except Exception as e:
            self.send_error_response(500, str(e))
    
    def handle_payment_history(self, data):
        """Get payment history for a customer"""
        customer_id = data.get('customer_id')
        
        if not customer_id:
            self.send_error_response(400, "customer_id is required")
            return
        
        try:
            history = database.get_payment_history(
                customer_id=customer_id,
                limit=data.get('limit', 12)
            )
            
            self.send_json_response({
                'success': True,
                'payments': history
            })
        except Exception as e:
            self.send_error_response(500, str(e))
    
    def handle_validate_card(self, data):
        """Validate credit card details"""
        required_fields = ['card_number', 'expiry_month', 'expiry_year', 'cvv']
        
        for field in required_fields:
            if field not in data:
                self.send_error_response(400, f"Missing required field: {field}")
                return
        
        is_valid, error_msg = payment_gateway.validate_credit_card(
            data['card_number'],
            data['expiry_month'],
            data['expiry_year'],
            data['cvv']
        )
        
        card_type = payment_gateway.detect_card_type(data['card_number']) if is_valid else None
        
        self.send_json_response({
            'valid': is_valid,
            'error': error_msg,
            'card_type': card_type
        })
    
    def handle_validate_standing_order(self, data):
        """Validate standing order details"""
        required_fields = ['bank_code', 'branch_code', 'account_number', 'account_holder_name']
        
        for field in required_fields:
            if field not in data:
                self.send_error_response(400, f"Missing required field: {field}")
                return
        
        is_valid, error_msg = payment_gateway.validate_standing_order(
            data['bank_code'],
            data['branch_code'],
            data['account_number'],
            data['account_holder_name']
        )
        
        self.send_json_response({
            'valid': is_valid,
            'error': error_msg
        })


def run_server(port=PORT):
    """Start the billing server"""
    # Initialize database
    database.init_database()
    
    # Change to the script directory
    script_dir = Path(__file__).parent.absolute()
    os.chdir(script_dir)
    
    # Allow port reuse
    socketserver.TCPServer.allow_reuse_address = True
    
    try:
        with socketserver.TCPServer((HOST, port), BillingRequestHandler) as httpd:
            print(f"=" * 60)
            print(f"💰 Billing Server - עולם הילד")
            print(f"=" * 60)
            print(f"🌐 Server running at: http://localhost:{port}")
            print(f"💳 Monthly amount: {MONTHLY_AMOUNT} ILS")
            print(f"📁 Serving files from: {script_dir}")
            print(f"-" * 60)
            print("API Endpoints:")
            print("  POST /api/register - Register new customer")
            print("  POST /api/add-credit-card - Add credit card")
            print("  POST /api/add-standing-order - Add standing order")
            print("  POST /api/create-recurring - Create recurring payment")
            print("  GET  /api/config - Get billing configuration")
            print("-" * 60)
            print("Press Ctrl+C to stop the server")
            print("=" * 60)
            
            # Try to open browser
            try:
                webbrowser.open(f"http://localhost:{port}/index.html")
            except:
                pass
            
            httpd.serve_forever()
            
    except KeyboardInterrupt:
        print("\n🛑 Server stopped by user")
        sys.exit(0)
    except OSError as e:
        if "Address already in use" in str(e):
            print(f"❌ Port {port} is already in use")
            print("Trying port 8001...")
            run_server(8001)
        else:
            print(f"❌ Error starting server: {e}")
            sys.exit(1)


if __name__ == "__main__":
    # Check if index.html exists
    if not os.path.exists("index.html"):
        print("❌ Error: index.html not found")
        sys.exit(1)
    
    run_server()
