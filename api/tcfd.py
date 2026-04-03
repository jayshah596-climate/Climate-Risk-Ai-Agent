"""
api/tcfd.py
============
Vercel Python serverless function — TCFD / ISSB S2 Report Generator.
POST /api/tcfd
Body: { entityName, physicalData, transitionData, year }
"""

from http.server import BaseHTTPRequestHandler
import json
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'lib'))

from tcfd_reporter import build_tcfd_report


class handler(BaseHTTPRequestHandler):

    def do_OPTIONS(self):
        self._send_cors_headers(200)
        self.end_headers()

    def do_POST(self):
        try:
            length = int(self.headers.get('Content-Length', 0))
            body = json.loads(self.rfile.read(length)) if length else {}

            entity_name    = body.get('entityName', 'Entity')
            physical_data  = body.get('physicalData', {})
            transition_data = body.get('transitionData', {})
            year           = int(body.get('year', 2030))

            if not physical_data or not transition_data:
                self._send_json(400, {
                    'error': 'Both physicalData and transitionData are required.'
                })
                return

            report = build_tcfd_report(entity_name, physical_data, transition_data, year)
            self._send_json(200, report)

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
