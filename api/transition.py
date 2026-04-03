"""
api/transition.py
==================
Vercel Python serverless function — Transition Risk & Carbon Stress Test.
POST /api/transition
Body: { scope1, scope2, scope3, assetValue, sector, scenario }
"""

from http.server import BaseHTTPRequestHandler
import json
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'lib'))

from carbon_pricing import stress_test_transition, compare_scenarios


class handler(BaseHTTPRequestHandler):

    def do_OPTIONS(self):
        self._send_cors_headers(200)
        self.end_headers()

    def do_POST(self):
        try:
            length = int(self.headers.get('Content-Length', 0))
            body = json.loads(self.rfile.read(length)) if length else {}

            scope1      = float(body.get('scope1', 0))
            scope2      = float(body.get('scope2', 0))
            scope3      = float(body.get('scope3', 0))
            asset_value = float(body.get('assetValue', 1_000_000))
            sector      = body.get('sector', 'general')
            scenario    = body.get('scenario', 'Net Zero 2050')

            stress = stress_test_transition(scope1, scope2, scenario, sector, asset_value, scope3)
            comparison = compare_scenarios(scope1, scope2, sector, asset_value, 2030)

            self._send_json(200, {**stress, 'scenario_comparison': comparison})

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
