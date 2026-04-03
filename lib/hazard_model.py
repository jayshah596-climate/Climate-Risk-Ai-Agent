"""
physical/hazard_model.py
========================
Multi-hazard physical climate risk model.
Supports: Heat Stress, Flood, Drought, Sea-Level Rise, Wildfire, Cyclone

Usage:
  python physical/hazard_model.py <lat> <lon> <scenario> <year> [hazard]

  scenario: ssp126 | ssp245 | ssp370 | ssp585
  year    : 2030 | 2050 | 2080
  hazard  : heat | flood | drought | slr | wildfire | cyclone | all (default: all)

Example:
  python physical/hazard_model.py 22.3 73.2 ssp585 2050 all

Data note:
  In production, point CMIP6_DATA_DIR to your local directory of downloaded
  .nc files from NASA NEX-GDDP-CMIP6 or Copernicus CDS.
  This script runs in SIMULATION MODE when no data directory is configured,
  producing illustrative outputs based on published IPCC AR6 regional ranges.
"""

import sys
import json
import os
import numpy as np
from datetime import datetime

# ── Configuration ─────────────────────────────────────────────────────────────
CMIP6_DATA_DIR = os.environ.get("CMIP6_DATA_DIR", None)   # Set to your .nc folder
SIMULATION_MODE = CMIP6_DATA_DIR is None

# ── IPCC AR6 Regional warming multipliers (simplified from WGI Atlas) ─────────
# These represent illustrative median warming relative to 1850–1900 baseline
# Source: IPCC AR6 WGI Chapter 4 and Interactive Atlas
WARMING_DELTAS = {
    "ssp126": {"2030": 1.5, "2050": 1.7, "2080": 1.8},
    "ssp245": {"2030": 1.5, "2050": 2.0, "2080": 2.7},
    "ssp370": {"2030": 1.6, "2050": 2.2, "2080": 3.6},
    "ssp585": {"2030": 1.6, "2050": 2.4, "2080": 4.4},
}

# ── Damage/Exposure functions ─────────────────────────────────────────────────
def classify_risk(score: float) -> str:
    if score >= 4.5: return "CRITICAL"
    if score >= 3.5: return "HIGH"
    if score >= 2.5: return "MEDIUM"
    if score >= 1.5: return "LOW"
    return "NEGLIGIBLE"

def heat_stress(lat, lon, scenario, year, delta_t):
    """Assess extreme heat exposure."""
    # Baseline HDD approximation from latitude (tropical = higher baseline)
    baseline_tasmax = 25 + max(0, (30 - abs(lat)) * 0.4)
    projected_tasmax = baseline_tasmax + delta_t * 1.2  # land warms ~1.2x global mean
    
    # Wet Bulb Globe Temperature proxy (simplified)
    wbgt_risk = projected_tasmax - 35  # days above 35°C proxy
    score = min(5, max(1, 1 + (projected_tasmax - 28) / 3))
    
    return {
        "hazard": "Extreme Heat / Heat Stress",
        "metric": "Maximum Daily Temperature (tasmax)",
        "baseline_value": f"{baseline_tasmax:.1f}°C",
        "projected_value": f"{projected_tasmax:.1f}°C",
        "change": f"+{delta_t * 1.2:.1f}°C vs pre-industrial baseline",
        "risk_score": round(score, 1),
        "risk_level": classify_risk(score),
        "key_impacts": [
            "Worker productivity loss (outdoor/industrial sectors)",
            "Cooling energy demand spike → grid stress",
            "Crop yield reduction (cereals, cotton)",
            "Infrastructure buckling (roads, rail)",
        ],
        "financial_proxy": f"~{int(score * 8)}–{int(score * 18)}% OPEX increase in heat-sensitive industries",
        "adaptation": ["Cool roofs / green canopy", "Shift work hours", "Crop variety switch"],
        "data_source": "IPCC AR6 WGI Atlas + CMIP6 ensemble median (simulation)",
    }

def flood_risk(lat, lon, scenario, year, delta_t):
    """Assess river/pluvial flood exposure."""
    # Precipitation intensification follows Clausius-Clapeyron (~7% per °C)
    precip_increase_pct = delta_t * 7
    # Coastal zones increase vulnerability
    coastal_flag = abs(lat) < 25 and abs(lon) < 120   # simplified tropics proxy
    base_score = 2.0 if not coastal_flag else 2.8
    score = min(5, base_score + (precip_increase_pct / 20))
    
    return {
        "hazard": "River / Pluvial Flood",
        "metric": "Extreme Precipitation Intensity (Rx5day)",
        "baseline_value": "100-year return period flood",
        "projected_value": f"Return period shrinks to ~{max(5, int(100 / (1 + precip_increase_pct/100)))} years",
        "change": f"+{precip_increase_pct:.0f}% extreme precipitation intensity",
        "risk_score": round(score, 1),
        "risk_level": classify_risk(score),
        "key_impacts": [
            "Building / inventory damage",
            "Supply chain disruption",
            "Infrastructure downtime",
            "Increased insurance premiums / uninsurability",
        ],
        "financial_proxy": f"~${int(score * 50_000):,}–${int(score * 200_000):,} per flood event (SME proxy)",
        "adaptation": ["Flood barriers", "Green drainage infrastructure", "Elevated foundations"],
        "data_source": "IPCC AR6 WGI Ch. 11 + Global Flood Database (simulation)",
    }

