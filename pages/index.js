import Head from 'next/head';
import { useState, useCallback } from 'react';
import dynamic from 'next/dynamic';

// Plotly must be client-side only (uses browser APIs)
const Plot = dynamic(() => import('react-plotly.js'), { ssr: false });

// ── Constants ────────────────────────────────────────────────────────────────

const RISK_COLOR = {
  CRITICAL: '#dc2626',
  HIGH: '#ea580c',
  MEDIUM: '#d97706',
  LOW: '#16a34a',
  NEGLIGIBLE: '#64748b',
};

const SCENARIOS_PHYSICAL = [
  { value: 'ssp585', label: 'SSP5-8.5 — Very high emissions (4–5°C)' },
  { value: 'ssp370', label: 'SSP3-7.0 — High emissions (3–4°C)' },
  { value: 'ssp245', label: 'SSP2-4.5 — Intermediate (2–3°C)' },
  { value: 'ssp126', label: 'SSP1-2.6 — Paris aligned (1.5–2°C)' },
];

const SCENARIOS_NGFS = [
  'Net Zero 2050',
  'Below 2C',
  'Delayed Transition',
  'Divergent Net Zero',
  'NDCs',
  'Current Policies',
];

const SECTORS = [
  'general', 'energy', 'utilities', 'transport',
  'real_estate', 'agriculture', 'manufacturing', 'finance',
];

const HAZARD_OPTIONS = ['heat', 'flood', 'drought', 'slr', 'wildfire', 'cyclone'];

const ASSET_TYPES = [
  'coal_plant', 'gas_plant', 'oil_field', 'coal_mine',
  'petrol_station', 'ICE_fleet', 'gas_boiler',
  'high_carbon_building', 'conventional_farm',
];

// ── Helper components ─────────────────────────────────────────────────────────

function RiskBadge({ level }) {
  const base = level?.split(' ')[0] || 'NEGLIGIBLE';
  return <span className={`risk-badge risk-${base}`}>{level}</span>;
}

function MetricCard({ label, value, delta, accentColor }) {
  return (
    <div className="metric-card" style={accentColor ? { borderLeftColor: accentColor } : {}}>
      <div className="m-label">{label}</div>
      <div className="m-value">{value ?? '—'}</div>
      {delta && <div className="m-delta">{delta}</div>}
    </div>
  );
}

function Spinner() {
  return <span className="spinner" />;
}

function Alert({ type = 'info', children }) {
  return <div className={`alert alert-${type}`}>{children}</div>;
}

// ── API helper ────────────────────────────────────────────────────────────────

