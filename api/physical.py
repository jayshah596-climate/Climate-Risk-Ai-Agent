"""
api/physical.py
================
Vercel Python serverless function — Physical Climate Risk Analysis.
POST /api/physical
Body: { location, scenario, year, hazards }
"""

from http.server import BaseHTTPRequestHandler
import json
import sys
import os

# Add lib/ to path so we can import the model modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'lib'))

from hazard_model import run_hazard_analysis
from location_check import geocode, get_elevation_info


class handler(BaseHTTPRequestHandler):

    def do_OPTIONS(self):
        self._send_cors_headers(200)
        self.end_headers()

    def do_POST(self):
        try:
            length = int(self.headers.get('Content-Length', 0))
            body = json.loads(self.rfile.read(length)) if length else {}

            location   = body.get('location', '')
            scenario   = body.get('scenario', 'ssp585')
            year       = int(body.get('year', 2050))
            hazards    = body.get('hazards', 'all')

            # Resolve location
            coords = geocode(location)
            if coords.get('error'):
                self._send_json(400, {'error': coords['error']})
                return

            lat = coords['lat']
            lon = coords['lon']

            # Elevation info (non-blocking — may return None)
            elev = get_elevation_info(lat, lon)

            # Run hazard model
            result = run_hazard_analysis(lat, lon, scenario, year, hazards)
            result['location_info'] = {
                'display_name': coords.get('display_name', location),
                'lat': lat,
                'lon': lon,
                'country': coords.get('country', ''),
                'elevation_m': elev.get('elevation_m'),
                'coastal_risk_flag': elev.get('coastal_risk_flag', False),
            }

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
        pass  # Suppress default access log noise in serverless
