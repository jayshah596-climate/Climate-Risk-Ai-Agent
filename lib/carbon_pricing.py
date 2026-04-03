"""
transition/carbon_pricing.py
=============================
Calculates Earnings at Risk (EaR), Carbon Liability, and Stranded Asset probability
using NGFS Phase 5 scenario carbon price pathways.

Usage:
  python transition/carbon_pricing.py <scope1> <scope2> <scenario> <sector> <asset_value>

  scope1       : Scope 1 emissions in tCO2e/year
  scope2       : Scope 2 emissions in tCO2e/year
  scenario     : "Net Zero 2050" | "Below 2C" | "Delayed Transition" | 
                 "Divergent Net Zero" | "NDCs" | "Current Policies"
  sector       : energy | utilities | transport | real_estate | agriculture | 
                 manufacturing | finance | general
  asset_value  : total asset value or annual revenue in USD

Example:
  python transition/carbon_pricing.py 50000 20000 "Delayed Transition" manufacturing 5000000

Data source:
  NGFS Phase 5 Scenarios (2023) — IIASA Scenario Explorer
  https://data.ene.iiasa.ac.at/ngfs/
  Carbon prices below are NGFS median illustrative values (USD/tCO2).
"""

import sys
import json
from datetime import datetime

# ── NGFS Phase 5 Carbon Price Pathways (USD/tCO2, global median) ─────────────
# Source: NGFS Scenarios for Central Banks and Supervisors, Phase 5 (2023)
# Values rounded to nearest $5 for clarity. 
# Category: Orderly | Disorderly | Hot House World
NGFS_CARBON_PRICES = {
    # ORDERLY — smooth, credible early policy action
    "Net Zero 2050": {
        "category": "Orderly",
        "description": "Immediate and credible global climate action. Limits warming to 1.5°C.",
        2025: 50,  2030: 160, 2035: 270, 2040: 420, 2045: 570, 2050: 700,
    },
    "Below 2C": {
        "category": "Orderly",
        "description": "Strong climate policies with higher mitigation costs than NZ2050.",
        2025: 40,  2030: 120, 2035: 200, 2040: 310, 2045: 430, 2050: 540,
    },
    # DISORDERLY — late or uncoordinated action → abrupt policy shifts
    "Delayed Transition": {
        "category": "Disorderly",
        "description": "Policies delayed until 2030, then sudden steep carbon price ramp.",
        2025: 20,  2030: 45,  2035: 250, 2040: 500, 2045: 700, 2050: 850,
    },
    "Divergent Net Zero": {
        "category": "Disorderly",
        "description": "Uneven global policies. Some sectors face extreme costs.",
        2025: 30,  2030: 100, 2035: 220, 2040: 380, 2045: 520, 2050: 660,
    },
    # HOT HOUSE WORLD — insufficient action, high physical risk
    "NDCs": {
        "category": "Hot House World",
        "description": "Only current pledges implemented. ~2.5°C warming.",
        2025: 15,  2030: 30,  2035: 50,  2040: 75,  2045: 100, 2050: 130,
    },
    "Current Policies": {
        "category": "Hot House World",
        "description": "No new policies. ~3°C+ warming. Low transition risk, HIGH physical risk.",
        2025: 10,  2030: 20,  2035: 30,  2040: 45,  2045: 60,  2050: 75,
    },
}

# ── Sector carbon intensity multipliers ──────────────────────────────────────
# Reflects how much of operating costs are exposed to carbon pricing
SECTOR_EXPOSURE = {
    "energy":         {"intensity_factor": 2.5, "stranded_threshold_pct": 15},
    "utilities":      {"intensity_factor": 2.0, "stranded_threshold_pct": 18},
    "transport":      {"intensity_factor": 1.8, "stranded_threshold_pct": 15},
    "real_estate":    {"intensity_factor": 0.8, "stranded_threshold_pct": 10},
    "agriculture":    {"intensity_factor": 1.5, "stranded_threshold_pct": 12},
    "manufacturing":  {"intensity_factor": 1.6, "stranded_threshold_pct": 15},
    "finance":        {"intensity_factor": 0.3, "stranded_threshold_pct": 5},
    "general":        {"intensity_factor": 1.0, "stranded_threshold_pct": 20},
}

# ── Policy risk multipliers by scenario ──────────────────────────────────────
POLICY_RISK_SCORE = {
    "Net Zero 2050":       5,  # High transition risk, low physical risk
    "Below 2C":            4,
    "Delayed Transition":  5,  # Highest combined risk (sudden policy + residual physical)
    "Divergent Net Zero":  4,
    "NDCs":                2,
    "Current Policies":    1,  # Low transition risk, VERY HIGH physical risk
}

def calculate_carbon_liability(scope1: float, scope2: float, scenario: str, year: int) -> float:
    """Carbon liability = (Scope1 + Scope2) × carbon_price at that year."""
    prices = NGFS_CARBON_PRICES.get(scenario, NGFS_CARBON_PRICES["Current Policies"])
    # Linear interpolation between benchmark years
    years = sorted([y for y in prices if isinstance(y, int)])
    if year <= years[0]:  price = prices[years[0]]
    elif year >= years[-1]: price = prices[years[-1]]
    else:
        for i in range(len(years) - 1):
            if years[i] <= year <= years[i+1]:
                t = (year - years[i]) / (years[i+1] - years[i])
                price = prices[years[i]] + t * (prices[years[i+1]] - prices[years[i]])
                break
    return (scope1 + scope2) * price, price

