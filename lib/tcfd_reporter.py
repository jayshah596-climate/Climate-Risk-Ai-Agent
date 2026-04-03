"""
scripts/tcfd_reporter.py
=========================
Combines Physical + Transition risk outputs into a structured TCFD / ISSB S2 report.

Usage:
  python scripts/tcfd_reporter.py \
    --physical physical_output.json \
    --transition transition_output.json \
    --entity "Acme Manufacturing Ltd" \
    --year 2030 \
    --output report_output.json

Or import as a module:
  from scripts.tcfd_reporter import build_tcfd_report
"""

import json
import sys
import argparse
from datetime import datetime

# ── TCFD / ISSB S2 framework structure ───────────────────────────────────────
TCFD_SECTIONS = ["Governance", "Strategy", "Risk Management", "Metrics and Targets"]
NGFS_TO_IPCC_ALIGNMENT = {
    "Net Zero 2050":        "SSP1-2.6 / 1.5°C pathway",
    "Below 2C":             "SSP1-2.6 / 2°C pathway",
    "Delayed Transition":   "SSP2-4.5 transitional",
    "Divergent Net Zero":   "SSP2-4.5 / high variance",
    "NDCs":                 "SSP3-7.0 / ~2.5°C",
    "Current Policies":     "SSP5-8.5 / 3°C+",
}

