"""
physical/location_check.py
===========================
Resolves place names → (lat, lon) using the free Nominatim OpenStreetMap API.
No API key required. Rate limit: 1 request/second.

Usage:
  python physical/location_check.py "Vadodara, India"
  python physical/location_check.py "Port of Rotterdam"
  python physical/location_check.py "23.0225,72.5714"   # pass lat,lon directly
"""

import sys
import json
import time
import urllib.request
import urllib.parse

NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
USER_AGENT = "ClimateRiskEngine/1.0 (BTW-AI; contact@btw-ai.site)"

def geocode(location_str: str) -> dict:
    """
    Returns: {"lat": float, "lon": float, "display_name": str, "source": str}
    """
    # If user passed "lat,lon" directly, parse and return
    parts = location_str.strip().split(",")
    if len(parts) == 2:
        try:
            lat = float(parts[0].strip())
            lon = float(parts[1].strip())
            return {"lat": lat, "lon": lon, "display_name": location_str, "source": "user_input"}
        except ValueError:
            pass
    
    # Geocode via Nominatim (free OSM API)
    params = urllib.parse.urlencode({
        "q": location_str,
        "format": "json",
        "limit": 1,
        "addressdetails": 1,
    })
    url = f"{NOMINATIM_URL}?{params}"
    
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    
    try:
        time.sleep(1)   # respect Nominatim rate limit
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())
    except Exception as e:
        return {"error": f"Geocoding failed: {str(e)}", "lat": None, "lon": None}
    
    if not data:
        return {"error": f"No results found for '{location_str}'", "lat": None, "lon": None}
    
    result = data[0]
    return {
        "lat": float(result["lat"]),
        "lon": float(result["lon"]),
        "display_name": result.get("display_name", location_str),
        "country": result.get("address", {}).get("country", "Unknown"),
        "source": "OpenStreetMap Nominatim (free)",
    }

def get_elevation_info(lat: float, lon: float) -> dict:
    """
    Fetch elevation from Open-Elevation API (free, no key).
    Useful for sea-level rise and flood depth assessment.
    """
    url = f"https://api.open-elevation.com/api/v1/lookup?locations={lat},{lon}"
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=8) as resp:
            data = json.loads(resp.read().decode())
        elevation_m = data["results"][0]["elevation"]
        return {
            "elevation_m": elevation_m,
            "coastal_risk_flag": elevation_m < 10,
            "note": "Elevation < 10m = elevated coastal flood / SLR exposure",
        }
    except Exception:
        return {"elevation_m": None, "note": "Elevation data unavailable (offline or API error)"}

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print('Usage: python physical/location_check.py "City, Country"')
        sys.exit(1)
    
    location_input = " ".join(sys.argv[1:])
    coords = geocode(location_input)
    print(json.dumps(coords, indent=2))
    
    if coords.get("lat") and coords.get("lon"):
        elev = get_elevation_info(coords["lat"], coords["lon"])
        print("\nElevation data:")
        print(json.dumps(elev, indent=2))
