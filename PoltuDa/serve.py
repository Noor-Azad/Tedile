#!/usr/bin/env python3
"""Simple HTTP Server for PoltuDa Frontend"""
import http.server
import socketserver
import os

os.chdir('/Users/noorazad/Tedile')

PORT = 8080
Handler = http.server.SimpleHTTPRequestHandler

with socketserver.TCPServer(("127.0.0.1", PORT), Handler) as httpd:
    print(f"Server running at http://127.0.0.1:{PORT}")
    print(f"Frontend available at http://127.0.0.1:{PORT}/index.html")
    print("Press Ctrl+C to stop")
    httpd.serve_forever()
