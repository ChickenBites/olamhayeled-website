#!/usr/bin/env python3
"""
Simple Python web server to serve the landing page
"""

import http.server
import socketserver
import webbrowser
import os
import sys
from pathlib import Path

def run_server(port=8000):
    """Start a simple HTTP server and open the browser"""
    
    # Change to the directory containing this script
    script_dir = Path(__file__).parent.absolute()
    os.chdir(script_dir)
    
    # Create a custom handler that serves files with proper MIME types
    class CustomHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
        def end_headers(self):
            # Add CORS headers for local development
            self.send_header('Access-Control-Allow-Origin', '*')
            self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
            self.send_header('Access-Control-Allow-Headers', 'Content-Type')
            super().end_headers()
    
    try:
        with socketserver.TCPServer(("", port), CustomHTTPRequestHandler) as httpd:
            print(f"🌐 Server running at: http://localhost:{port}")
            print(f"📁 Serving files from: {script_dir}")
            print("Press Ctrl+C to stop the server")
            print("-" * 50)
            
            # Try to open the browser automatically
            try:
                webbrowser.open(f"http://localhost:{port}/index.html")
                print("✅ Browser opened automatically")
            except Exception as e:
                print(f"⚠️  Could not open browser automatically: {e}")
                print(f"Please manually open: http://localhost:{port}/index.html")
            
            print("\nServer is running...")
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
        print("❌ Error: index.html not found in current directory")
        print("Please make sure index.html is in the same directory as this script")
        sys.exit(1)
    
    # Start the server
    run_server()