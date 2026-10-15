"""
AMR Sentinel - Reports & Reproducibility Export
"""
import streamlit as st
import pandas as pd
from datetime import datetime

from src.ui_helpers import (
    initialize_session_state,
    render_header,
    render_sidebar_filters,
    require_authentication,
    ACCENT_TEAL,
    BORDER_DARK,
    PANEL_BG
)
from src.metrics import calculate_resistance_rate
from src.alerts import detect_alerts_from_dataframe
from src.exports import generate_executive_report_markdown, generate_export_csv

st.set_page_config(page_title="AMR Sentinel · Reports", page_icon="📑", layout="wide")
initialize_session_state()
require_authentication()
render_header("Reports & Export Center", "Download reproducible surveillance audits and filter-synchronized datasets")

raw_df = st.session_state.active_df
filtered_df, filter_meta = render_sidebar_filters(raw_df)

if filtered_df.empty:
    st.warning("No records match the active filter criteria.")
    st.stop()

# Recompute current metrics & alerts
kpi_res = calculate_resistance_rate(filtered_df, min_denominator=15)
alerts = detect_alerts_from_dataframe(filtered_df)

report_md = generate_executive_report_markdown(
    df=filtered_df,
    alerts=alerts,
    filters=filter_meta,
    scenario_name=st.session_state.get("scenario_name", "Synthetic Demo"),
    overall_rate=kpi_res.resistance_rate,
    total_tested=kpi_res.valid_tested,
)

# 1. Export Buttons
col_exp1, col_exp2 = st.columns(2)

with col_exp1:
    st.download_button(
        label="📥 Download Executive Surveillance Report (.md / .txt)",
        data=report_md,
        file_name=f"AMR_Sentinel_Surveillance_Report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md",
        mime="text/markdown",
        type="primary",
        use_container_width=True
    )

with col_exp2:
    csv_bytes = generate_export_csv(filtered_df, filter_meta)
    st.download_button(
        label="📊 Export Filtered AST Records (.csv)",
        data=csv_bytes,
        file_name=f"AMR_Sentinel_Filtered_Data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
        mime="text/csv",
        use_container_width=True
    )

st.markdown("---")

# 2. In-App Report Preview
st.subheader("📄 Live Report Preview")
st.markdown(
    f"""
    <div class="amr-card" style="padding: 24px; font-size: 0.95rem; line-height: 1.7;">
    """,
    unsafe_allow_html=True
)
st.markdown(report_md)
st.markdown("</div>", unsafe_allow_html=True)