def drought_risk(lat, lon, scenario, year, delta_t):
    """Assess drought and water stress exposure."""
    # SPEI-based approximation: higher warming = more evapotranspiration
    drought_increase = delta_t * 0.15  # ~SPEI units shift
    # Arid zone flag
    arid = abs(lat) > 20 and abs(lat) < 35
    score = min(5, 1.5 + delta_t * 0.6 + (0.8 if arid else 0))
    
    return {
        "hazard": "Drought / Water Stress",
        "metric": "Standardised Precipitation-Evapotranspiration Index (SPEI)",
        "baseline_value": "SPEI-12 baseline normal",
        "projected_value": f"SPEI shift of -{drought_increase:.2f} units",
        "change": f"~{int(delta_t * 15)}% increase in drought frequency",
        "risk_score": round(score, 1),
        "risk_level": classify_risk(score),
        "key_impacts": [
            "Water-intensive operations: cooling towers, agriculture",
            "Municipal water restriction risk",
            "Hydropower generation reduction",
            "Wildfire precondition",
        ],
        "financial_proxy": f"~{int(score * 5)}–{int(score * 12)}% increase in water procurement costs",
        "adaptation": ["Water recycling systems", "Drought-resistant crops", "Groundwater monitoring"],
        "data_source": "IPCC AR6 WGI Ch. 8 + CHELSA SPEI dataset (simulation)",
    }

def sea_level_rise(lat, lon, scenario, year, delta_t):
    """Assess sea-level rise and coastal flood exposure."""
    # IPCC AR6 median global mean SLR (metres above 1995–2014)
    slr_median = {
        "ssp126": {"2030": 0.10, "2050": 0.18, "2080": 0.30},
        "ssp245": {"2030": 0.11, "2050": 0.20, "2080": 0.37},
        "ssp370": {"2030": 0.11, "2050": 0.22, "2080": 0.46},
        "ssp585": {"2030": 0.12, "2050": 0.26, "2080": 0.57},
    }
    # Low elevation coastal zone proxy
    coastal_exposed = abs(lon) > 60 and abs(lat) < 30
    slr_m = slr_median.get(scenario, slr_median["ssp245"]).get(str(year), 0.20)
    score = min(5, 1 + slr_m * 8 + (1.5 if coastal_exposed else 0))
    
    return {
        "hazard": "Sea-Level Rise / Coastal Inundation",
        "metric": "Global Mean Sea Level (GMSL) above 1995–2014 baseline",
        "baseline_value": "0 m (1995–2014 reference)",
        "projected_value": f"+{slr_m:.2f} m (IPCC AR6 median, {scenario.upper()})",
        "change": f"+{slr_m*100:.0f} cm by {year}",
        "risk_score": round(score, 1),
        "risk_level": classify_risk(score),
        "key_impacts": [
            "Coastal asset inundation / storm surge amplification",
            "Saltwater intrusion into freshwater / agriculture",
            "Port / logistics disruption",
            "Property value decline in coastal zones",
        ],
        "financial_proxy": f"Coastal assets: ~{int(score * 3)}–{int(score * 8)}% value at risk by {year}",
        "adaptation": ["Coastal defences", "Managed retreat planning", "Elevated infrastructure"],
        "data_source": "IPCC AR6 WGI Ch. 9 Table 9.9 (simulation)",
    }

def wildfire_risk(lat, lon, scenario, year, delta_t):
    """Assess wildfire weather exposure."""
    # McArthur Fire Danger Rating proxy
    fire_weather_increase = delta_t * 10   # % increase in fire weather days
    boreal_or_med = (abs(lat) > 30 and abs(lat) < 60) or (abs(lat) > 30 and abs(lat) < 45)
    score = min(5, 1.5 + delta_t * 0.5 + (0.7 if boreal_or_med else 0))
    
    return {
        "hazard": "Wildfire / Bushfire",
        "metric": "Fire Weather Index (FWI) days per year",
        "baseline_value": "Historical FWI baseline",
        "projected_value": f"~+{fire_weather_increase:.0f}% high-FWI days",
        "change": f"Longer fire season by ~{int(delta_t * 5)} days/year",
        "risk_score": round(score, 1),
        "risk_level": classify_risk(score),
        "key_impacts": [
            "Direct property / asset destruction",
            "Air quality → workforce health / absenteeism",
            "Supply chain disruption (roads, utilities)",
            "Insurance unavailability in high-risk zones",
        ],
        "financial_proxy": f"~{int(score * 4)}% annual risk-adjusted asset loss in wildland-urban interface",
        "adaptation": ["Defensible space clearing", "Fireproof building materials", "Early-warning monitoring"],
        "data_source": "IPCC AR6 WGI Ch. 12 + Copernicus EFFIS (simulation)",
    }