async function callApi(endpoint, body) {
  const res = await fetch(`/api/${endpoint}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.error || `API error ${res.status}`);
  return data;
}

// ── Physical Risk Section ─────────────────────────────────────────────────────

function PhysicalRiskSection({ onResult }) {
  const [form, setForm] = useState({
    location: '',
    scenario: 'ssp585',
    year: 2050,
    hazards: ['heat', 'flood', 'drought'],
  });
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const [expanded, setExpanded] = useState({});

  const toggleHazard = (h) =>
    setForm((f) => ({
      ...f,
      hazards: f.hazards.includes(h) ? f.hazards.filter((x) => x !== h) : [...f.hazards, h],
    }));

  const toggleExpand = (key) => setExpanded((e) => ({ ...e, [key]: !e[key] }));

  const run = async () => {
    if (!form.location.trim()) return;
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const data = await callApi('physical', {
        location: form.location,
        scenario: form.scenario,
        year: form.year,
        hazards: form.hazards.length ? form.hazards.join(',') : 'all',
      });
      setResult(data);
      onResult?.(data);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  const hazardResults = result?.hazard_results || {};
  const agg = result?.aggregate || {};
  const locInfo = result?.location_info || {};

  // Chart data
  const chartData = Object.entries(hazardResults).map(([k, v]) => ({
    name: k.charAt(0).toUpperCase() + k.slice(1),
    score: v.risk_score,
    level: v.risk_level?.split(' ')[0],
  }));

  return (
    <div>
      <div className="page-header">
        <h1>Physical Climate Risk Assessment</h1>
        <p>Quantify hazard exposure under IPCC SSP scenarios — Heat, Flood, Drought, SLR, Wildfire, Cyclone</p>
      </div>

      {/* Input form */}
      <div className="card">
        <div className="card-title">Analysis Inputs</div>
        <div className="form-grid">
          <div className="form-group" style={{ gridColumn: '1 / -1' }}>
            <label>Asset Location</label>
            <input
              type="text"
              placeholder="e.g. Vadodara, India  or  22.3,73.2"
              value={form.location}
              onChange={(e) => setForm({ ...form, location: e.target.value })}
              onKeyDown={(e) => e.key === 'Enter' && run()}
            />
          </div>
          <div className="form-group">
            <label>IPCC Scenario (SSP)</label>
            <select value={form.scenario} onChange={(e) => setForm({ ...form, scenario: e.target.value })}>
              {SCENARIOS_PHYSICAL.map((s) => (
                <option key={s.value} value={s.value}>{s.label}</option>
              ))}
            </select>
          </div>
          <div className="form-group">
            <label>Time Horizon</label>
            <select value={form.year} onChange={(e) => setForm({ ...form, year: Number(e.target.value) })}>
              {[2030, 2050, 2080].map((y) => <option key={y}>{y}</option>)}
            </select>
          </div>
          <div className="form-group" style={{ gridColumn: '1 / -1' }}>
            <label>Hazards to Assess</label>
            <div className="checkbox-group">
              {HAZARD_OPTIONS.map((h) => (
                <div
                  key={h}
                  className={`checkbox-pill ${form.hazards.includes(h) ? 'checked' : ''}`}
                  onClick={() => toggleHazard(h)}
                >
                  {h.toUpperCase()}
                </div>
              ))}
            </div>
          </div>
        </div>
        <div style={{ marginTop: 16 }}>
          <button className="btn-primary" onClick={run} disabled={loading || !form.location.trim()}>
            {loading ? <><Spinner /> Running Analysis…</> : '▶ Run Physical Risk Analysis'}
          </button>
        </div>
      </div>

      {error && <Alert type="error">{error}</Alert>}

      {/* Results */}
      {result && (
        <>
          {/* Location */}
          <Alert type="info">
            📍 <strong>{locInfo.display_name}</strong> &nbsp;|&nbsp;
            Lat: {locInfo.lat?.toFixed(3)}, Lon: {locInfo.lon?.toFixed(3)}
            {locInfo.elevation_m != null && (
              <> &nbsp;|&nbsp; Elevation: {locInfo.elevation_m}m
                {locInfo.coastal_risk_flag && ' ⚠️ Low-elevation coastal zone'}
              </>
            )}
          </Alert>

          {/* Metric cards */}
          <div className="metrics-row">
            <MetricCard
              label="Overall Physical Risk"
              value={agg.overall_risk_level}
              delta={`Score: ${agg.overall_physical_risk_score}/5`}
              accentColor={RISK_COLOR[agg.overall_risk_level]}
            />
            <MetricCard
              label="Peak Hazard"
              value={agg.highest_risk_hazard?.toUpperCase()}
              delta={`Score: ${agg.peak_hazard_score}/5`}
              accentColor={RISK_COLOR[agg.overall_risk_level]}
            />
            <MetricCard
              label="Warming vs Pre-industrial"
              value={result.analysis_metadata?.warming_delta_vs_preindustrial}
              delta={`Scenario: ${form.scenario.toUpperCase()}, Year: ${form.year}`}
            />
          </div>

          {/* Bar chart */}
          {chartData.length > 0 && (
            <div className="card">
              <div className="card-title">Hazard Exposure Scores (1 = Negligible → 5 = Critical)</div>
              <Plot
                data={[{
                  type: 'bar',
                  x: chartData.map((d) => d.score),
                  y: chartData.map((d) => d.name),
                  orientation: 'h',
                  marker: {
                    color: chartData.map((d) => RISK_COLOR[d.level] || '#64748b'),
                  },
                  text: chartData.map((d) => d.level),
                  textposition: 'outside',
                  hovertemplate: '<b>%{y}</b><br>Score: %{x}<extra></extra>',
                }]}
                layout={{
                  margin: { l: 80, r: 60, t: 10, b: 30 },
                  xaxis: { range: [0, 5.5], title: 'Risk Score' },
                  yaxis: { automargin: true },
                  height: 280,
                  paper_bgcolor: 'transparent',
                  plot_bgcolor: 'transparent',
                  font: { size: 12 },
                  shapes: [
                    { type: 'line', x0: 2.5, x1: 2.5, y0: -0.5, y1: chartData.length - 0.5,
                      line: { color: '#d97706', dash: 'dot', width: 1.5 } },
                  ],
                }}
                config={{ displayModeBar: false, responsive: true }}
                style={{ width: '100%' }}
              />
            </div>
          )}

          {/* Hazard detail cards */}
          <div className="card">
            <div className="card-title">Hazard Detail</div>
            {Object.entries(hazardResults).map(([key, hdata]) => {
              const lvl = hdata.risk_level?.split(' ')[0] || 'LOW';
              const isOpen = expanded[key] ?? (lvl === 'CRITICAL' || lvl === 'HIGH');
              return (
                <div key={key} className="hazard-card">
                  <div className="hazard-card-header" onClick={() => toggleExpand(key)}>
                    <h4>{key.toUpperCase()} — {hdata.hazard}</h4>
                    <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
                      <RiskBadge level={hdata.risk_level} />
                      <span style={{ color: '#94a3b8', fontSize: 14 }}>{isOpen ? '▲' : '▼'}</span>
                    </div>
                  </div>
                  {isOpen && (
                    <div className="hazard-card-body">
                      <div className="hazard-mini-metrics">
                        <div className="hazard-mini-metric">
                          Baseline<span>{hdata.baseline_value}</span>
                        </div>
                        <div className="hazard-mini-metric">
                          Projected {form.year}<span>{hdata.projected_value}</span>
                        </div>
                        <div className="hazard-mini-metric">
                          Change<span>{hdata.change}</span>
                        </div>
                      </div>
                      <div className="hazard-detail-row">
                        <strong>Financial Proxy:</strong> {hdata.financial_proxy}
                      </div>
                      <div className="hazard-detail-row">
                        <strong>Key Impacts:</strong> {hdata.key_impacts?.join(' | ')}
                      </div>
                      <div className="hazard-detail-row">
                        <strong>Adaptation Options:</strong> {hdata.adaptation?.join(' · ')}
                      </div>
                      <div className="caption">Source: {hdata.data_source}</div>
                    </div>
                  )}
                </div>
              );
            })}
          </div>

          <div className="caption" style={{ textAlign: 'right' }}>
            Mode: {result.analysis_metadata?.mode} | Generated: {result.analysis_metadata?.generated_at}
          </div>
        </>
      )}
    </div>
  );
}

// ── Transition Risk Section ───────────────────────────────────────────────────

function TransitionRiskSection({ onResult }) {
  const [form, setForm] = useState({
    scope1: 50000,
    scope2: 20000,
    scope3: 0,
    assetValue: 5000000,
    sector: 'general',
    scenario: 'Net Zero 2050',
  });
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);

  const set = (k, v) => setForm((f) => ({ ...f, [k]: v }));

  const run = async () => {
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const data = await callApi('transition', form);
      setResult(data);
      onResult?.(data);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  const horizons = result?.carbon_stress_results || {};
  const summary = result?.risk_summary || {};
  const meta = result?.analysis_metadata || {};
  const comp = result?.scenario_comparison?.scenario_comparison || {};

  // Chart data
  const years = Object.keys(horizons).map(Number);
  const liabilities = years.map((y) => horizons[y]?.sector_adjusted_liability_usd || 0);
  const prices = years.map((y) => horizons[y]?.carbon_price_usd_per_tco2 || 0);

  return (
    <div>
      <div className="page-header">
        <h1>Transition Risk &amp; Carbon Stress Test</h1>
        <p>NGFS Phase 5 Scenarios — carbon pricing, earnings at risk, stranded asset flags</p>
      </div>

      <div className="card">
        <div className="card-title">Analysis Inputs</div>
        <div className="form-grid">
          <div className="form-group">
            <label>Scope 1 Emissions (tCO2e/yr)</label>
            <input type="number" min={0} step={1000} value={form.scope1}
              onChange={(e) => set('scope1', Number(e.target.value))} />
          </div>
          <div className="form-group">
            <label>Scope 2 Emissions (tCO2e/yr)</label>
            <input type="number" min={0} step={1000} value={form.scope2}
              onChange={(e) => set('scope2', Number(e.target.value))} />
          </div>
          <div className="form-group">
            <label>Scope 3 — optional (tCO2e/yr)</label>
            <input type="number" min={0} step={5000} value={form.scope3}
              onChange={(e) => set('scope3', Number(e.target.value))} />
          </div>
          <div className="form-group">
            <label>Asset Value / Revenue (USD)</label>
            <input type="number" min={0} step={100000} value={form.assetValue}
              onChange={(e) => set('assetValue', Number(e.target.value))} />
          </div>
          <div className="form-group">
            <label>Sector</label>
            <select value={form.sector} onChange={(e) => set('sector', e.target.value)}>
              {SECTORS.map((s) => <option key={s}>{s}</option>)}
            </select>
          </div>
          <div className="form-group">
            <label>NGFS Scenario</label>
            <select value={form.scenario} onChange={(e) => set('scenario', e.target.value)}>
              {SCENARIOS_NGFS.map((s) => <option key={s}>{s}</option>)}
            </select>
          </div>
        </div>
        <div style={{ marginTop: 16 }}>
          <button className="btn-primary" onClick={run} disabled={loading}>
            {loading ? <><Spinner /> Running Stress Test…</> : '▶ Run Transition Risk Analysis'}
          </button>
        </div>
      </div>

      {error && <Alert type="error">{error}</Alert>}

      {result && (
        <>
          <div className="metrics-row">
            <MetricCard label="Policy Risk Score" value={`${summary.policy_risk_score_1_5} / 5`}
              delta={meta.category} />
            <MetricCard label="First Stranded Asset Year"
              value={summary.first_stranded_asset_year || 'None by 2050'}
              delta={summary.first_stranded_asset_year ? '⚠️ Stranding flagged' : 'No stranding detected'}
              accentColor={summary.first_stranded_asset_year ? '#dc2626' : '#16a34a'}
            />
            <MetricCard label="Scenario Category" value={meta.category}
              delta={`${meta.scope1_tco2e?.toLocaleString()} + ${meta.scope2_tco2e?.toLocaleString()} tCO2e`}
            />
          </div>

          {summary.recommendation && (
            <Alert type={summary.first_stranded_asset_year ? 'warning' : 'info'}>
              {summary.recommendation}
            </Alert>
          )}

          {/* Carbon liability chart */}
          {years.length > 0 && (
            <div className="card">
              <div className="card-title">Carbon Liability Pathway — {form.scenario}</div>
              <Plot
                data={[
                  {
                    type: 'bar',
                    x: years,
                    y: liabilities,
                    name: 'Carbon Liability (USD)',
                    marker: { color: '#ea580c' },
                    yaxis: 'y',
                    hovertemplate: 'Year %{x}<br>$%{y:,.0f}<extra></extra>',
                  },
                  {
                    type: 'scatter',
                    x: years,
                    y: prices,
                    name: 'Carbon Price ($/tCO2)',
                    yaxis: 'y2',
                    line: { color: '#0ea5e9', width: 2.5 },
                    mode: 'lines+markers',
                    hovertemplate: 'Year %{x}<br>$%{y:.0f}/tCO2<extra></extra>',
                  },
                ]}
                layout={{
                  margin: { l: 70, r: 70, t: 10, b: 40 },
                  yaxis: { title: 'Carbon Liability (USD)', titlefont: { size: 11 } },
                  yaxis2: { title: 'Carbon Price (USD/tCO2)', overlaying: 'y', side: 'right', titlefont: { size: 11 } },
                  legend: { x: 0.01, y: 0.99, font: { size: 11 } },
                  height: 300,
                  paper_bgcolor: 'transparent',
                  plot_bgcolor: 'transparent',
                  barmode: 'group',
                }}
                config={{ displayModeBar: false, responsive: true }}
                style={{ width: '100%' }}
              />
            </div>
          )}

          {/* Year-by-year table */}
          <div className="card">
            <div className="card-title">Carbon Stress Results by Year</div>
            <table className="data-table">
              <thead>
                <tr>
                  <th>Year</th>
                  <th>Carbon Price</th>
                  <th>Liability (USD)</th>
                  <th>% of Asset Value</th>
                  <th>Stranded?</th>
                  <th>EaR Note</th>
                </tr>
              </thead>
              <tbody>
                {years.map((y) => {
                  const row = horizons[y];
                  return (
                    <tr key={y}>
                      <td><strong>{y}</strong></td>
                      <td>${row.carbon_price_usd_per_tco2?.toLocaleString()}/tCO2</td>
                      <td>${row.sector_adjusted_liability_usd?.toLocaleString()}</td>
                      <td>{row.liability_as_pct_of_asset_value}%</td>
                      <td>
                        {row.stranded_asset_flag
                          ? <span style={{ color: '#dc2626', fontWeight: 700 }}>⚠ YES</span>
                          : <span style={{ color: '#16a34a' }}>No</span>}
                      </td>
                      <td style={{ fontSize: 11, color: '#64748b' }}>{row.earnings_at_risk_note}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>

          {/* Multi-scenario comparison */}
          {Object.keys(comp).length > 0 && (
            <div className="card">
              <div className="card-title">Scenario Comparison at 2030</div>
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Scenario</th>
                    <th>Carbon Price</th>
                    <th>Carbon Liability</th>
                    <th>% of Asset</th>
                    <th>Category</th>
                  </tr>
                </thead>
                <tbody>
                  {Object.entries(comp).map(([sc, v]) => (
                    <tr key={sc}>
                      <td><strong>{sc}</strong></td>
                      <td>{v.carbon_price}</td>
                      <td>${v.carbon_liability_usd?.toLocaleString()}</td>
                      <td>{v.pct_of_asset}%</td>
                      <td>
                        <span style={{
                          fontSize: 11, fontWeight: 600,
                          color: v.category === 'Orderly' ? '#16a34a' : v.category === 'Hot House World' ? '#dc2626' : '#d97706',
                        }}>
                          {v.category}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </>
      )}
    </div>
  );
}

// ── Stranded Assets Section ───────────────────────────────────────────────────

function StrandedAssetsSection() {
  const [form, setForm] = useState({
    assetType: 'coal_plant',
    scenario: 'Net Zero 2050',
    year: 2035,
  });
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);

  const run = async () => {
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const data = await callApi('stranded', form);
      setResult(data);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  const prob = result?.stranding_probability_pct || 0;
  const probColor =
    prob >= 75 ? '#dc2626' :
    prob >= 50 ? '#ea580c' :
    prob >= 25 ? '#d97706' : '#16a34a';

  const pathway = result?.full_probability_pathway || {};
  const pathYears = Object.keys(pathway).map(Number);
  const pathProbs = pathYears.map((y) => pathway[y]);

  return (
    <div>
      <div className="page-header">
        <h1>Stranded Asset Risk Assessment</h1>
        <p>Probability of asset stranding by year under NGFS transition pathways</p>
      </div>

      <div className="card">
        <div className="card-title">Assessment Inputs</div>
        <div className="form-grid">
          <div className="form-group">
            <label>Asset Type</label>
            <select value={form.assetType} onChange={(e) => setForm({ ...form, assetType: e.target.value })}>
              {ASSET_TYPES.map((a) => (
                <option key={a} value={a}>{a.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase())}</option>
              ))}
            </select>
          </div>
          <div className="form-group">
            <label>NGFS Scenario</label>
            <select value={form.scenario} onChange={(e) => setForm({ ...form, scenario: e.target.value })}>
              {SCENARIOS_NGFS.map((s) => <option key={s}>{s}</option>)}
            </select>
          </div>
          <div className="form-group">
            <label>Assessment Year</label>
            <select value={form.year} onChange={(e) => setForm({ ...form, year: Number(e.target.value) })}>
              {[2030, 2035, 2040, 2050].map((y) => <option key={y}>{y}</option>)}
            </select>
          </div>
        </div>
        <div style={{ marginTop: 16 }}>
          <button className="btn-primary" onClick={run} disabled={loading}>
            {loading ? <><Spinner /> Assessing…</> : '▶ Assess Stranding Probability'}
          </button>
        </div>
      </div>

      {error && <Alert type="error">{error}</Alert>}

      {result && (
        <>
          {/* Probability display */}
          <div className="prob-display" style={{
            background: probColor + '14',
            border: `2px solid ${probColor}`,
          }}>
            <div className="prob-number" style={{ color: probColor }}>{prob}%</div>
            <div className="prob-label" style={{ color: probColor }}>
              Stranding Probability by {form.year}
            </div>
            <div style={{ marginTop: 8, fontSize: 13, color: '#475569' }}>{result.risk_band}</div>
          </div>

          {/* Pathway chart */}
          {pathYears.length > 0 && (
            <div className="card">
              <div className="card-title">
                Stranding Probability Pathway — {result.asset_type?.replace(/_/g, ' ')} | {form.scenario}
              </div>
              <Plot
                data={[{
                  type: 'scatter',
                  x: pathYears,
                  y: pathProbs,
                  mode: 'lines+markers',
                  line: { color: probColor, width: 3 },
                  marker: { size: 8 },
                  fill: 'tozeroy',
                  fillcolor: probColor + '1a',
                  hovertemplate: 'Year %{x}<br>Probability: %{y}%<extra></extra>',
                }]}
                layout={{
                  margin: { l: 55, r: 20, t: 10, b: 40 },
                  xaxis: { title: 'Year' },
                  yaxis: { title: 'Stranding Probability (%)', range: [0, 105] },
                  height: 280,
                  paper_bgcolor: 'transparent',
                  plot_bgcolor: 'transparent',
                  shapes: [
                    { type: 'line', x0: pathYears[0], x1: pathYears[pathYears.length - 1],
                      y0: 50, y1: 50, line: { color: '#94a3b8', dash: 'dash', width: 1.5 } },
                  ],
                  annotations: [
                    { x: pathYears[pathYears.length - 1], y: 51, xanchor: 'right',
                      text: '50% threshold', font: { size: 11, color: '#94a3b8' }, showarrow: false },
                  ],
                }}
                config={{ displayModeBar: false, responsive: true }}
                style={{ width: '100%' }}
              />
            </div>
          )}

          {/* Recommended actions */}
          <div className="card">
            <div className="card-title">Recommended Actions</div>
            {result.recommended_actions?.map((action, i) => (
              <div key={i} style={{
                display: 'flex', gap: 10, alignItems: 'flex-start',
                padding: '8px 0', borderBottom: '1px solid #f1f5f9', fontSize: 13,
              }}>
                <span style={{ color: '#16a34a', fontWeight: 700, fontSize: 15 }}>✓</span>
                <span>{action}</span>
              </div>
            ))}
            <div className="caption" style={{ marginTop: 8 }}>
              Source: {result.data_source}
            </div>
          </div>
        </>
      )}
    </div>
  );
}

// ── TCFD Report Section ───────────────────────────────────────────────────────

function TCFDReportSection({ physicalResult, transitionResult }) {
  const [entityName, setEntityName] = useState('');
  const [year, setYear] = useState(2030);
  const [loading, setLoading] = useState(false);
  const [report, setReport] = useState(null);
  const [error, setError] = useState(null);

  const canRun = physicalResult && transitionResult && entityName.trim();

  const run = async () => {
    setLoading(true);
    setError(null);
    setReport(null);
    try {
      const data = await callApi('tcfd', {
        entityName,
        physicalData: physicalResult,
        transitionData: transitionResult,
        year,
      });
      setReport(data);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  const downloadReport = () => {
    if (!report) return;
    const blob = new Blob([JSON.stringify(report, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `tcfd_report_${entityName.replace(/\s+/g, '_')}_${year}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const TCFD_ICONS = {
    A_governance: '🏛️',
    B_strategy: '🗺️',
    C_risk_management: '⚙️',
    D_metrics_and_targets: '📊',
    E_summary_heatmap: '🌡️',
  };

  return (
    <div>
      <div className="page-header">
        <h1>TCFD / ISSB S2 Climate Risk Report</h1>
        <p>Combines Physical + Transition risk into a standards-aligned disclosure report</p>
      </div>

      {/* Prerequisites */}
      <div className="card">
        <div className="card-title">Prerequisites</div>
        <div style={{ display: 'flex', gap: 20, fontSize: 13 }}>
          <div style={{
            display: 'flex', alignItems: 'center', gap: 8, padding: '8px 16px',
            borderRadius: 6, background: physicalResult ? '#f0fdf4' : '#fef2f2',
            border: `1px solid ${physicalResult ? '#86efac' : '#fca5a5'}`,
          }}>
            <span>{physicalResult ? '✅' : '❌'}</span>
            <span style={{ fontWeight: 600 }}>Physical Risk Analysis</span>
            <span style={{ color: '#64748b', fontSize: 11 }}>
              {physicalResult ? '(run complete)' : '— run Physical Risk tab first'}
            </span>
          </div>
          <div style={{
            display: 'flex', alignItems: 'center', gap: 8, padding: '8px 16px',
            borderRadius: 6, background: transitionResult ? '#f0fdf4' : '#fef2f2',
            border: `1px solid ${transitionResult ? '#86efac' : '#fca5a5'}`,
          }}>
            <span>{transitionResult ? '✅' : '❌'}</span>
            <span style={{ fontWeight: 600 }}>Transition Risk Analysis</span>
            <span style={{ color: '#64748b', fontSize: 11 }}>
              {transitionResult ? '(run complete)' : '— run Transition Risk tab first'}
            </span>
          </div>
        </div>
      </div>

      <div className="card">
        <div className="card-title">Report Settings</div>
        <div className="form-grid">
          <div className="form-group">
            <label>Entity / Company Name</label>
            <input type="text" placeholder="e.g. Tata Steel Jamshedpur"
              value={entityName} onChange={(e) => setEntityName(e.target.value)} />
          </div>
          <div className="form-group">
            <label>Reference Year</label>
            <select value={year} onChange={(e) => setYear(Number(e.target.value))}>
              {[2025, 2030, 2035, 2040].map((y) => <option key={y}>{y}</option>)}
            </select>
          </div>
        </div>
        <div style={{ marginTop: 16, display: 'flex', gap: 12 }}>
          <button className="btn-primary" onClick={run} disabled={loading || !canRun}>
            {loading ? <><Spinner /> Generating Report…</> : '📄 Generate TCFD Report'}
          </button>
          {report && (
            <button className="btn-outline" onClick={downloadReport}>
              ⬇ Download JSON
            </button>
          )}
        </div>
        {!canRun && !loading && (
          <div className="caption" style={{ marginTop: 8 }}>
            {!entityName.trim() ? 'Enter entity name above.' : 'Run both Physical and Transition analyses first.'}
          </div>
        )}
      </div>

      {error && <Alert type="error">{error}</Alert>}

      {/* Report output */}
      {report && (
        <>
          <Alert type="success">
            TCFD Report generated for <strong>{report.report_metadata?.entity}</strong> &nbsp;|&nbsp;
            {report.report_metadata?.report_type}
          </Alert>

          {/* Metadata */}
          <div className="card">
            <div className="card-title">Report Metadata</div>
            <table className="data-table">
              <tbody>
                {Object.entries(report.report_metadata || {}).map(([k, v]) => (
                  <tr key={k}>
                    <td style={{ width: 220, fontWeight: 600, color: '#374151' }}>
                      {k.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase())}
                    </td>
                    <td style={{ color: '#475569' }}>{String(v)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* TCFD Pillars */}
          {['A_governance', 'B_strategy', 'C_risk_management', 'D_metrics_and_targets'].map((key) => {
            const section = report[key];
            if (!section) return null;
            return (
              <div key={key} className="tcfd-section">
                <div className="tcfd-section-header">
                  <span style={{ fontSize: 20 }}>{TCFD_ICONS[key]}</span>
                  <h4>{section.tcfd_pillar}</h4>
                  <span className="tcfd-pillar-tag">TCFD Pillar</span>
                </div>
                <div className="tcfd-section-body">
                  {section.disclosure_text && (
                    <p style={{ fontSize: 13, color: '#374151', marginBottom: 12 }}>
                      {section.disclosure_text}
                    </p>
                  )}
                  {section.action_items && (
                    <>
                      <div style={{ fontSize: 12, fontWeight: 700, color: '#64748b', marginBottom: 6 }}>
                        ACTION ITEMS
                      </div>
                      {section.action_items.map((item, i) => (
                        <div key={i} style={{ fontSize: 13, padding: '4px 0', display: 'flex', gap: 8 }}>
                          <span style={{ color: '#0ea5e9' }}>→</span> {item}
                        </div>
                      ))}
                    </>
                  )}
                  {section.scenario_analysis && (
                    <table className="data-table" style={{ marginTop: 8 }}>
                      <tbody>
                        {Object.entries(section.scenario_analysis).map(([k, v]) => (
                          <tr key={k}>
                            <td style={{ width: 200, fontWeight: 600, fontSize: 12, color: '#374151' }}>
                              {k.replace(/_/g, ' ')}
                            </td>
                            <td style={{ fontSize: 12 }}>{String(v)}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  )}
                  {section.key_physical_risks?.length > 0 && (
                    <>
                      <div style={{ fontSize: 12, fontWeight: 700, color: '#64748b', margin: '12px 0 6px' }}>
                        KEY PHYSICAL RISKS
                      </div>
                      {section.key_physical_risks.map((r, i) => (
                        <div key={i} style={{ fontSize: 13, padding: '4px 0', display: 'flex', gap: 10 }}>
                          <RiskBadge level={r.risk_level} />
                          <span><strong>{r.hazard?.toUpperCase()}</strong> — {r.impact?.join(', ')}</span>
                        </div>
                      ))}
                    </>
                  )}
                  {section.key_transition_risks && (
                    <table className="data-table" style={{ marginTop: 8 }}>
                      <tbody>
                        {Object.entries(section.key_transition_risks).map(([k, v]) => (
                          <tr key={k}>
                            <td style={{ width: 220, fontWeight: 600, fontSize: 12 }}>
                              {k.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase())}
                            </td>
                            <td style={{ fontSize: 12 }}>{String(v)}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  )}
                  {section.climate_var_pct && (
                    <div style={{ marginTop: 8 }}>
                      <div style={{ fontSize: 24, fontWeight: 800, color: '#0f172a' }}>
                        {section.climate_var_pct}
                      </div>
                      <div style={{ fontSize: 12, color: '#64748b' }}>Climate VaR — {section.climate_var_description}</div>
                    </div>
                  )}
                  {section.recommended_targets && (
                    <>
                      <div style={{ fontSize: 12, fontWeight: 700, color: '#64748b', margin: '12px 0 6px' }}>
                        RECOMMENDED TARGETS
                      </div>
                      {section.recommended_targets.map((t, i) => (
                        <div key={i} style={{ fontSize: 13, padding: '4px 0', display: 'flex', gap: 8 }}>
                          <span style={{ color: '#16a34a' }}>✓</span> {t}
                        </div>
                      ))}
                    </>
                  )}
                </div>
              </div>
            );
          })}

          {/* Risk Heatmap */}
          {report.E_summary_heatmap && (
            <div className="card">
              <div className="card-title">🌡️ Risk Heatmap — Physical × Transition by Time Horizon</div>
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Time Horizon</th>
                    <th>Physical Risk</th>
                    <th>Transition Risk</th>
                  </tr>
                </thead>
                <tbody>
                  {Object.entries(report.E_summary_heatmap.matrix || {}).map(([horizon, risks]) => (
                    <tr key={horizon}>
                      <td><strong>{horizon}</strong></td>
                      <td><RiskBadge level={risks['Physical Risk']} /></td>
                      <td><RiskBadge level={risks['Transition Risk']} /></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </>
      )}
    </div>
  );
}

// ── Sidebar ───────────────────────────────────────────────────────────────────

function Sidebar({ activeTab, setActiveTab }) {
  const navItems = [
    { id: 'physical',   icon: '🌊', label: 'Physical Risk' },
    { id: 'transition', icon: '💰', label: 'Transition Risk' },
    { id: 'stranded',   icon: '🏚️', label: 'Stranded Assets' },
    { id: 'tcfd',       icon: '📋', label: 'TCFD Report' },
  ];

  return (
    <aside className="sidebar">
      <div className="sidebar-logo">
        <h2>🌍 Climate Risk Engine</h2>
        <p>Physical &amp; Transition Risk</p>
        <p style={{ marginTop: 4, fontSize: 10, color: '#334155' }}>
          TCFD · ISSB S2 · NGFS · IPCC AR6
        </p>
      </div>

      <nav className="sidebar-nav">
        <div className="nav-label">Analysis</div>
        {navItems.map((item) => (
          <div
            key={item.id}
            className={`nav-item ${activeTab === item.id ? 'active' : ''}`}
            onClick={() => setActiveTab(item.id)}
          >
            <span className="nav-icon">{item.icon}</span>
            {item.label}
          </div>
        ))}
      </nav>

      <div className="sidebar-info">
        <strong style={{ display: 'block', marginBottom: 6, fontSize: 11 }}>DATA SOURCES</strong>
        <p>IPCC AR6 (CMIP6 ensemble)</p>
        <p>NGFS Phase 5 Scenarios</p>
        <p>NASA NEX-GDDP</p>
        <p>OpenStreetMap / Nominatim</p>
        <p>Open-Elevation API</p>
        <p style={{ marginTop: 8, color: '#334155' }}>⚠ Simulation mode. Connect CMIP6 .nc files for full data.</p>
      </div>
    </aside>
  );
}

// ── Root Page ─────────────────────────────────────────────────────────────────

export default function Home() {
  const [activeTab, setActiveTab] = useState('physical');
  const [physicalResult, setPhysicalResult] = useState(null);
  const [transitionResult, setTransitionResult] = useState(null);

  return (
    <>
      <Head>
        <title>Climate Risk Engine | BTW AI</title>
        <meta name="description" content="Physical and Transition Climate Risk Analysis Platform — TCFD, ISSB S2, NGFS, IPCC AR6" />
        <meta name="viewport" content="width=device-width, initial-scale=1" />
        <link rel="icon" href="/favicon.ico" />
      </Head>

      <div className="layout">
        <Sidebar activeTab={activeTab} setActiveTab={setActiveTab} />

        <main className="main">
          {activeTab === 'physical' && (
            <PhysicalRiskSection onResult={setPhysicalResult} />
          )}
          {activeTab === 'transition' && (
            <TransitionRiskSection onResult={setTransitionResult} />
          )}
          {activeTab === 'stranded' && (
            <StrandedAssetsSection />
          )}
          {activeTab === 'tcfd' && (
            <TCFDReportSection
              physicalResult={physicalResult}
              transitionResult={transitionResult}
            />
          )}

          <div className="page-footer">
            Built by{' '}
            <a href="https://btw-ai.site" target="_blank" rel="noreferrer"
              style={{ color: '#0ea5e9' }}>BTW AI</a>
            {' '} | Data: IPCC AR6 · NGFS Phase 5 · NASA NEX-GDDP · OpenStreetMap · IIASA |{' '}
            Simulation mode. Not financial advice.
          </div>
        </main>
      </div>
    </>
  );
}
