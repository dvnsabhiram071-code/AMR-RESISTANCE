"""
AMR Sentinel - Intelligence Brief ("What Changed")
"""
import streamlit as st
import pandas as pd

from src.ui_helpers import (
    initialize_session_state,
    render_header,
    render_sidebar_filters,
    require_authentication,
    ACCENT_TEAL,
    BORDER_DARK,
    PANEL_BG,
    TEXT_MUTED
)
from src.intelligence_brief import generate_intelligence_brief

st.set_page_config(page_title="AMR Sentinel · Intelligence Brief", page_icon="📑", layout="wide")
initialize_session_state()
require_authentication()
render_header("Intelligence Brief · What Changed", "Ranked analysis of the largest observed resistance shifts across facilities and wards")

raw_df = st.session_state.active_df
filtered_df, filter_meta = render_sidebar_filters(raw_df)

if filtered_df.empty:
    st.warning("No records match the active filter criteria.")
    st.stop()

brief_data = generate_intelligence_brief(filtered_df, current_days=60, baseline_days=180, min_denominator=15, top_n=10)
rankings = brief_data.get("rankings", [])
stats = brief_data.get("summary_stats", {})

# Stats cards
c1, c2, c3 = st.columns(3)
with c1:
    st.markdown(
        f"""
        <div class="amr-card">
            <div class="kpi-title">Organism-Drug Pairs Evaluated</div>
            <div class="kpi-val">{stats.get('total_groups_compared', 0)}</div>
            <div class="kpi-sub">Across all wards & units</div>
        </div>
        """,
        unsafe_allow_html=True
    )
with c2:
    st.markdown(
        f"""
        <div class="amr-card">
            <div class="kpi-title">Shifts Exceeding +10% pt</div>
            <div class="kpi-val">{stats.get('shifts_exceeding_10pct', 0)}</div>
            <div class="kpi-sub">Notable upward variations</div>
        </div>
        """,
        unsafe_allow_html=True
    )
with c3:
    st.markdown(
        f"""
        <div class="amr-card">
            <div class="kpi-title">Critical Shifts Exceeding +20% pt</div>
            <div class="kpi-val" style="color: #EF4444;">{stats.get('shifts_exceeding_20pct', 0)}</div>
            <div class="kpi-sub">Surveillance attention recommended</div>
        </div>
        """,
        unsafe_allow_html=True
    )

st.markdown("---")

st.subheader("🏆 Ranked Resistance Shifts (Current vs Baseline Window)")
st.caption(
    f"Current Window: **{stats.get('current_window')}** vs Baseline Window: **{stats.get('baseline_window')}**. "
    "Ranked by absolute percentage-point difference."
)

if not rankings:
    st.info("No comparative shifts found meeting the reporting criteria.")
else:
    for item in rankings:
        badge_style = "color: #10B981; border: 1px solid #10B981;" if item["is_reliable"] else "color: #F59E0B; border: 1px solid #F59E0B;"
        col_rank, col_btn = st.columns([4, 1])
        with col_rank:
            st.markdown(
                f"""
                <div class="amr-card" style="margin-bottom: 10px;">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;">
                        <div>
                            <span style="font-weight: 700; color: {ACCENT_TEAL}; font-size: 1.1rem; margin-right: 8px;">#{item['rank']}</span>
                            <strong style="font-size: 1.1rem; color: #FFFFFF;">{item['organism']}</strong> vs <strong>{item['antibiotic']}</strong>
                            <span style="color: {TEXT_MUTED};">({item['department']})</span>
                        </div>
                        <span style="font-size: 0.75rem; padding: 2px 8px; border-radius: 4px; {badge_style}">
                            {item['confidence']}
                        </span>
                    </div>
                    <div style="font-size: 0.9rem; color: #D1D5DB;">
                        Shift: <strong style="color: {ACCENT_TEAL}; font-size: 1.05rem;">{item['pct_point_change']:+.1f}% pt</strong>
                        (Current: <strong>{item['current_rate']:.1f}%</strong> [R={item['current_resistant']}/N={item['current_tested']}] vs 
                        Baseline: <strong>{item['baseline_rate']:.1f}%</strong> [R={item['baseline_resistant']}/N={item['baseline_tested']}])
                    </div>
                    {f"<div style='color: #F59E0B; font-size: 0.8rem; margin-top: 4px;'>⚠️ Caveat: {item['caveat']}</div>" if item['caveat'] else ""}
                </div>
                """,
                unsafe_allow_html=True
            )
        with col_btn:
            if st.button("🔍 Investigate", key=f"brief_{item['rank']}", use_container_width=True):
                # Look for matching alert
                st.switch_page("pages/2_Alert_Investigation.py")