def stress_test_transition(
    scope1: float,
    scope2: float,
    scenario: str = "Net Zero 2050",
    sector: str = "general",
    asset_value: float = 1_000_000,
    scope3: float = 0.0,
) -> dict:
    """
    Full NGFS transition stress test across multiple time horizons.
    Returns structured JSON with EaR, carbon liability, stranded asset flag.
    """
    scenario_data = NGFS_CARBON_PRICES.get(scenario, NGFS_CARBON_PRICES["Current Policies"])
    sector_data = SECTOR_EXPOSURE.get(sector, SECTOR_EXPOSURE["general"])
    intensity = sector_data["intensity_factor"]
    stranded_pct_threshold = sector_data["stranded_threshold_pct"] / 100
    
    horizons = {}
    for year in [2025, 2030, 2035, 2040, 2050]:
        liability, price = calculate_carbon_liability(scope1, scope2, scenario, year)
        adjusted_liability = liability * intensity
        pct_of_asset = (adjusted_liability / asset_value) * 100
        stranded = pct_of_asset > (stranded_pct_threshold * 100)
        
        horizons[year] = {
            "carbon_price_usd_per_tco2": round(price, 0),
            "raw_carbon_liability_usd": round(liability, 0),
            "sector_adjusted_liability_usd": round(adjusted_liability, 0),
            "liability_as_pct_of_asset_value": round(pct_of_asset, 1),
            "stranded_asset_flag": stranded,
            "earnings_at_risk_note": f"~{round(pct_of_asset * 0.4, 1)}% of EBITDA (illustrative, assuming 40% pass-through)",
        }
    
    # Scope 3 supplementary (informational only)
    scope3_note = None
    if scope3 > 0:
        s3_price_2030 = scenario_data.get(2030, 100)
        scope3_note = {
            "scope3_liability_2030_usd": round(scope3 * s3_price_2030, 0),
            "note": "Scope 3 included for disclosure awareness. Not used in EaR calculation.",
        }
    
    return {
        "analysis_metadata": {
            "scenario": scenario,
            "category": scenario_data["category"],
            "scenario_description": scenario_data["description"],
            "sector": sector,
            "scope1_tco2e": scope1,
            "scope2_tco2e": scope2,
            "scope3_tco2e": scope3,
            "total_asset_value_usd": asset_value,
            "generated_at": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
            "data_source": "NGFS Phase 5 Scenarios (2023) — IIASA/NGFS",
        },
        "carbon_stress_results": horizons,
        "scope3_supplementary": scope3_note,
        "risk_summary": {
            "policy_risk_score_1_5": POLICY_RISK_SCORE.get(scenario, 3),
            "first_stranded_asset_year": next(
                (yr for yr, v in horizons.items() if v["stranded_asset_flag"]), None
            ),
            "recommendation": _get_recommendation(scenario, horizons, scope1 + scope2),
        },
    }

def _get_recommendation(scenario: str, horizons: dict, total_emissions: float) -> str:
    first_stranded = next((yr for yr, v in horizons.items() if v["stranded_asset_flag"]), None)
    if first_stranded:
        return (
            f"⚠️ STRANDED ASSET RISK detected by {first_stranded} under '{scenario}'. "
            f"Consider immediate decarbonisation roadmap, asset divestment review, or green refinancing."
        )
    elif total_emissions > 100_000:
        return (
            f"Carbon liability is significant. Develop a Science-Based Target (SBTi) "
            f"aligned reduction plan. Monitor EU ETS / carbon border adjustments."
        )
    else:
        return (
            f"Carbon liability appears manageable under '{scenario}'. "
            f"Recommend annual review and Scope 3 screening."
        )

def compare_scenarios(scope1: float, scope2: float, sector: str, asset_value: float, year: int = 2030) -> dict:
    """Quick multi-scenario comparison at a single horizon year."""
    scenarios_to_compare = ["Net Zero 2050", "Delayed Transition", "Current Policies"]
    comparison = {}
    for sc in scenarios_to_compare:
        liability, price = calculate_carbon_liability(scope1, scope2, sc, year)
        sector_data = SECTOR_EXPOSURE.get(sector, SECTOR_EXPOSURE["general"])
        adj = liability * sector_data["intensity_factor"]
        comparison[sc] = {
            "carbon_price": f"${price:.0f}/tCO2",
            "carbon_liability_usd": round(adj, 0),
            "pct_of_asset": round((adj / asset_value) * 100, 1),
            "category": NGFS_CARBON_PRICES[sc]["category"],
        }
    return {"year": year, "scenario_comparison": comparison}

if __name__ == "__main__":
    if len(sys.argv) < 6:
        print("Usage: python transition/carbon_pricing.py <scope1> <scope2> <scenario> <sector> <asset_value> [scope3]")
        print('Example: python transition/carbon_pricing.py 50000 20000 "Net Zero 2050" manufacturing 5000000')
        sys.exit(1)
    
    s1 = float(sys.argv[1])
    s2 = float(sys.argv[2])
    sc = sys.argv[3]
    sect = sys.argv[4]
    av = float(sys.argv[5])
    s3 = float(sys.argv[6]) if len(sys.argv) > 6 else 0.0
    
    print("=== TRANSITION RISK STRESS TEST ===")
    result = stress_test_transition(s1, s2, sc, sect, av, s3)
    print(json.dumps(result, indent=2))
    
    print("\n=== MULTI-SCENARIO COMPARISON (2030) ===")
    comparison = compare_scenarios(s1, s2, sect, av, 2030)
    print(json.dumps(comparison, indent=2))