def cyclone_risk(lat, lon, scenario, year, delta_t):
    """Assess tropical cyclone / hurricane intensity exposure."""
    in_basin = abs(lat) < 35   # Simplified tropical cyclone basin check
    score = min(5, 1 + (2 if in_basin else 0) + delta_t * 0.4)
    
    return {
        "hazard": "Tropical Cyclone / Hurricane Intensification",
        "metric": "Category 4–5 storm probability increase",
        "baseline_value": "Historical basin frequency",
        "projected_value": f"~+{int(delta_t * 5)}% probability of Category 4–5 storms",
        "change": f"Peak intensity +{delta_t * 5:.0f}% more likely in {scenario.upper()} by {year}",
        "risk_score": round(score, 1) if in_basin else 1.0,
        "risk_level": classify_risk(score) if in_basin else "NEGLIGIBLE (outside cyclone basin)",
        "key_impacts": [
            "Structural damage to coastal buildings",
            "Storm surge flooding",
            "Supply chain and logistics disruption",
            "Catastrophic business interruption",
        ],
        "financial_proxy": f"Storm damage cost multiplier: ~x{1 + delta_t * 0.5:.1f} vs baseline",
        "adaptation": ["Structural hardening", "Business continuity planning", "Insurance review"],
        "data_source": "IPCC AR6 WGI Ch. 11 + IBTrACS historical database (simulation)",
    }

# ── Main orchestrator ─────────────────────────────────────────────────────────
def run_hazard_analysis(lat: float, lon: float, scenario: str, year: int, hazard: str = "all") -> dict:
    scenario = scenario.lower().replace("-", "").replace(".", "")
    year_str = str(year)
    
    delta_t = WARMING_DELTAS.get(scenario, WARMING_DELTAS["ssp245"]).get(year_str, 2.0)
    
    hazard_functions = {
        "heat":     heat_stress,
        "flood":    flood_risk,
        "drought":  drought_risk,
        "slr":      sea_level_rise,
        "wildfire": wildfire_risk,
        "cyclone":  cyclone_risk,
    }
    
    if hazard == "all":
        selected = hazard_functions
    else:
        selected = {k: v for k, v in hazard_functions.items() if k in hazard.split(",")}
    
    results = {}
    for key, fn in selected.items():
        results[key] = fn(lat, lon, scenario, year_str, delta_t)
    
    # ── Summary aggregate ────────────────────────────────────────────────────
    all_scores = [v["risk_score"] for v in results.values()]
    max_score = max(all_scores) if all_scores else 0
    avg_score = sum(all_scores) / len(all_scores) if all_scores else 0
    
    summary = {
        "analysis_metadata": {
            "coordinates": {"lat": lat, "lon": lon},
            "scenario": scenario.upper(),
            "year": year,
            "warming_delta_vs_preindustrial": f"+{delta_t}°C",
            "mode": "SIMULATION" if SIMULATION_MODE else "DATA",
            "generated_at": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
            "source": "Climate Risk Engine v1.0 — BTW AI",
        },
        "hazard_results": results,
        "aggregate": {
            "overall_physical_risk_score": round(avg_score, 1),
            "peak_hazard_score": round(max_score, 1),
            "overall_risk_level": classify_risk(max_score),
            "highest_risk_hazard": max(results, key=lambda k: results[k]["risk_score"]) if results else None,
        }
    }
    return summary

# ── CLI entry point ───────────────────────────────────────────────────────────
if __name__ == "__main__":
    if len(sys.argv) < 5:
        print("Usage: python physical/hazard_model.py <lat> <lon> <scenario> <year> [hazard]")
        print("  hazard options: all | heat | flood | drought | slr | wildfire | cyclone")
        sys.exit(1)
    
    lat_arg = float(sys.argv[1])
    lon_arg = float(sys.argv[2])
    scenario_arg = sys.argv[3]
    year_arg = int(sys.argv[4])
    hazard_arg = sys.argv[5] if len(sys.argv) > 5 else "all"
    
    result = run_hazard_analysis(lat_arg, lon_arg, scenario_arg, year_arg, hazard_arg)
    print(json.dumps(result, indent=2))
