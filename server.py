#!/usr/bin/env python3
"""
Billing Server - Web server with payment processing
Serves the landing page and handles billing API requests
"""

import http.server
import socketserver
import webbrowser
import os
import sys
import json
from pathlib import Path
from datetime import datetime, date

# Import billing modules
import database
import payment_gateway

# Configuration
PORT = 8000
HOST = "localhost"
MONTHLY_AMOUNT = 3500
CURRENCY = "ILS"

def run_server(port=PORT):
    """Start the billing server"""
    
    # Initialize database
    database.init_database()
    
    # Change to the directory containing this script
    script_dir = Path(__file__).parent.absolute()
    os.chdir(script_dir)
    
    # Create a custom handler that serves files and handles API
    class BillingRequestHandler(http.server.SimpleHTTPRequestHandler):
        def end_headers(self):
            self.send_header('Access-Control-Allow-Origin', '*')
            self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
            self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            super().end_headers()
        
        def do_OPTIONS(self):
            self.send_response(200)
            self.end_headers()
        
        def do_POST(self):
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length).decode('utf-8')
            
            try:
                data = json.loads(body) if body else {}
            except json.JSONDecodeError:
                self.send_error_response(400, "Invalid JSON")
                return
            
            # API Routes
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
            if self.path == '/api/config':
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
                super(http.server.SimpleHTTPRequestHandler, self).do_GET()
        
        def send_json_response(self, data, status=200):
            self.send_response(status)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.end_headers()
            self.wfile.write(json.dumps(data, ensure_ascii=False).encode('utf-8'))
        
        def send_error_response(self, code, message):
            self.send_json_response({'success': False, 'error': message}, code)
        
        def handle_register(self, data):
            required = ['parent_name', 'phone', 'child_name']
            for f in required:
                if f not in data or not data[f]:
                    self.send_error_response(400, f"Missing: {f}")
                    return
            try:
                cid = database.add_customer(data['parent_name'], data['phone'], 
                    data.get('email', ''), data['child_name'],
                    data.get('child_age', ''), data.get('allergies', ''), data.get('notes', ''))
                self.send_json_response({'success': True, 'customer_id': cid})
            except Exception as e:
                self.send_error_response(500, str(e))
        
        def handle_payment_methods(self, data):
            if not data.get('customer_id'):
                self.send_error_response(400, "customer_id required")
                return
            try:
                methods = database.get_payment_methods(data['customer_id'])
                for m in methods:
                    if m['payment_type'] == 'credit_card':
                        m['card_number'] = f"****{m.get('card_number_last4', '')}"
                    elif m['payment_type'] == 'standing_order':
                        acc = m.get('account_number', '')
                        m['account_number'] = f"****{acc[-4:]}" if len(acc) >= 4 else "****"
                self.send_json_response({'success': True, 'payment_methods': methods})
            except Exception as e:
                self.send_error_response(500, str(e))
        
        def handle_add_credit_card(self, data):
            required = ['customer_id', 'card_number', 'card_holder_name', 'expiry_month', 'expiry_year']
            for f in required:
                if f not in data:
                    self.send_error_response(400, f"Missing: {f}")
                    return
            is_valid, err = payment_gateway.validate_credit_card(
                data['card_number'], data['expiry_month'], data['expiry_year'], data.get('cvv', '000'))
            if not is_valid:
                self.send_error_response(400, err)
                return
            try:
                mid = database.add_credit_card(data['customer_id'], data['card_number'],
                    data['card_holder_name'], data['expiry_month'], data['expiry_year'],
                    None, data.get('is_default', True))
                self.send_json_response({'success': True, 'method_id': mid, 'last4': data['card_number'][-4:]})
            except Exception as e:
                self.send_error_response(500, str(e))
        
        def handle_add_standing_order(self, data):
            required = ['customer_id', 'bank_code', 'branch_code', 'account_number', 'account_holder_name']
            for f in required:
                if f not in data:
                    self.send_error_response(400, f"Missing: {f}")
                    return
            is_valid, err = payment_gateway.validate_standing_order(
                data['bank_code'], data['branch_code'], data['account_number'], data['account_holder_name'])
            if not is_valid:
                self.send_error_response(400, err)
                return
            try:
                mid = database.add_standing_order(data['customer_id'], data['bank_code'],
                    data['branch_code'], data['account_number'], data['account_holder_name'],
                    data.get('is_default', True))
                self.send_json_response({'success': True, 'method_id': mid})
            except Exception as e:
                self.send_error_response(500, str(e))
        
        def handle_create_recurring(self, data):
            required = ['customer_id', 'payment_method_id', 'start_date']
            for f in required:
                if f not in data:
                    self.send_error_response(400, f"Missing: {f}")
                    return
            try:
                rid = database.create_recurring_payment(data['customer_id'], data['payment_method_id'],
                    data.get('amount', MONTHLY_AMOUNT), data['start_date'],
                    data.get('frequency', 'monthly'), data.get('end_date'))
                self.send_json_response({'success': True, 'recurring_id': rid, 'amount': data.get('amount', MONTHLY_AMOUNT)})
            except Exception as e:
                self.send_error_response(500, str(e))
        
        def handle_process_payment(self, data):
            if not data.get('payment_id'):
                self.send_error_response(400, "payment_id required")
                return
            result = payment_gateway.process_credit_card("4532015112830366", "Test", "12", "2025", "123", MONTHLY_AMOUNT * 100)
            if result.success:
                database.process_payment(data['payment_id'], result.transaction_id, result.authorization_code, 'completed')
            self.send_json_response({'success': result.success, 'transaction_id': result.transaction_id, 'message': result.message})
        
        def handle_cancel_recurring(self, data):
            if not data.get('recurring_id'):
                self.send_error_response(400, "recurring_id required")
                return
            database.cancel_recurring_payment(data['recurring_id'])
            self.send_json_response({'success': True})
        
        def handle_pause_recurring(self, data):
            if not data.get('recurring_id'):
                self.send_error_response(400, "recurring_id required")
                return
            database.pause_recurring_payment(data['recurring_id'])
            self.send_json_response({'success': True})
        
        def handle_resume_recurring(self, data):
            if not data.get('recurring_id'):
                self.send_error_response(400, "recurring_id required")
                return
            database.resume_recurring_payment(data['recurring_id'])
            self.send_json_response({'success': True})
        
        def handle_payment_history(self, data):
            if not data.get('customer_id'):
                self.send_error_response(400, "customer_id required")
                return
            try:
                history = database.get_payment_history(data['customer_id'], data.get('limit', 12))
                self.send_json_response({'success': True, 'payments': history})
            except Exception as e:
                self.send_error_response(500, str(e))
        
        def handle_validate_card(self, data):
            required = ['card_number', 'expiry_month', 'expiry_year', 'cvv']
            for f in required:
                if f not in data:
                    self.send_error_response(400, f"Missing: {f}")
                    return
            is_valid, err = payment_gateway.validate_credit_card(data['card_number'], data['expiry_month'], data['expiry_year'], data['cvv'])
            card_type = payment_gateway.detect_card_type(data['card_number']) if is_valid else None
            self.send_json_response({'valid': is_valid, 'error': err, 'card_type': card_type})
        
        def handle_validate_standing_order(self, data):
            required = ['bank_code', 'branch_code', 'account_number', 'account_holder_name']
            for f in required:
                if f not in data:
                    self.send_error_response(400, f"Missing: {f}")
                    return
            is_valid, err = payment_gateway.validate_standing_order(data['bank_code'], data['branch_code'], data['account_number'], data['account_holder_name'])
            self.send_json_response({'valid': is_valid, 'error': err})
    
    socketserver.TCPServer.allow_reuse_address = True
    
    try:
        with socketserver.TCPServer((HOST, port), BillingRequestHandler) as httpd:
            print(f"{'='*50}")
            print(f"💰 Billing Server - עולם הילד")
            print(f"{'='*50}")
            print(f"🌐 Server running at: http://localhost:{port}")
            print(f"💳 Monthly amount: {MONTHLY_AMOUNT} ILS")
            print(f"📁 Serving files from: {script_dir}")
            print(f"{'-'*50}")
            print("Pages:")
            print(f"  - http://localhost:{port}/index.html (Home)")
            print(f"  - http://localhost:{port}/billing.html (Payment)")
            print(f"{'-'*50}")
            print("Press Ctrl+C to stop")
            print(f"{'='*50}")
            
            try:
                webbrowser.open(f"http://localhost:{port}/index.html")
            except:
                pass
            
            httpd.serve_forever()
            
    except KeyboardInterrupt:
        print("\n🛑 Server stopped")
        sys.exit(0)
    except OSError as e:
        if "Address already in use" in str(e):
            print(f"❌ Port {port} is already in use")
            print("Trying port 8001...")
            run_server(8001)
        else:
            print(f"❌ Error: {e}")
            sys.exit(1)

if __name__ == "__main__":
    if not os.path.exists("index.html"):
        print("❌ Error: index.html not found")
        sys.exit(1)
    run_server()
