#!/usr/bin/env python3
"""
Simple HTTP server with CORS enabled for local development.
Run this in the output_dictionary folder to serve dictionary files locally.

Usage:
    cd output_dictionary && python3 cors_server.py
"""

from http.server import HTTPServer, SimpleHTTPRequestHandler
import sys
import socket
import os

class CORSRequestHandler(SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', '*')
        self.send_header('Cache-Control', 'no-store, no-cache, must-revalidate')
        super().end_headers()

    def do_OPTIONS(self):
        self.send_response(200)
        self.end_headers()

    # Suppress request logging for cleaner output
    def log_message(self, format, *args):
        pass  # Comment out to see request logs

def find_available_port(start_port=8000, max_attempts=100):
    """Find the first available port starting from start_port"""
    for port in range(start_port, start_port + max_attempts):
        try:
            # Try to bind to the port
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.bind(('', port))
            sock.close()
            return port
        except OSError:
            # Port is in use, try next one
            continue
    raise RuntimeError(f"Could not find available port in range {start_port}-{start_port + max_attempts}")

if __name__ == '__main__':
    # Find first available port starting from 8000
    port = find_available_port(8000)

    # Write port to a file BEFORE starting the server
    # This ensures Vite can read it as soon as the server is ready
    port_file = os.path.join(os.path.dirname(__file__), '.cors_port')
    with open(port_file, 'w') as f:
        f.write(str(port))

    # Flush to ensure the file is written immediately
    sys.stdout.flush()

    server_address = ('', port)
    httpd = HTTPServer(server_address, CORSRequestHandler)

    # Print AFTER server is bound and ready
    print(f'🚀 CORS server ready on http://localhost:{port}/', flush=True)

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print('\n👋 Shutting down server...')
        # Clean up port file on exit
        if os.path.exists(port_file):
            os.remove(port_file)