def build_tcfd_report(
    entity_name: str,
    physical_data: dict,
    transition_data: dict,
    year: int = 2030,
) -> dict:
    """Build a TCFD/ISSB S2-aligned climate risk disclosure report."""
    
    # ── Extract physical risk summary ────────────────────────────────────────
    phys_meta = physical_data.get("analysis_metadata", {})
    phys_agg = physical_data.get("aggregate", {})
    phys_hazards = physical_data.get("hazard_results", {})
    
    top_hazard = phys_agg.get("highest_risk_hazard", "N/A")
    phys_score = phys_agg.get("overall_physical_risk_score", 0)
    phys_scenario = phys_meta.get("scenario", "Unknown")
    
    # ── Extract transition risk summary ─────────────────────────────────────
    tr_meta = transition_data.get("analysis_metadata", {})
    tr_summary = transition_data.get("risk_summary", {})
    tr_horizons = transition_data.get("carbon_stress_results", {})
    
    tr_scenario = tr_meta.get("scenario", "Unknown")
    policy_score = tr_summary.get("policy_risk_score_1_5", "N/A")
    first_stranded = tr_summary.get("first_stranded_asset_year", None)
    
    year_str = str(year)
    year_data = tr_horizons.get(year, tr_horizons.get(list(tr_horizons.keys())[0], {})) if tr_horizons else {}
    
    # ── Climate VaR ─────────────────────────────────────────────────────────
    asset_value = tr_meta.get("total_asset_value_usd", 1)
    carbon_liability = year_data.get("sector_adjusted_liability_usd", 0)
    physical_damage_est = phys_score * 0.03 * asset_value   # ~3% per risk unit proxy
    climate_var_pct = max(
        (carbon_liability / asset_value) * 100,
        (physical_damage_est / asset_value) * 100
    )
    
    report = {
        "report_metadata": {
            "entity": entity_name,
            "report_type": "TCFD / ISSB S2 Climate Risk Disclosure",
            "reference_year": year,
            "physical_scenario": phys_scenario,
            "transition_scenario": tr_scenario,
            "ipcc_alignment": NGFS_TO_IPCC_ALIGNMENT.get(tr_scenario, tr_scenario),
            "generated_at": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
            "standard_reference": "TCFD 2017, ISSB IFRS S2 (2023), EU Taxonomy Delegated Act",
        },

        "A_governance": {
            "tcfd_pillar": "Governance",
            "disclosure_text": (
                f"{entity_name} has assessed climate-related risks and opportunities across "
                f"physical and transition dimensions in line with TCFD recommendations and ISSB IFRS S2. "
                f"Board-level oversight is recommended for risks flagged as HIGH or above."
            ),
            "action_items": [
                "Assign board-level climate risk owner",
                "Integrate climate KPIs into executive remuneration",
                "Annual climate risk review cycle",
            ],
        },

        "B_strategy": {
            "tcfd_pillar": "Strategy",
            "time_horizons": {
                "short_term": "0–3 years (to 2027)",
                "medium_term": "3–10 years (to 2035)",
                "long_term": "10–30 years (to 2055)",
            },
            "scenario_analysis": {
                "physical_scenario_used": phys_scenario,
                "transition_scenario_used": tr_scenario,
                "orderly_scenario": "Net Zero 2050 — moderate transition cost, controlled physical risk",
                "disorderly_scenario": "Delayed Transition — abrupt carbon price shock post-2030",
                "hot_house_scenario": "Current Policies — low transition risk but severe physical damage",
            },
            "key_physical_risks": [
                {
                    "hazard": k,
                    "risk_level": v.get("risk_level"),
                    "impact": v.get("key_impacts", [])[:2],
                }
                for k, v in phys_hazards.items()
                if v.get("risk_score", 0) >= 2.5
            ],
            "key_transition_risks": {
                "carbon_liability_at_horizon": f"${carbon_liability:,.0f}",
                "liability_pct_of_asset": f"{year_data.get('liability_as_pct_of_asset_value', 0):.1f}%",
                "stranded_asset_year": first_stranded or "Not flagged within 2050 horizon",
            },
        },

        "C_risk_management": {
            "tcfd_pillar": "Risk Management",
            "overall_physical_risk_score": f"{phys_score:.1f} / 5.0",
            "overall_transition_policy_score": f"{policy_score} / 5",
            "top_physical_hazard": top_hazard,
            "risk_integration_recommendation": (
                "Integrate climate risk into enterprise risk management (ERM) framework. "
                "Physical risks feed into operational continuity planning; "
                "transition risks feed into capital allocation and asset lifecycle reviews."
            ),
            "adaptation_priorities": [
                v.get("adaptation", [])[:1][0]
                for k, v in phys_hazards.items()
                if v.get("risk_score", 0) >= 3.0 and v.get("adaptation")
            ],
        },

        "D_metrics_and_targets": {
            "tcfd_pillar": "Metrics and Targets",
            "scope1_tco2e": tr_meta.get("scope1_tco2e", "N/A"),
            "scope2_tco2e": tr_meta.get("scope2_tco2e", "N/A"),
            "scope3_tco2e": tr_meta.get("scope3_tco2e", 0),
            "carbon_price_assumed_2030": f"${year_data.get('carbon_price_usd_per_tco2', 'N/A')}/tCO2",
            "climate_var_pct": f"{climate_var_pct:.1f}%",
            "climate_var_description": "Climate Value-at-Risk: max(Physical damage, Carbon liability) / Asset Value",
            "recommended_targets": [
                "Set SBTi-aligned Scope 1+2 reduction target (near-term: 2030, long-term: 2050)",
                "Achieve net-zero Scope 1+2 by 2050 at latest",
                "Annual 4.2% emissions reduction (Science-Based Target 1.5°C trajectory)",
                "Climate CAPEX allocation: ≥15% of total CAPEX toward low-carbon transition",
            ],
        },

        "E_summary_heatmap": {
            "description": "Risk matrix: rows = time horizon, columns = risk type",
            "matrix": {
                "2025–2030": {
                    "Physical Risk": "LOW–MEDIUM" if phys_score < 2.5 else "MEDIUM–HIGH",
                    "Transition Risk": "HIGH" if tr_scenario in ["Net Zero 2050", "Delayed Transition"] else "LOW",
                },
                "2030–2050": {
                    "Physical Risk": "MEDIUM" if phys_score < 3 else "HIGH",
                    "Transition Risk": "HIGH" if policy_score >= 4 else "MEDIUM",
                },
                "Post-2050": {
                    "Physical Risk": "HIGH–CRITICAL" if phys_scenario in ["ssp585", "ssp370"] else "MEDIUM",
                    "Transition Risk": "LOW (stabilised)" if tr_scenario == "Net Zero 2050" else "MEDIUM",
                },
            },
        },
    }
    return report

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--physical", required=True)
    parser.add_argument("--transition", required=True)
    parser.add_argument("--entity", default="Entity Name")
    parser.add_argument("--year", type=int, default=2030)
    parser.add_argument("--output", default=None)
    args = parser.parse_args()
    
    with open(args.physical) as f:
        phys = json.load(f)
    with open(args.transition) as f:
        trans = json.load(f)
    
    report = build_tcfd_report(args.entity, phys, trans, args.year)
    
    output_str = json.dumps(report, indent=2)
    if args.output:
        with open(args.output, "w") as f:
            f.write(output_str)
        print(f"Report saved to {args.output}")
    else:
        print(output_str)
