"""
app.py — AgentRelief Algorithm Arena  (Streamlit UI)
=====================================================
Run with:  streamlit run app.py
"""
from __future__ import annotations

import os
import sys

_ROOT    = os.path.dirname(os.path.abspath(__file__))
_MODULES = os.path.join(_ROOT, "python modules")
for p in (_ROOT, _MODULES):
    if p not in sys.path:
        sys.path.insert(0, p)

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from data_store  import store
from arena.pipeline import ArenaPipeline, BenchmarkReport
from arena.evaluator import AlgorithmResult

# ─────────────────────────────────────────────────────────────────────────────
# Page config
# ─────────────────────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="AgentRelief — Algorithm Arena",
    page_icon=":material/dashboard:",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─────────────────────────────────────────────────────────────────────────────
# Custom CSS — clean light theme
# ─────────────────────────────────────────────────────────────────────────────

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;600&display=swap');

/* ── Global ── */
html, body {
    font-family: 'Inter', sans-serif;
    color: #111111;
}
.stApp { background: #f8f9fa; color: #111111; }
[data-testid="stAppViewContainer"] { background: #f8f9fa; }
[data-testid="stHeader"] { background: #ffffff; border-bottom: 1px solid #e5e7eb; }
p, label, span, div { color: #111111; }

/* ── Sidebar ── */
[data-testid="stSidebar"] {
    background: #ffffff;
    border-right: 1px solid #e5e7eb;
}
[data-testid="stSidebar"] [data-testid="stMarkdownContainer"],
[data-testid="stSidebar"] label,
[data-testid="stSidebar"] p,
[data-testid="stSidebar"] span {
    color: #111111 !important;
}
[data-testid="stSidebar"] .stSlider label { color: #111111 !important; }

/* ── Header ── */
.arena-header {
    background: #ffffff;
    border: 1px solid #e5e7eb;
    border-radius: 16px;
    padding: 24px 28px;
    margin-bottom: 20px;
    position: relative;
    overflow: hidden;
    box-shadow: 0 8px 24px rgba(15, 23, 42, 0.06);
}
.arena-header::before {
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0; height: 3px;
    background: linear-gradient(90deg, #2563eb, #60a5fa, #93c5fd);
}
.arena-title {
    font-size: clamp(1.5rem, 2.8vw, 2.2rem);
    font-weight: 700;
    color: #111111;
    margin: 0 0 6px 0;
}
.arena-subtitle {
    color: #222222;
    font-size: 0.95rem;
    font-weight: 400;
}

/* ── Stage section ── */
.stage-header {
    display: flex;
    align-items: center;
    gap: 12px;
    background: #ffffff;
    border: 1px solid #e5e7eb;
    border-left: 4px solid;
    border-radius: 12px;
    padding: 14px 16px;
    margin: 20px 0 14px 0;
    box-shadow: 0 4px 18px rgba(15, 23, 42, 0.05);
}
.stage-icon {
    font-size: 0.72rem;
    font-weight: 700;
    color: #1d4ed8;
    background: #eff6ff;
    border: 1px solid #bfdbfe;
    border-radius: 999px;
    padding: 0.2rem 0.5rem;
}
.stage-title {
    font-size: 1.1rem;
    font-weight: 600;
    color: #111827;
    margin: 0;
}
.stage-subtitle {
    font-size: 0.8rem;
    color: #374151;
    margin: 2px 0 0 0;
}

/* ── Algorithm card ── */
.algo-card {
    background: #ffffff;
    border: 1px solid #e5e7eb;
    border-radius: 14px;
    padding: 16px;
    height: 100%;
    position: relative;
    transition: border-color 0.2s, box-shadow 0.2s;
    box-shadow: 0 8px 20px rgba(15, 23, 42, 0.04);
}
.algo-card:hover {
    border-color: #cbd5e1;
    box-shadow: 0 10px 22px rgba(15, 23, 42, 0.08);
}
.algo-card.winner {
    border-color: #93c5fd;
    background: #f8fbff;
    box-shadow: 0 10px 24px rgba(37, 99, 235, 0.12);
}
.algo-name {
    font-size: 1rem;
    font-weight: 600;
    color: #111827;
    margin: 0 0 4px 0;
}
.algo-complexity {
    font-size: 0.75rem;
    color: #6b7280;
    font-family: 'JetBrains Mono', monospace;
    margin: 0 0 16px 0;
}
.winner-badge {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    background: linear-gradient(135deg, #1d4ed8, #2563eb);
    color: white;
    font-size: 0.75rem;
    font-weight: 600;
    padding: 4px 10px;
    border-radius: 20px;
    margin-bottom: 12px;
}
.metric-row {
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 8px;
    padding: 8px 0;
    border-bottom: 1px solid #edf2f7;
}
.metric-row:last-child { border-bottom: none; }
.metric-label { color: #374151; font-size: 0.82rem; }
.metric-value {
    font-weight: 600;
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.85rem;
    color: #111111;
    text-align: right;
}
.metric-value.green  { color: #15803d; }
.metric-value.blue   { color: #2563eb; }
.metric-value.purple { color: #7c3aed; }
.metric-value.orange { color: #c2410c; }

/* ── Composite score bar ── */
.composite-bar-bg {
    background: #e5e7eb;
    border-radius: 8px;
    height: 6px;
    margin-top: 14px;
    overflow: hidden;
}
.composite-bar-fill {
    height: 100%;
    border-radius: 8px;
    background: linear-gradient(90deg, #2563eb, #14b8a6);
}

/* ── Summary metric pill ── */
.summary-pill {
    background: #ffffff;
    border: 1px solid #e5e7eb;
    border-radius: 12px;
    padding: 14px 16px;
    text-align: center;
    box-shadow: 0 6px 16px rgba(15, 23, 42, 0.04);
    margin-bottom: 10px;
}
.summary-pill-value {
    font-size: 1.55rem;
    font-weight: 700;
    background: linear-gradient(135deg, #1d4ed8, #0f766e);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    display: block;
    margin-bottom: 4px;
}
.summary-pill-label {
    color: #374151;
    font-size: 0.8rem;
    font-weight: 500;
}

/* ── Info box ── */
.info-box {
    background: #eff6ff;
    border: 1px solid #bfdbfe;
    border-radius: 10px;
    padding: 12px 14px;
    color: #1e3a8a;
    font-size: 0.85rem;
    line-height: 1.6;
}

/* ── Streamlit components ── */
.stButton > button {
    background: #ffffff;
    color: #111111;
    border: 1px solid #d1d5db;
    border-radius: 10px;
    font-weight: 600;
    min-height: 2.6rem;
    opacity: 1;
}
.stButton > button:hover {
    background: #f3f4f6;
    border-color: #94a3b8;
}
.stButton > button[kind="primary"] {
    background: #2563eb;
    color: #ffffff;
    border-color: #2563eb;
}
.stButton > button[kind="primary"]:hover {
    background: #1d4ed8;
    border-color: #1d4ed8;
}
.stButton > button:disabled,
.stButton > button[disabled] {
    background: #e5e7eb !important;
    color: #4b5563 !important;
    border-color: #d1d5db !important;
    opacity: 1 !important;
}

div[data-baseweb="input"] input,
div[data-baseweb="textarea"] textarea,
div[data-baseweb="select"] > div,
div[data-baseweb="input"] > div {
    color: #111111 !important;
    background: #ffffff !important;
}
input::placeholder, textarea::placeholder { color: #6b7280 !important; opacity: 1 !important; }

div[data-baseweb="input"] > div,
div[data-baseweb="select"] > div,
div[data-baseweb="textarea"] > div {
    border-color: #d1d5db !important;
}
div[data-baseweb="input"] > div:hover,
div[data-baseweb="select"] > div:hover,
div[data-baseweb="textarea"] > div:hover {
    border-color: #94a3b8 !important;
}

div[data-testid="stDataFrame"] {
    border: 1px solid #e5e7eb;
    border-radius: 10px;
    overflow: hidden;
    background: #ffffff;
}
div[data-testid="stDataFrame"] * {
    color: #111111 !important;
}
div[data-testid="stExpander"] {
    border: 1px solid #e5e7eb;
    border-radius: 10px;
    background: #ffffff;
}
div[data-testid="stExpander"] details summary p {
    color: #1f2937;
    font-weight: 600;
}

/* ── Responsive rules ── */
@media (max-width: 1024px) {
    .arena-header { padding: 18px 20px; }
    .stage-header { padding: 12px 14px; }
}
@media (max-width: 768px) {
    .metric-row { flex-wrap: wrap; }
    .metric-value { text-align: left; }
    div[data-testid="stHorizontalBlock"] {
        flex-wrap: wrap;
        gap: 0.5rem;
    }
    div[data-testid="column"] {
        min-width: 100% !important;
        flex: 1 1 100% !important;
    }
}
</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# Demo scenario data (same as main.py DEMO dict)
# ─────────────────────────────────────────────────────────────────────────────

DEMO = {
    "requests": [
        {"id": "REQ-001", "location": "Village A",   "severity": "High",     "people_affected": 150, "deadline_hours": 6,  "distance_km": 20, "need_type": "Medical", "status": "pending"},
        {"id": "REQ-002", "location": "Village B",   "severity": "Medium",   "people_affected": 80,  "deadline_hours": 12, "distance_km": 35, "need_type": "Food",    "status": "pending"},
        {"id": "REQ-003", "location": "Village C",   "severity": "Critical", "people_affected": 340, "deadline_hours": 2,  "distance_km": 15, "need_type": "Medical", "status": "pending"},
        {"id": "REQ-004", "location": "Hospital B",  "severity": "High",     "people_affected": 210, "deadline_hours": 4,  "distance_km": 10, "need_type": "Rescue",  "status": "pending"},
        {"id": "REQ-005", "location": "Camp North",  "severity": "Low",      "people_affected": 45,  "deadline_hours": 24, "distance_km": 50, "need_type": "Shelter", "status": "pending"},
        {"id": "REQ-006", "location": "East Hamlet", "severity": "High",     "people_affected": 120, "deadline_hours": 8,  "distance_km": 30, "need_type": "Water",   "status": "pending"},
    ],
    "resources": [
        {"id": "RES-001", "name": "Medicine Kits",   "weight": 2.0,  "value": 150.0, "quantity": 30.0},
        {"id": "RES-002", "name": "Food Rations",    "weight": 5.0,  "value": 80.0,  "quantity": 50.0},
        {"id": "RES-003", "name": "Water Canisters", "weight": 10.0, "value": 100.0, "quantity": 20.0},
        {"id": "RES-004", "name": "Stretchers",      "weight": 8.0,  "value": 120.0, "quantity": 10.0},
        {"id": "RES-005", "name": "Tents",           "weight": 15.0, "value": 90.0,  "quantity": 15.0},
        {"id": "RES-006", "name": "Radio Units",     "weight": 1.0,  "value": 200.0, "quantity": 5.0},
        {"id": "RES-007", "name": "Water Purifiers", "weight": 3.0,  "value": 130.0, "quantity": 8.0},
    ],
    "teams": [
        {"id": "TEAM-01", "name": "MedForce Alpha",  "specialization": "medical",   "capacity": 200, "available": True, "base_location": "HQ",          "deploy_cost": 20.0},
        {"id": "TEAM-02", "name": "RescueBrigade",   "specialization": "rescue",    "capacity": 150, "available": True, "base_location": "Base South",   "deploy_cost": 25.0},
        {"id": "TEAM-03", "name": "LogiCore",        "specialization": "logistics", "capacity": 100, "available": True, "base_location": "Depot West",   "deploy_cost": 15.0},
        {"id": "TEAM-04", "name": "GenForce",        "specialization": "general",   "capacity": 80,  "available": True, "base_location": "HQ",           "deploy_cost": 10.0},
        {"id": "TEAM-05", "name": "MedForce Beta",   "specialization": "medical",   "capacity": 180, "available": True, "base_location": "Base South",   "deploy_cost": 20.0},
        {"id": "TEAM-06", "name": "AquaLogistics",   "specialization": "logistics", "capacity": 90,  "available": True, "base_location": "Depot West",   "deploy_cost": 12.0},
    ],
    "graph_nodes": ["HQ", "Junction X", "Village A", "Village B", "Village C",
                    "Hospital B", "Camp North", "Base South", "Depot West", "East Hamlet"],
    "graph_edges": [
        ("HQ",          "Junction X",  8),
        ("Junction X",  "Village A",  14),
        ("Junction X",  "Village C",   9),
        ("Junction X",  "Hospital B",  7),
        ("HQ",          "Depot West", 12),
        ("Depot West",  "Village B",  25),
        ("Village B",   "Camp North", 18),
        ("Base South",  "Hospital B",  6),
        ("Base South",  "Village A",  16),
        ("Base South",  "Village C",  12),
        ("HQ",          "Hospital B", 15),
        ("HQ",          "Village A",  20),
        ("Junction X",  "East Hamlet",11),
        ("Depot West",  "East Hamlet",14),
    ],
}

REQUEST_COLUMNS = ["id", "location", "severity", "people_affected", "deadline_hours", "distance_km", "need_type", "status"]
RESOURCE_COLUMNS = ["id", "name", "weight", "value", "quantity"]
TEAM_COLUMNS = ["id", "name", "specialization", "capacity", "available", "base_location", "deploy_cost"]
NODE_COLUMNS = ["node"]
EDGE_COLUMNS = ["source", "target", "distance_km"]


def _init_custom_state():
    if "custom_requests_df" not in st.session_state:
        st.session_state.custom_requests_df = pd.DataFrame(DEMO["requests"])[REQUEST_COLUMNS]
    if "custom_resources_df" not in st.session_state:
        st.session_state.custom_resources_df = pd.DataFrame(DEMO["resources"])[RESOURCE_COLUMNS]
    if "custom_teams_df" not in st.session_state:
        st.session_state.custom_teams_df = pd.DataFrame(DEMO["teams"])[TEAM_COLUMNS]
    if "custom_nodes_df" not in st.session_state:
        st.session_state.custom_nodes_df = pd.DataFrame({"node": DEMO["graph_nodes"]})
    if "custom_edges_df" not in st.session_state:
        st.session_state.custom_edges_df = pd.DataFrame(DEMO["graph_edges"], columns=EDGE_COLUMNS)


def _normalize_df(df: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    out = df.copy() if isinstance(df, pd.DataFrame) else pd.DataFrame(columns=columns)
    for col in columns:
        if col not in out.columns:
            out[col] = None
    return out[columns]


def _build_selected_data(scenario_name: str):
    if scenario_name == "Demo Scenario":
        return DEMO, []

    warnings = []

    req_df = _normalize_df(st.session_state.get("custom_requests_df"), REQUEST_COLUMNS)
    res_df = _normalize_df(st.session_state.get("custom_resources_df"), RESOURCE_COLUMNS)
    team_df = _normalize_df(st.session_state.get("custom_teams_df"), TEAM_COLUMNS)
    nodes_df = _normalize_df(st.session_state.get("custom_nodes_df"), NODE_COLUMNS)
    edges_df = _normalize_df(st.session_state.get("custom_edges_df"), EDGE_COLUMNS)

    req_df = req_df.dropna(how="all")
    res_df = res_df.dropna(how="all")
    team_df = team_df.dropna(how="all")
    nodes_df = nodes_df.dropna(how="all")
    edges_df = edges_df.dropna(how="all")

    if req_df.empty or res_df.empty or team_df.empty:
        warnings.append("Custom scenario is incomplete. Using demo data instead.")
        return DEMO, warnings

    req_df["id"] = req_df["id"].fillna("").astype(str).str.strip()
    req_df["location"] = req_df["location"].fillna("Unknown").astype(str).str.strip()
    req_df["severity"] = req_df["severity"].fillna("Medium").astype(str).str.strip()
    req_df["need_type"] = req_df["need_type"].fillna("General").astype(str).str.strip()
    req_df["status"] = req_df["status"].fillna("pending").astype(str).str.strip()
    req_df["people_affected"] = pd.to_numeric(req_df["people_affected"], errors="coerce").fillna(0).astype(int)
    req_df["deadline_hours"] = pd.to_numeric(req_df["deadline_hours"], errors="coerce").fillna(24.0).astype(float)
    req_df["distance_km"] = pd.to_numeric(req_df["distance_km"], errors="coerce").fillna(10.0).astype(float)
    req_df = req_df[req_df["id"] != ""]
    if req_df.empty:
        warnings.append("Custom requests are missing IDs. Using demo data instead.")
        return DEMO, warnings

    res_df["id"] = res_df["id"].fillna("").astype(str).str.strip()
    res_df["name"] = res_df["name"].fillna("Resource").astype(str).str.strip()
    res_df["weight"] = pd.to_numeric(res_df["weight"], errors="coerce").fillna(1.0).astype(float)
    res_df["value"] = pd.to_numeric(res_df["value"], errors="coerce").fillna(1.0).astype(float)
    res_df["quantity"] = pd.to_numeric(res_df["quantity"], errors="coerce").fillna(1.0).astype(float)
    res_df = res_df[res_df["id"] != ""]
    if res_df.empty:
        warnings.append("Custom resources are missing IDs. Using demo data instead.")
        return DEMO, warnings

    team_df["id"] = team_df["id"].fillna("").astype(str).str.strip()
    team_df["name"] = team_df["name"].fillna("Team").astype(str).str.strip()
    team_df["specialization"] = team_df["specialization"].fillna("general").astype(str).str.strip()
    team_df["base_location"] = team_df["base_location"].fillna("HQ").astype(str).str.strip()
    team_df["capacity"] = pd.to_numeric(team_df["capacity"], errors="coerce").fillna(50).astype(int)
    team_df["deploy_cost"] = pd.to_numeric(team_df["deploy_cost"], errors="coerce").fillna(10.0).astype(float)
    team_df["available"] = team_df["available"].fillna(True).astype(bool)
    team_df = team_df[team_df["id"] != ""]
    if team_df.empty:
        warnings.append("Custom teams are missing IDs. Using demo data instead.")
        return DEMO, warnings

    nodes = nodes_df["node"].fillna("").astype(str).str.strip().tolist()
    nodes = [n for n in nodes if n]
    if not nodes:
        nodes = list(DEMO["graph_nodes"])
        warnings.append("Custom network nodes were empty. Using demo network nodes.")

    edges_df["source"] = edges_df["source"].fillna("").astype(str).str.strip()
    edges_df["target"] = edges_df["target"].fillna("").astype(str).str.strip()
    edges_df["distance_km"] = pd.to_numeric(edges_df["distance_km"], errors="coerce").fillna(0.0).astype(float)
    edges_df = edges_df[(edges_df["source"] != "") & (edges_df["target"] != "") & (edges_df["distance_km"] > 0)]
    edges = [(row.source, row.target, float(row.distance_km)) for row in edges_df.itertuples(index=False)]
    if not edges:
        edges = list(DEMO["graph_edges"])
        warnings.append("Custom network edges were invalid or empty. Using demo network edges.")

    for src, dst, _ in edges:
        if src not in nodes:
            nodes.append(src)
        if dst not in nodes:
            nodes.append(dst)

    custom_data = {
        "requests": req_df.to_dict("records"),
        "resources": res_df.to_dict("records"),
        "teams": team_df.to_dict("records"),
        "graph_nodes": nodes,
        "graph_edges": edges,
    }
    return custom_data, warnings


# ─────────────────────────────────────────────────────────────────────────────
# Sidebar
# ─────────────────────────────────────────────────────────────────────────────

with st.sidebar:
    st.markdown("## Arena Controls")
    st.markdown("---")
    st.caption("Step 1: Choose scenario and parameters")

    scenario = st.radio(
        "Scenario",
        ["Demo Scenario", "Custom"],
        help="Demo loads the built-in 6-request disaster scenario.",
    )

    st.markdown("### Pipeline Parameters")
    capacity = st.slider("Carrier Capacity (kg)", 100, 1000, 500, step=50,
                         help="Max weight the supply carrier can hold.")
    budget   = st.slider("Team Budget (units)",    50, 2000, 1000, step=50,
                         help="Total deployment budget for team assignment.")

    st.markdown("### Algorithm Selection Weights")
    st.markdown('<div class="info-box">Drag to favour a metric when picking the best algorithm at each stage.</div>', unsafe_allow_html=True)
    st.markdown("")

    w_speed   = st.slider("Speed Weight",   0.0, 1.0, 0.30, step=0.05)
    w_memory  = st.slider("Memory Weight",  0.0, 1.0, 0.20, step=0.05)
    w_quality = st.slider("Quality Weight", 0.0, 1.0, 0.50, step=0.05)
    weight_total = w_speed + w_memory + w_quality
    if weight_total == 0:
        st.error("At least one algorithm selection weight must be greater than 0.")
    elif abs(weight_total - 1.0) > 0.001:
        st.warning(f"Weights currently sum to {weight_total:.2f}. Results still run, but balanced weights usually improve comparisons.")
    else:
        st.success("Weights are balanced.")

    st.markdown("---")
    st.caption("Step 2: Run the pipeline")
    run_btn = st.button("Run Algorithm Arena", use_container_width=True, type="primary", disabled=(weight_total == 0))


# ─────────────────────────────────────────────────────────────────────────────
# Header
# ─────────────────────────────────────────────────────────────────────────────

st.markdown("""
<div class="arena-header">
  <div class="arena-title">AgentRelief Algorithm Arena</div>
  <div class="arena-subtitle">
    Multi-algorithm benchmarking for every stage of the disaster relief pipeline.
    Each stage races all algorithms in parallel · measures time &amp; memory · picks the best.
  </div>
</div>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# Helper: render one algorithm race section
# ─────────────────────────────────────────────────────────────────────────────

COMPLEXITY = {
    "Greedy Max-Heap":       "O(n log n) time · O(n) space",
    "Simple Sort (TimSort)": "O(n log n) time · O(n) space",
    "Fractional Knapsack":   "O(n log n) time · O(n) space",
    "0/1 Knapsack DP":       "O(n × W) time · O(n × W) space",
    "Dijkstra":              "O((V+E) log V) time · O(V) space",
    "Bellman-Ford":          "O(V × E) time · O(V) space",
    "A* Search":             "O(E log V) time · O(V) space",
    "Backtracking":          "O(n!) pruned to O(k) · O(n) space",
    "Branch & Bound":        "O(n!) pruned by LP bound · O(n) space",
}

STAGE_COLORS = {
    "prioritization": "#1d4ed8",
    "allocation":     "#2563eb",
    "routing":        "#3b82f6",
    "assignment":     "#60a5fa",
}


def render_race_section(
    icon: str,
    title: str,
    subtitle: str,
    results: list[AlgorithmResult],
    winner: AlgorithmResult,
    color: str,
):
    st.markdown(f"""
    <div class="stage-header" style="border-left-color: {color};">
      <span class="stage-icon">{icon}</span>
      <div>
        <div class="stage-title">{title}</div>
        <div class="stage-subtitle">{subtitle}</div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    cols = st.columns(len(results))
    for col, result in zip(cols, results):
        is_winner = result.algorithm_name == winner.algorithm_name
        card_class = "algo-card winner" if is_winner else "algo-card"

        # Build metric rows HTML
        quality_lbl = result.quality_label or "Quality Score"
        direction   = "↓ lower=better" if result.lower_quality_is_better else "↑ higher=better"

        badge_html = ''
        if is_winner:
            badge_html = f'<div class="winner-badge">Winner · Composite {winner.composite_score:.3f}</div>'

        composite_pct = max(0.0, min(1.0, result.composite_score)) * 100

        with col:
            st.markdown(f"""
            <div class="{card_class}">
              <div class="algo-name">{result.algorithm_name}</div>
              <div class="algo-complexity">{COMPLEXITY.get(result.algorithm_name, '')}</div>
              {badge_html}

              <div class="metric-row">
                <span class="metric-label">Exec Time</span>
                <span class="metric-value {'green' if is_winner else 'blue'}">{result.exec_time_ms:.3f} ms</span>
              </div>
              <div class="metric-row">
                <span class="metric-label">Peak Memory</span>
                <span class="metric-value {'green' if is_winner else 'purple'}">{result.memory_kb:.2f} KB</span>
              </div>
              <div class="metric-row">
                <span class="metric-label">{quality_lbl}</span>
                <span class="metric-value {'green' if is_winner else 'orange'}">{result.quality_score:.2f} <span style="font-size:0.7rem;color:#6b7280">{direction}</span></span>
              </div>
              <div class="metric-row">
                <span class="metric-label">Composite Score</span>
                <span class="metric-value blue">{result.composite_score:.4f}</span>
              </div>

              <div class="composite-bar-bg">
                <div class="composite-bar-fill" style="width: {composite_pct:.1f}%"></div>
              </div>
            </div>
            """, unsafe_allow_html=True)

    # Bar chart comparison
    names   = [r.algorithm_name for r in results]
    times   = [r.exec_time_ms   for r in results]
    mems    = [r.memory_kb      for r in results]
    comps   = [r.composite_score for r in results]

    fig = go.Figure()
    fig.add_trace(go.Bar(name="Exec Time (ms)",  x=names, y=times,  marker_color="#2563eb"))
    fig.add_trace(go.Bar(name="Memory (KB)",     x=names, y=mems,   marker_color="#7c3aed"))
    fig.add_trace(go.Bar(name="Composite Score", x=names, y=comps,  marker_color="#16a34a"))
    fig.update_layout(
        barmode="group",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#111827", family="Inter"),
        legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(color="#1f2937")),
        xaxis=dict(gridcolor="#e5e7eb"),
        yaxis=dict(gridcolor="#e5e7eb"),
        margin=dict(l=0, r=0, t=20, b=0),
        height=280,
    )
    st.plotly_chart(fig, use_container_width=True)

    if results[0].metadata.get("error"):
        st.error(f"Error in algorithm: {results[0].metadata['error']}")


def render_network_graph(report: BenchmarkReport, graph_edges, graph_nodes):
    """Plotly network graph with winning routes highlighted."""
    if not graph_edges:
        return

    # Build position map (simple circle layout)
    import math
    nodes = list(graph_nodes)
    n = len(nodes)
    pos = {}
    for i, node in enumerate(nodes):
        angle = 2 * math.pi * i / n
        pos[node] = (math.cos(angle), math.sin(angle))

    # All edges (grey)
    edge_x, edge_y = [], []
    for u, v, w in graph_edges:
        if u in pos and v in pos:
            x0, y0 = pos[u]
            x1, y1 = pos[v]
            edge_x += [x0, x1, None]
            edge_y += [y0, y1, None]

    # Winning routes (highlighted)
    win_routes = report.routing_winner.output or {}
    highlight_x, highlight_y = [], []

    all_path_nodes = set()
    for key, (dist, path) in win_routes.items():
        for i in range(len(path) - 1):
            u, v = path[i], path[i+1]
            if u in pos and v in pos:
                x0, y0 = pos[u]
                x1, y1 = pos[v]
                highlight_x += [x0, x1, None]
                highlight_y += [y0, y1, None]
        all_path_nodes.update(path)

    node_colors = ["#2563eb" if n in all_path_nodes else "#94a3b8" for n in nodes]
    node_x = [pos[n][0] for n in nodes]
    node_y = [pos[n][1] for n in nodes]

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=edge_x, y=edge_y, mode="lines",
                             line=dict(color="#d1d5db", width=1.5), hoverinfo="none"))
    fig.add_trace(go.Scatter(x=highlight_x, y=highlight_y, mode="lines",
                             line=dict(color="#3b82f6", width=3), hoverinfo="none", name="Best Path"))
    fig.add_trace(go.Scatter(
        x=node_x, y=node_y, mode="markers+text",
        marker=dict(size=16, color=node_colors, line=dict(color="#ffffff", width=2)),
        text=nodes, textposition="top center",
        textfont=dict(color="#111827", size=11, family="Inter"),
        hoverinfo="text",
    ))
    fig.update_layout(
        showlegend=False,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        margin=dict(l=0, r=0, t=10, b=0),
        height=350,
    )
    st.plotly_chart(fig, use_container_width=True)


# ─────────────────────────────────────────────────────────────────────────────
# Main — triggered on Run button
# ─────────────────────────────────────────────────────────────────────────────

_init_custom_state()

if not run_btn:
    # Landing state — show input summary
    st.markdown("### Scenario Preview")
    st.caption("Review or edit data, then run the arena from the sidebar.")

    if scenario == "Custom":
        st.info("Edit custom scenario data below. The pipeline will run using these values.")
        c_reset1, c_reset2 = st.columns([2, 1])
        with c_reset1:
            confirm_reset = st.checkbox("Confirm reset of all custom scenario data")
        with c_reset2:
            if st.button("Reset Custom Data", use_container_width=True, disabled=not confirm_reset):
                st.session_state.custom_requests_df = pd.DataFrame(DEMO["requests"])[REQUEST_COLUMNS]
                st.session_state.custom_resources_df = pd.DataFrame(DEMO["resources"])[RESOURCE_COLUMNS]
                st.session_state.custom_teams_df = pd.DataFrame(DEMO["teams"])[TEAM_COLUMNS]
                st.session_state.custom_nodes_df = pd.DataFrame({"node": DEMO["graph_nodes"]})
                st.session_state.custom_edges_df = pd.DataFrame(DEMO["graph_edges"], columns=EDGE_COLUMNS)
                st.success("Custom scenario reset to demo defaults.")
                st.rerun()
        tab_req, tab_res, tab_team, tab_net = st.tabs(["Requests", "Resources", "Teams", "Network"])

        with tab_req:
            st.caption("Add at least one valid request with an ID.")
            st.session_state.custom_requests_df = st.data_editor(
                st.session_state.custom_requests_df,
                num_rows="dynamic",
                use_container_width=True,
                hide_index=True,
                key="custom_requests_editor",
            )
        with tab_res:
            st.caption("Add resources with positive weight, value, and quantity.")
            st.session_state.custom_resources_df = st.data_editor(
                st.session_state.custom_resources_df,
                num_rows="dynamic",
                use_container_width=True,
                hide_index=True,
                key="custom_resources_editor",
            )
        with tab_team:
            st.caption("Add available teams with valid IDs and capacities.")
            st.session_state.custom_teams_df = st.data_editor(
                st.session_state.custom_teams_df,
                num_rows="dynamic",
                use_container_width=True,
                hide_index=True,
                key="custom_teams_editor",
            )
        with tab_net:
            c1, c2 = st.columns(2)
            with c1:
                st.markdown("**Nodes**")
                st.caption("List every location node used in routes.")
                st.session_state.custom_nodes_df = st.data_editor(
                    st.session_state.custom_nodes_df,
                    num_rows="dynamic",
                    use_container_width=True,
                    hide_index=True,
                    key="custom_nodes_editor",
                )
            with c2:
                st.markdown("**Edges**")
                st.caption("Define source, target, and positive distance.")
                st.session_state.custom_edges_df = st.data_editor(
                    st.session_state.custom_edges_df,
                    num_rows="dynamic",
                    use_container_width=True,
                    hide_index=True,
                    key="custom_edges_editor",
                )
    else:
        data = DEMO
        tab_req, tab_res, tab_team = st.tabs(["Requests", "Resources", "Teams"])

        with tab_req:
            df_req = pd.DataFrame(data["requests"])[
                ["id", "location", "severity", "people_affected", "need_type"]
            ]
            df_req.columns = ["ID", "Location", "Severity", "People", "Need"]
            st.dataframe(df_req, use_container_width=True, hide_index=True)

        with tab_res:
            df_res = pd.DataFrame(data["resources"])[["id", "name", "weight", "value", "quantity"]]
            df_res.columns = ["ID", "Name", "Weight", "Value", "Qty"]
            st.dataframe(df_res, use_container_width=True, hide_index=True)

        with tab_team:
            df_teams = pd.DataFrame(data["teams"])[["id", "name", "specialization", "capacity", "deploy_cost"]]
            df_teams.columns = ["ID", "Name", "Spec", "Capacity", "Cost"]
            st.dataframe(df_teams, use_container_width=True, hide_index=True)

    st.markdown("---")
    st.markdown(
        '<div class="info-box">Next: configure sidebar controls and click <strong>Run Algorithm Arena</strong>.</div>',
        unsafe_allow_html=True,
    )
    st.stop()


# ─────────────────────────────────────────────────────────────────────────────
# Load data into store snapshot
# ─────────────────────────────────────────────────────────────────────────────

data, ui_warnings = _build_selected_data(scenario)
for msg in ui_warnings:
    st.warning(msg)

if scenario == "Custom" and not ui_warnings:
    st.success("Custom scenario loaded successfully.")

# Populate the store singleton
store.requests    = list(data["requests"])
store.resources   = list(data["resources"])
store.teams       = list(data["teams"])
store.graph_nodes = list(data["graph_nodes"])
store.graph_edges = [tuple(e) for e in data["graph_edges"]]


# ─────────────────────────────────────────────────────────────────────────────
# Run the pipeline
# ─────────────────────────────────────────────────────────────────────────────

with st.spinner("Running algorithms... please wait"):
    pipeline = ArenaPipeline(
        store,
        weight_time    = w_speed,
        weight_memory  = w_memory,
        weight_quality = w_quality,
        capacity_kg    = float(capacity),
        budget_units   = float(budget),
    )
    report: BenchmarkReport = pipeline.run()

st.success("Pipeline run complete.")


# ─────────────────────────────────────────────────────────────────────────────
# Section 1 — Pipeline summary metrics
# ─────────────────────────────────────────────────────────────────────────────

st.markdown("### Pipeline Results")
st.caption("Review summary metrics first, then inspect stage-level race details and final dispatch.")

unassigned_count = len(report.unassigned)
top_row = st.columns(3)
bottom_row = st.columns(2)

with top_row[0]:
    st.markdown(f"""
    <div class="summary-pill">
      <span class="summary-pill-value">{report.total_pipeline_ms:.1f}</span>
      <span class="summary-pill-label">Total Pipeline (ms)</span>
    </div>""", unsafe_allow_html=True)
with top_row[1]:
    st.markdown(f"""
    <div class="summary-pill">
      <span class="summary-pill-value">{len(report.dispatch_rows)}</span>
      <span class="summary-pill-label">Requests Processed</span>
    </div>""", unsafe_allow_html=True)
with top_row[2]:
    st.markdown(f"""
    <div class="summary-pill">
      <span class="summary-pill-value">{report.total_assignment_score:.1f}</span>
      <span class="summary-pill-label">Assignment Score</span>
    </div>""", unsafe_allow_html=True)

with bottom_row[0]:
    st.markdown(f"""
    <div class="summary-pill">
      <span class="summary-pill-value">{report.total_resource_value:.0f}</span>
      <span class="summary-pill-label">Resource Value</span>
    </div>""", unsafe_allow_html=True)
with bottom_row[1]:
    st.markdown(f"""
    <div class="summary-pill">
      <span class="summary-pill-value" style="{'color:#dc2626;-webkit-text-fill-color:#dc2626' if unassigned_count else ''}">{unassigned_count}</span>
      <span class="summary-pill-label">Unassigned Requests</span>
    </div>""", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# Section 2 — Prioritization Race
# ─────────────────────────────────────────────────────────────────────────────

render_race_section(
    icon="S1",
    title="Stage 1: Request Prioritization",
    subtitle="Ranking 6 disaster requests by urgency score",
    results=report.prioritization_results,
    winner=report.prioritization_winner,
    color=STAGE_COLORS["prioritization"],
)

with st.expander("Prioritized Request Order (winning algorithm)"):
    ranked = report.prioritization_winner.output or []
    if ranked:
        df_r = pd.DataFrame(ranked)
        cols_show = [c for c in ["id", "location", "severity", "people_affected", "deadline_hours", "score"] if c in df_r.columns]
        st.dataframe(df_r[cols_show].rename(columns={
            "id": "ID", "location": "Location", "severity": "Severity",
            "people_affected": "People", "deadline_hours": "Deadline (h)", "score": "Priority Score"
        }), use_container_width=True, hide_index=True)
    else:
        st.info("No prioritized requests were produced.")


# ─────────────────────────────────────────────────────────────────────────────
# Section 3 — Resource Allocation Race
# ─────────────────────────────────────────────────────────────────────────────

render_race_section(
    icon="S2",
    title="Stage 2: Resource Allocation",
    subtitle=f"Optimizing cargo load within {capacity} kg capacity",
    results=report.allocation_results,
    winner=report.allocation_winner,
    color=STAGE_COLORS["allocation"],
)

with st.expander("Allocated Resources (winning algorithm)"):
    alloc = report.allocation_winner.output or []
    if alloc:
        rows = []
        for r in alloc:
            rows.append({
                "ID":     getattr(r, "id", ""),
                "Name":   getattr(r, "name", ""),
                "Qty":    round(getattr(r, "quantity", 0), 2),
                "Weight (kg)": round(getattr(r, "weight", 0) * getattr(r, "quantity", 0), 2),
                "Value":  round(getattr(r, "value", 0) * getattr(r, "quantity", 0), 2),
            })
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
    else:
        st.info("No resources were allocated.")


# ─────────────────────────────────────────────────────────────────────────────
# Section 4 — Route Planning Race
# ─────────────────────────────────────────────────────────────────────────────

render_race_section(
    icon="S3",
    title="Stage 3: Route Planning",
    subtitle="Computing shortest paths across the road network",
    results=report.routing_results,
    winner=report.routing_winner,
    color=STAGE_COLORS["routing"],
)

# Network graph
st.markdown("**Road Network - Winning Algorithm Paths**")
render_network_graph(report, data["graph_edges"], data["graph_nodes"])

with st.expander("Planned Routes (winning algorithm)"):
    routes = report.routing_winner.output or {}
    if routes:
        rows = []
        for key, (dist, path) in routes.items():
            rows.append({
                "Route":    key,
                "Path":     " → ".join(path),
                "Dist (km)": round(dist, 1),
            })
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
    else:
        st.info("No routes computed (check if graph data is loaded).")


# ─────────────────────────────────────────────────────────────────────────────
# Section 5 — Team Assignment Race
# ─────────────────────────────────────────────────────────────────────────────

render_race_section(
    icon="S4",
    title="Stage 4: Team Assignment",
    subtitle=f"Matching rescue teams to requests within budget {budget} units",
    results=report.assignment_results,
    winner=report.assignment_winner,
    color=STAGE_COLORS["assignment"],
)

with st.expander("Team Assignments (winning algorithm)"):
    assign_map = report.assignment_winner.output or {}
    if assign_map:
        teams_by_id = {t["id"]: t["name"] for t in data["teams"]}
        rows = [{"Request ID": rid, "Team ID": tid, "Team Name": teams_by_id.get(tid, tid)}
                for rid, tid in assign_map.items()]
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
    else:
        st.warning("No assignments found within budget.")


# ─────────────────────────────────────────────────────────────────────────────
# Section 6 — Final Dispatch Plan
# ─────────────────────────────────────────────────────────────────────────────

st.markdown(f"""
<div class="stage-header" style="border-left-color: #2563eb;">
  <span class="stage-icon">FINAL</span>
  <div>
    <div class="stage-title">Final Dispatch Plan</div>
    <div class="stage-subtitle">Assembled from the winning algorithm of each stage</div>
  </div>
</div>
""", unsafe_allow_html=True)

if report.dispatch_rows:
    rows = []
    for row in report.dispatch_rows:
        resource_names = ", ".join(
            getattr(r, "name", "") for r in (row.resources or [])[:3]
        )
        if len(row.resources or []) > 3:
            resource_names += f" +{len(row.resources)-3} more"

        rows.append({
            "#":            row.rank,
            "Request":      row.request_id,
            "Location":     row.location,
            "Severity":     row.severity,
            "People":       row.people,
            "P-Score":      round(row.priority_score, 2),
            "Team":         row.team_id or "UNASSIGNED",
            "Team Name":    row.team_name or "—",
            "Route":        " → ".join(row.route) if row.route else "—",
            "Dist (km)":    round(row.distance_km, 1),
            "Resources":    resource_names,
            "Res Value":    round(row.resource_value, 0),
            "A-Score":      round(row.assignment_score, 2),
        })

    df_dispatch = pd.DataFrame(rows)
    st.dataframe(df_dispatch, use_container_width=True, hide_index=True, height=320)
else:
    st.info("No dispatch rows available for this run.")

# Winner summary expander
with st.expander("Why Each Algorithm Won"):
    winner_rows = []
    stages = [
        ("Prioritization", report.prioritization_winner, report.prioritization_results),
        ("Allocation",     report.allocation_winner,     report.allocation_results),
        ("Routing",        report.routing_winner,        report.routing_results),
        ("Assignment",     report.assignment_winner,     report.assignment_results),
    ]
    for stage_name, winner, all_results in stages:
        if winner is None:
            continue
        others = [r for r in all_results if r.algorithm_name != winner.algorithm_name]
        reason_parts = []
        if others:
            avg_other_quality = sum(r.quality_score for r in others) / len(others)
            avg_other_time    = sum(r.exec_time_ms  for r in others) / len(others)
            q_diff = winner.quality_score - avg_other_quality
            t_diff = winner.exec_time_ms  - avg_other_time
            if abs(q_diff) > 0.01:
                direction = "higher" if not winner.lower_quality_is_better else "lower"
                if (q_diff > 0 and not winner.lower_quality_is_better) or \
                   (q_diff < 0 and winner.lower_quality_is_better):
                    reason_parts.append(f"**{abs(q_diff):.2f} {direction}** quality score than average")
                else:
                    reason_parts.append(f"comparable quality score")
            if t_diff < 0:
                reason_parts.append(f"**{abs(t_diff):.3f} ms faster**")
        reason = (", ".join(reason_parts) + ".") if reason_parts else "Best combined composite score."

        winner_rows.append({
            "Stage":           stage_name,
            "Winner":          winner.algorithm_name,
            "Composite Score": f"{winner.composite_score:.4f}",
            "Quality":         f"{winner.quality_score:.2f}",
            "Time (ms)":       f"{winner.exec_time_ms:.3f}",
            "Memory (KB)":     f"{winner.memory_kb:.2f}",
            "Why":             reason,
        })

    if winner_rows:
        st.dataframe(pd.DataFrame(winner_rows), use_container_width=True, hide_index=True)
    else:
        st.info("Winner summary is unavailable for the current run.")

st.markdown("---")
st.markdown(
    '<div class="info-box" style="text-align:center;">AgentRelief Algorithm Arena · '
    'Built for DAA Mini Project — Algorithms: Greedy · HeapSort · TimSort · '
    'Fractional Knapsack · 0/1 DP · Dijkstra · Bellman-Ford · A* · Backtracking · Branch &amp; Bound</div>',
    unsafe_allow_html=True,
)
