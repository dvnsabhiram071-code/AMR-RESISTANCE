"""
AMR Sentinel - Scenario Lab & Longitudinal Timeline Replay
"""
import streamlit as st
import pandas as pd
import plotly.express as px

from src.ui_helpers import (
    initialize_session_state,
    render_header,
    require_authentication,
    ACCENT_TEAL,
    BORDER_DARK,
    PANEL_BG,
    TEXT_MUTED
)
from src.scenarios import SCENARIOS, load_scenario_dataset, slice_timeline
from src.alerts import detect_alerts_from_dataframe
from src.metrics import calculate_resistance_rate

st.set_page_config(page_title="AMR Sentinel · Scenario Lab", page_icon="🧪", layout="wide")
initialize_session_state()
require_authentication()
render_header("Scenario Lab & Timeline Replay", "Simulate outbreak trajectories and step through monthly surveillance timelines")

# 1. Scenario Selector
st.subheader("🧬 Select Synthetic Epidemiological Scenario")

scenario_keys = list(SCENARIOS.keys())
scenario_names = [f"{SCENARIOS[k]['name']} — {SCENARIOS[k]['description']}" for k in scenario_keys]

curr_key = st.session_state.get("scenario_key", "sudden_spike")
curr_idx = scenario_keys.index(curr_key) if curr_key in scenario_keys else 0

selected_scen_str = st.selectbox("Choose Benchmark Scenario", scenario_names, index=curr_idx)
selected_scen_key = scenario_keys[scenario_names.index(selected_scen_str)]

col_btn1, col_btn2 = st.columns([1, 4])
with col_btn1:
    if st.button("🔄 Apply Scenario & Recompute", type="primary", use_container_width=True):
        st.session_state.scenario_key = selected_scen_key
        report, s_name = load_scenario_dataset(scenario_key=selected_scen_key)
        st.session_state.validation_report = report
        st.session_state.active_df = report.clean_df
        st.session_state.scenario_name = s_name
        st.session_state.alerts_cache = detect_alerts_from_dataframe(report.clean_df)
        if st.session_state.alerts_cache:
            st.session_state.selected_alert_id = st.session_state.alerts_cache[0].id
        st.success(f"Loaded scenario: {s_name}. All metrics and alerts recomputed!")
        st.rerun()

with col_btn2:
    st.info(f"**Expected Signals for this Scenario:** {SCENARIOS[selected_scen_key]['expected_signals']}")

st.markdown("---")

# 2. Timeline Replay
st.subheader("⏱️ Interactive Surveillance Timeline Replay")
st.markdown("Step forward in time month-by-month to observe how rates evolve and when surveillance rules trigger signals.")

active_df = st.session_state.active_df
if not active_df.empty and "test_date" in active_df:
    all_dates = pd.to_datetime(active_df["test_date"]).sort_values()
    min_date = all_dates.min().strftime("%Y-%m-%d")
    max_date = all_dates.max().strftime("%Y-%m-%d")

    # Generate distinct month cutoff options
    month_cutoffs = sorted(all_dates.dt.to_period("M").astype(str).unique().tolist())
    
    selected_month = st.select_slider(
        "Surveillance Timeline Cutoff",
        options=month_cutoffs,
        value=month_cutoffs[-1],
        help="Slide back in time to simulate surveillance alerts as they would have appeared at that moment."
    )

    # Slice data up to end of selected month
    cutoff_date = (pd.to_datetime(selected_month) + pd.offsets.MonthEnd(1)).strftime("%Y-%m-%d")
    sliced_df = slice_timeline(active_df, cutoff_date)

    # Recompute metrics for this time slice
    kpi_slice = calculate_resistance_rate(sliced_df, min_denominator=15)
    slice_alerts = detect_alerts_from_dataframe(sliced_df)

    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown(
            f"""
            <div class="amr-card">
                <div class="kpi-title">Records Accumulated to {selected_month}</div>
                <div class="kpi-val">{kpi_slice.valid_tested:,}</div>
                <div class="kpi-sub">Total verified AST records</div>
            </div>
            """,
            unsafe_allow_html=True
        )
    with col2:
        r_str = f"{kpi_slice.resistance_rate:.1f}%" if kpi_slice.resistance_rate is not None else "N/A"
        st.markdown(
            f"""
            <div class="amr-card">
                <div class="kpi-title">Calculated Resistance to {selected_month}</div>
                <div class="kpi-val">{r_str}</div>
                <div class="kpi-sub">Resistant: {kpi_slice.resistant_count} / Tested: {kpi_slice.valid_tested}</div>
            </div>
            """,
            unsafe_allow_html=True
        )
    with col3:
        st.markdown(
            f"""
            <div class="amr-card">
                <div class="kpi-title">Triggered Alerts at {selected_month}</div>
                <div class="kpi-val">{len(slice_alerts)}</div>
                <div class="kpi-sub">Active detection signals</div>
            </div>
            """,
            unsafe_allow_html=True
        )

    # Mini Trend of Sliced Data
    st.markdown(f"#### Trajectory up to {selected_month}")
    sliced_df["ym"] = pd.to_datetime(sliced_df["test_date"]).dt.to_period("M").astype(str)
    slice_trend = []
    for ym, grp in sliced_df.groupby("ym"):
        r = calculate_resistance_rate(grp, min_denominator=1)
        slice_trend.append({"Month": ym, "Rate": r.resistance_rate or 0, "Tested": r.valid_tested})
    
    t_df = pd.DataFrame(slice_trend)
    if not t_df.empty:
        fig = px.line(
            t_df,
            x="Month",
            y="Rate",
            markers=True,
            labels={"Rate": "Resistance Rate (%)"},
            title=f"Evolving Resistance Trajectory up to {selected_month}"
        )
        fig.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(17, 24, 39, 0.7)",
            yaxis=dict(range=[0, 100], gridcolor=BORDER_DARK),
            xaxis=dict(gridcolor=BORDER_DARK),
            font=dict(color="#D1D5DB"),
            height=280,
        )
        st.plotly_chart(fig, use_container_width=True)

    if slice_alerts:
        st.markdown("#### Detected Signals at this Step:")
        for sa in slice_alerts:
            st.markdown(f"- **[{sa.severity}] {sa.title}:** {sa.trigger_reason} (Current Rate: {sa.current_rate:.1f}%)")
    else:
        st.caption("No alerts triggered as of this timeline step.")
