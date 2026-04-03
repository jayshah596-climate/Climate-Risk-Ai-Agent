"""
api/stranded.py
================
Vercel Python serverless function — Stranded Asset Risk Assessment.
POST /api/stranded
Body: { assetType, scenario, year }
"""

from http.server import BaseHTTPRequestHandler
import json
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'lib'))

from stranded_asset import assess_stranded_asset, STRANDING_PROBABILITIES


class handler(BaseHTTPRequestHandler):

    def do_OPTIONS(self):
        self._send_cors_headers(200)
        self.end_headers()

    def do_POST(self):
        try:
            length = int(self.headers.get('Content-Length', 0))
            body = json.loads(self.rfile.read(length)) if length else {}

            asset_type = body.get('assetType', 'coal_plant')
            scenario   = body.get('scenario', 'Net Zero 2050')
            year       = int(body.get('year', 2035))

            result = assess_stranded_asset(asset_type, scenario, year)

            # Also return asset type list for the frontend dropdown
            result['available_asset_types'] = list(STRANDING_PROBABILITIES.keys())

            self._send_json(200, result)

        except Exception as e:
            self._send_json(500, {'error': str(e)})

    def _send_json(self, status, data):
        body = json.dumps(data).encode()
        self._send_cors_headers(status)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_cors_headers(self, status):
        self.send_response(status)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')

    def log_message(self, format, *args):
        pass
