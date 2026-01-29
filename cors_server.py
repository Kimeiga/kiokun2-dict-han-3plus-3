#!/usr/bin/env python3
"""
Simple HTTP server with CORS enabled for local development.
Run this in the output_dictionary folder to serve dictionary files locally.

MODES:
1. SQLite mode (fast): Uses dictionary.db if present
2. File mode (fallback): Uses individual .json.deflate files

Usage:
    cd output_dictionary && python3 cors_server.py
"""

from http.server import HTTPServer, BaseHTTPRequestHandler
import sys
import socket
import os
import sqlite3
from urllib.parse import unquote

# Global SQLite connection (for SQLite mode)
db_connection = None

class CORSRequestHandler(BaseHTTPRequestHandler):
    def end_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', '*')
        self.send_header('Cache-Control', 'no-store, no-cache, must-revalidate')
        super().end_headers()

    def do_OPTIONS(self):
        self.send_response(200)
        self.end_headers()

    def do_GET(self):
        global db_connection

        # Parse the requested word from URL (e.g., /word.json.deflate -> word)
        path = unquote(self.path.lstrip('/'))

        # Remove .json.deflate suffix if present
        if path.endswith('.json.deflate'):
            word = path[:-13]  # Remove '.json.deflate' (13 chars)
        else:
            word = path

        if not word:
            self.send_error(400, 'No word specified')
            return

        # Try SQLite first if connection is available
        if db_connection is not None:
            try:
                cursor = db_connection.cursor()
                cursor.execute("SELECT json_data FROM entries WHERE word = ?", (word,))
                row = cursor.fetchone()

                if row:
                    # Found in database - return compressed data
                    self.send_response(200)
                    self.send_header('Content-Type', 'application/octet-stream')
                    self.send_header('Content-Length', len(row[0]))
                    self.end_headers()
                    self.wfile.write(row[0])
                    return
                else:
                    self.send_error(404, f'Word "{word}" not found in database')
                    return
            except Exception as e:
                self.send_error(500, f'Database error: {e}')
                return
        else:
            # Fallback to file-based serving
            file_path = f"{word}.json.deflate"
            if os.path.exists(file_path):
                try:
                    with open(file_path, 'rb') as f:
                        data = f.read()
                    self.send_response(200)
                    self.send_header('Content-Type', 'application/octet-stream')
                    self.send_header('Content-Length', len(data))
                    self.end_headers()
                    self.wfile.write(data)
                    return
                except Exception as e:
                    self.send_error(500, f'File read error: {e}')
                    return
            else:
                self.send_error(404, f'Word "{word}" not found')
                return

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
    # Check for SQLite database
    db_path = os.path.join(os.path.dirname(__file__), 'dictionary.db')
    if os.path.exists(db_path):
        try:
            db_connection = sqlite3.connect(db_path, check_same_thread=False)
            # Get entry count
            cursor = db_connection.cursor()
            cursor.execute("SELECT COUNT(*) FROM entries")
            count = cursor.fetchone()[0]
            print(f'📚 Using SQLite database with {count:,} entries', flush=True)
        except Exception as e:
            print(f'⚠️  Failed to open SQLite database: {e}', flush=True)
            print('📁 Falling back to file-based serving', flush=True)
            db_connection = None
    else:
        print('📁 No dictionary.db found, using file-based serving', flush=True)

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
        # Close database connection
        if db_connection:
            db_connection.close()

