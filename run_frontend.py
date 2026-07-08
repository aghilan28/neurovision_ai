#!/usr/bin/env python3
"""
NEUROVISION FRONTEND SERVER
Serves your existing HTML files (upload.html, code.html, etc.)
and proxies API calls to the backend on port 8080.

Run this AFTER starting the backend:
    python run_with_real_model.py

Then run:
    python run_frontend.py

Frontend will be at: http://localhost:5173
"""

import os
import sys
from http.server import HTTPServer, SimpleHTTPRequestHandler
import urllib.request
import urllib.error

FRONTEND_PORT = 5173
BACKEND_URL = "http://localhost:8080"

# Best frontend entry points (in order of preference)
POSSIBLE_ENTRY = [
    "upload.html",
    "code.html",
    "runtime_frontend_preview/upload.html",
    "runtime_frontend_preview/index.html",
]

class ProxyHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=os.getcwd(), **kwargs)

    def do_GET(self):
        # Root → serve best available frontend page
        if self.path in ("/", ""):
            for page in POSSIBLE_ENTRY:
                if os.path.exists(page):
                    self.path = "/" + page
                    break

        # Proxy API calls
        if self.path.startswith(("/api/", "/v1/", "/upload_and_analyze", "/health")):
            self.proxy_request()
            return

        # Normal static file
        super().do_GET()

    def do_POST(self):
        if self.path.startswith(("/api/", "/v1/", "/upload_and_analyze")):
            self.proxy_request()
        else:
            self.send_error(405, "Method Not Allowed")

    def proxy_request(self):
        """Forward request to real backend"""
        try:
            content_length = int(self.headers.get('Content-Length', 0) or 0)
            body = self.rfile.read(content_length) if content_length > 0 else None

            target = BACKEND_URL + self.path

            req = urllib.request.Request(target, data=body, method=self.command)

            # Forward important headers
            for h in ['Content-Type', 'Authorization']:
                if h in self.headers:
                    req.add_header(h, self.headers[h])

            with urllib.request.urlopen(req, timeout=60) as resp:
                self.send_response(resp.status)
                for key, val in resp.getheaders():
                    if key.lower() not in ('transfer-encoding', 'content-encoding'):
                        self.send_header(key, val)
                self.end_headers()
                self.wfile.write(resp.read())

        except urllib.error.HTTPError as e:
            self.send_response(e.code)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(e.read())
        except Exception as e:
            self.send_error(502, f"Backend unreachable: {e}")

    def end_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', '*')
        self.send_header('Access-Control-Allow-Headers', '*')
        super().end_headers()

    def do_OPTIONS(self):
        self.send_response(200)
        self.end_headers()


if __name__ == "__main__":
    os.chdir(os.path.dirname(os.path.abspath(__file__)) or ".")

    print("=" * 60)
    print("NEUROVISION FRONTEND SERVER")
    print("=" * 60)
    print(f"Frontend URL:     http://localhost:{FRONTEND_PORT}")
    print(f"Backend (proxy):  {BACKEND_URL}")
    print()
    print("Make sure backend is already running:")
    print("   python run_with_real_model.py")
    print()
    print("Then open in browser:")
    print(f"   http://localhost:{FRONTEND_PORT}")
    print(f"   http://localhost:{FRONTEND_PORT}/upload.html")
    print("=" * 60)
    print()

    httpd = HTTPServer(('0.0.0.0', FRONTEND_PORT), ProxyHandler)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nFrontend stopped.")
        httpd.server_close()
