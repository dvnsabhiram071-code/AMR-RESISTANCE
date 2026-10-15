"""
AMR Sentinel - Resistance Trends & Longitudinal Explorer
"""
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from src.ui_helpers import (
    initialize_session_state,
    render_header,
    render_sidebar_filters,
    require_authentication,
    ACCENT_TEAL,
    BORDER_DARK,
    PANEL_BG
)
from src.metrics import calculate_resistance_rate, compute_grouped_summary

st.set_page_config(page_title="AMR Sentinel · Trends", page_icon="📈", layout="wide")
initialize_session_state()
require_authentication()
render_header("Resistance Trends Explorer", "Longitudinal multi-dimensional surveillance across wards, specimens, and bug-drug pairs")

raw_df = st.session_state.active_df
filtered_df, filter_meta = render_sidebar_filters(raw_df)

if filtered_df.empty:
    st.warning("No records match the active filter criteria.")
    st.stop()

# 1. Department Breakdown
st.subheader("🏥 Departmental Susceptibility Breakdown")
dept_summary = compute_grouped_summary(filtered_df, group_cols=["department"], min_denominator=5)

if not dept_summary.empty:
    fig_dept = px.bar(
        dept_summary,
        x="department",
        y="resistance_rate",
        color="resistance_rate",
        color_continuous_scale=["#14B8A6", "#F59E0B", "#EF4444"],
        text="resistance_rate",
        labels={"resistance_rate": "Resistance Rate (%)", "department": "Hospital Unit"},
    )
    fig_dept.update_traces(texttemplate='%{text:.1f}%', textposition='outside')
    fig_dept.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(17, 24, 39, 0.7)",
        yaxis=dict(range=[0, 105], gridcolor=BORDER_DARK),
        xaxis=dict(gridcolor=BORDER_DARK),
        font=dict(color="#D1D5DB"),
        height=340,
    )
    st.plotly_chart(fig_dept, use_container_width=True)

# 2. Specimen Distribution & Monthly Trend by Specimen
col_left, col_right = st.columns(2)

with col_left:
    st.subheader("🧫 Specimen Source Distribution")
    spec_counts = filtered_df["specimen_type"].value_counts().reset_index()
    spec_counts.columns = ["Specimen Type", "Count"]
    fig_pie = px.pie(
        spec_counts,
        names="Specimen Type",
        values="Count",
        color_discrete_sequence=["#14B8A6", "#3B82F6", "#F59E0B", "#EC4899", "#8B5CF6"],
        hole=0.45
    )
    fig_pie.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#D1D5DB"),
        height=320,
        margin=dict(l=10, r=10, t=10, b=10)
    )
    st.plotly_chart(fig_pie, use_container_width=True)

with col_right:
    st.subheader("📅 Longitudinal Organism Resistance")
    filtered_df["year_month"] = pd.to_datetime(filtered_df["test_date"]).dt.to_period("M").astype(str)
    
    # Calculate monthly rates per top organism
    top_orgs = filtered_df["organism"].value_counts().head(3).index.tolist()
    monthly_org_df = filtered_df[filtered_df["organism"].isin(top_orgs)]
    
    rows = []
    for (ym, org), grp in monthly_org_df.groupby(["year_month", "organism"]):
        r = calculate_resistance_rate(grp, min_denominator=5)
        rows.append({"Month": ym, "Organism": org, "Rate": r.resistance_rate})
    
    m_org_summary = pd.DataFrame(rows)
    if not m_org_summary.empty:
        fig_m_org = px.line(
            m_org_summary,
            x="Month",
            y="Rate",
            color="Organism",
            markers=True,
            labels={"Rate": "Resistance Rate (%)"}
        )
        fig_m_org.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(17, 24, 39, 0.7)",
            yaxis=dict(range=[0, 100], gridcolor=BORDER_DARK),
            xaxis=dict(gridcolor=BORDER_DARK),
            font=dict(color="#D1D5DB"),
            height=320,
            margin=dict(l=10, r=10, t=10, b=10)
        )
        st.plotly_chart(fig_m_org, use_container_width=True)

# 3. Detailed Data Table
st.subheader("📋 Granular Surveillance Summary Table")
grouped_detail = compute_grouped_summary(
    filtered_df,
    group_cols=["department", "organism", "antibiotic"],
    min_denominator=1
)
st.dataframe(
    grouped_detail,
    column_config={
        "resistance_rate": st.column_config.NumberColumn("Resistance Rate (%)", format="%.1f%%"),
        "valid_tested": st.column_config.NumberColumn("Tested (N)"),
        "resistant_count": st.column_config.NumberColumn("Resistant (R)"),
        "intermediate_count": st.column_config.NumberColumn("Intermediate (I)"),
        "susceptible_count": st.column_config.NumberColumn("Susceptible (S)"),
        "is_low_volume": st.column_config.CheckboxColumn("Low Volume Caveat"),
    },
    use_container_width=True,
    hide_index=True
)
