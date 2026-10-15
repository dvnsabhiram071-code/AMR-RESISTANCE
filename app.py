"""
AMR Sentinel - Core Application Entry Point (app.py)
Provides the Landing Page (Screenshot 1), Two-Column Login Page (Screenshot 2),
Mandatory First-Login Password Change Flow, and Role-Based Overview Dashboard.
"""
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import time

from src.ui_helpers import (
    initialize_session_state,
    render_header,
    render_sidebar_filters,
    render_sidebar_auth,
    get_current_user,
    is_authenticated,
    PANEL_BG,
    ACCENT_TEAL,
    BORDER_DARK,
    TEXT_MUTED,
)
from src.metrics import calculate_resistance_rate, compute_grouped_summary, build_antibiogram_matrix
from src.alerts import detect_alerts_from_dataframe
from src.auth import (
    authenticate_user,
    change_user_password,
    validate_password_policy,
    ROLE_SYSTEM_ADMIN,
    ROLE_SURVEILLANCE_ANALYST,
    ROLE_READ_ONLY_VIEWER,
    ROLE_NAMES
)

st.set_page_config(
    page_title="AMR Sentinel · Antimicrobial Resistance Surveillance",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

initialize_session_state()

# Synchronize Auth Navigation View: 'landing', 'login', 'change_password', 'dashboard'
query_param_page = st.query_params.get("page") or st.query_params.get("view")
if query_param_page in ["landing", "login", "change_password", "dashboard"]:
    if st.session_state.get("_active_query_page") != query_param_page:
        st.session_state.auth_view = query_param_page
        st.session_state._active_query_page = query_param_page
elif "auth_view" not in st.session_state:
    st.session_state.auth_view = "landing"


# ========================================================
# 1. LANDING PAGE — Matching Reference Screenshot 1
# ========================================================
def render_landing_page():
    st.markdown(
        """
        <style>
            /* Landing Page Light Theme Styling */
            .stApp {
                background: radial-gradient(circle at 10% 20%, #E0F2FE 0%, #F0F9FF 30%, #F8FAFC 70%) !important;
                color: #0F172A !important;
            }
            .landing-pill {
                display: inline-block;
                padding: 6px 14px;
                background: rgba(14, 165, 233, 0.1);
                border: 1px solid rgba(14, 165, 233, 0.3);
                border-radius: 20px;
                color: #0284C7;
                font-size: 12px;
                font-weight: 700;
                margin-bottom: 14px;
            }
            .hero-h1 {
                font-size: 3.2rem;
                font-weight: 800;
                line-height: 1.12;
                letter-spacing: -1.2px;
                color: #0F172A;
                margin-bottom: 16px;
            }
            .hero-cyan {
                color: #06B6D4;
                background: linear-gradient(135deg, #0284C7 0%, #06B6D4 100%);
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
            }
            .hero-desc {
                font-size: 1.05rem;
                line-height: 1.6;
                color: #64748B;
                margin-bottom: 24px;
            }
            .feat-card-light {
                background: #FFFFFF;
                border: 1px solid #E2E8F0;
                border-radius: 12px;
                padding: 16px;
                box-shadow: 0 2px 8px rgba(0,0,0,0.04);
            }
            .feat-card-light h4 {
                color: #0F172A !important;
                font-size: 0.95rem;
                font-weight: 700;
                margin: 6px 0 2px 0;
            }
            .feat-card-light p {
                color: #64748B;
                font-size: 0.8rem;
                line-height: 1.4;
                margin: 0;
            }
            .stat-strip-box {
                background: #FFFFFF;
                border-top: 1px solid #E2E8F0;
                border-radius: 12px;
                padding: 20px;
                margin-top: 32px;
                box-shadow: 0 4px 12px rgba(0,0,0,0.03);
            }
            .preview-dark-box {
                background: #0B1224;
                border: 1px solid #1E2D5A;
                border-radius: 16px;
                padding: 18px;
                color: #FFFFFF;
                box-shadow: 0 20px 40px rgba(11, 18, 36, 0.4);
            }
        </style>
        """,
        unsafe_allow_html=True
    )

    # Top Light Header
    h_col1, h_col2, h_col3 = st.columns([1.5, 3, 1])
    with h_col1:
        st.markdown(
            """
            <div style="display:flex; align-items:center; gap:10px;">
                <div style="width:38px; height:38px; border-radius:10px; background:linear-gradient(135deg, #0284C7, #0369A1); display:flex; align-items:center; justify-content:center; color:#FFF; font-size:18px;">🛡️</div>
                <div>
                    <strong style="font-size:1.15rem; color:#0F172A; display:block; line-height:1.1;">AMR Sentinel</strong>
                    <span style="font-size:0.7rem; color:#0284C7; font-weight:600;">Antimicrobial Resistance Surveillance</span>
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )
    with h_col2:
        st.markdown(
            """
            <div style="display:flex; justify-content:center; gap:24px; font-size:0.88rem; font-weight:600; color:#475569; padding-top:10px;">
                <span style="color:#0284C7; border-bottom:2px solid #0284C7; padding-bottom:4px;">Overview</span>
                <span>Geographic Surveillance</span>
                <span>Resistance Trends</span>
                <span>Alert Center</span>
                <span>AI Copilot</span>
                <span>Data Quality</span>
            </div>
            """,
            unsafe_allow_html=True
        )
    with h_col3:
        if st.button("👤 Sign In", key="landing_top_signin_btn", use_container_width=True):
            st.query_params["page"] = "login"
            st.session_state.auth_view = "login"
            st.rerun()

    st.markdown("<div style='height:24px;'></div>", unsafe_allow_html=True)

    # Hero Row
    hero_left, hero_right = st.columns([1.05, 1.25], gap="large")

    with hero_left:
        st.markdown(
            """
            <div class="landing-pill">Smarter Surveillance. Healthier Tomorrows.</div>
            <div class="hero-h1">
                Antimicrobial<br>
                Resistance<br>
                <span class="hero-cyan">Intelligence,</span><br>
                in Real Time
            </div>
            <div class="hero-desc">
                Real-time insights, data-driven alerts and AI-powered analysis to help public health teams detect, track and respond to antimicrobial resistance across regions and healthcare systems.
            </div>
            """,
            unsafe_allow_html=True
        )

        cta1, cta2 = st.columns([1.3, 1])
        with cta1:
            if st.button("📊 Explore Surveillance →", key="landing_explore_btn", type="primary", use_container_width=True):
                # Demo login as Surveillance Analyst
                st.session_state.authenticated_user = {
                    "email": "analyst@amrsentinel.org",
                    "name": "Dr. Priya Sharma",
                    "role": ROLE_SURVEILLANCE_ANALYST,
                    "must_change_password": False
                }
                st.query_params["page"] = "dashboard"
                st.session_state.auth_view = "dashboard"
                st.rerun()

        with cta2:
            if st.button("Sign In", key="landing_hero_signin_btn", use_container_width=True):
                st.query_params["page"] = "login"
                st.session_state.auth_view = "login"
                st.rerun()

        st.markdown("<div style='height:16px;'></div>", unsafe_allow_html=True)

        # 3 Feature Cards
        f1, f2, f3 = st.columns(3)
        with f1:
            st.markdown(
                """
                <div class="feat-card-light">
                    <div style="font-size:18px;">🌊</div>
                    <h4>Real-time Monitoring</h4>
                    <p>Early signal detection across regions</p>
                </div>
                """,
                unsafe_allow_html=True
            )
        with f2:
            st.markdown(
                """
                <div class="feat-card-light">
                    <div style="font-size:18px;">📍</div>
                    <h4>Geographic Insights</h4>
                    <p>Region-wise analysis and hotspot detection</p>
                </div>
                """,
                unsafe_allow_html=True
            )
        with f3:
            st.markdown(
                """
                <div class="feat-card-light">
                    <div style="font-size:18px;">🤖</div>
                    <h4>AI-Powered Intel</h4>
                    <p>Evidence-based recommendations</p>
                </div>
                """,
                unsafe_allow_html=True
            )

    with hero_right:
        # Live Styled Dashboard Preview Card (Screenshot 1 Right)
        st.markdown(
            """
            <div class="preview-dark-box">
                <div style="display:flex; justify-content:space-between; align-items:center; border-bottom:1px solid #1E2D5A; padding-bottom:8px; margin-bottom:12px;">
                    <div style="display:flex; align-items:center; gap:6px; font-weight:700; font-size:0.85rem; color:#00E5FF;">
                        <span>🛡️</span> AMR Sentinel Preview
                    </div>
                    <div style="font-size:0.75rem; color:#94A3B8;">
                        📅 Last 30 days · 👤 JS
                    </div>
                </div>

                <div style="display:grid; grid-template-columns:repeat(4, 1fr); gap:8px; margin-bottom:12px;">
                    <div style="background:#111C38; border:1px solid #1E2D5A; border-radius:6px; padding:6px 8px;">
                        <div style="font-size:0.65rem; color:#94A3B8;">Total Records</div>
                        <div style="font-size:1rem; font-weight:800; color:#FFF;">2,000 <span style="font-size:0.65rem; color:#10B981;">▲12%</span></div>
                    </div>
                    <div style="background:#111C38; border:1px solid #1E2D5A; border-radius:6px; padding:6px 8px;">
                        <div style="font-size:0.65rem; color:#94A3B8;">Organisms</div>
                        <div style="font-size:1rem; font-weight:800; color:#FFF;">28 <span style="font-size:0.65rem; color:#10B981;">▲8%</span></div>
                    </div>
                    <div style="background:#111C38; border:1px solid #1E2D5A; border-radius:6px; padding:6px 8px;">
                        <div style="font-size:0.65rem; color:#94A3B8;">Active Alerts</div>
                        <div style="font-size:1rem; font-weight:800; color:#FFF;">12 <span style="font-size:0.65rem; color:#EF4444;">▲3</span></div>
                    </div>
                    <div style="background:#111C38; border:1px solid #1E2D5A; border-radius:6px; padding:6px 8px;">
                        <div style="font-size:0.65rem; color:#94A3B8;">Sentinel Sites</div>
                        <div style="font-size:1rem; font-weight:800; color:#FFF;">48 <span style="font-size:0.65rem; color:#10B981;">▲9%</span></div>
                    </div>
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )

        # Interactive Trend Preview inside Card
        months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
        ecoli = [28, 30, 32, 38, 37, 42, 40, 44, 43, 48, 50, 52]
        kpneumo = [20, 22, 23, 26, 28, 31, 30, 34, 37, 39, 41, 45]

        fig_prev = go.Figure()
        fig_prev.add_trace(go.Scatter(x=months, y=ecoli, name="E. coli", line=dict(color="#00E5FF", width=2.5)))
        fig_prev.add_trace(go.Scatter(x=months, y=kpneumo, name="K. pneumoniae", line=dict(color="#A855F7", width=2.5)))
        fig_prev.update_layout(
            paper_bgcolor="#0B1224",
            plot_bgcolor="#0B1224",
            margin=dict(l=10, r=10, t=10, b=10),
            height=200,
            yaxis=dict(range=[0, 60], gridcolor="#1E2D5A", title="Rate (%)"),
            xaxis=dict(gridcolor="#1E2D5A"),
            font=dict(color="#94A3B8", size=9),
            legend=dict(orientation="h", y=1.1, x=0.2)
        )
        st.plotly_chart(fig_prev, use_container_width=True)

        st.markdown(
            """
            <div style="text-align:center; margin-top:8px;">
                <span style="display:inline-flex; align-items:center; gap:6px; padding:4px 12px; background:#FFFFFF; border:1px solid #CBD5E1; border-radius:20px; font-size:0.75rem; color:#0284C7; font-weight:600; box-shadow:0 2px 6px rgba(0,0,0,0.05);">
                    🛡️ Synthetic demo data · non-diagnostic ℹ️
                </span>
            </div>
            """,
            unsafe_allow_html=True
        )

    # Bottom Statistics Strip
    st.markdown(
        """
        <div class="stat-strip-box">
            <div style="display:grid; grid-template-columns:repeat(4, 1fr); gap:20px;">
                <div style="display:flex; align-items:center; gap:12px;">
                    <div style="width:42px; height:42px; border-radius:50%; background:#EFF6FF; display:flex; align-items:center; justify-content:center; color:#0284C7; font-size:20px;">🗄️</div>
                    <div>
                        <strong style="font-size:0.95rem; color:#0F172A; display:block;">2,000 verified records ℹ️</strong>
                        <span style="font-size:0.75rem; color:#64748B;">Example data for product demonstration</span>
                    </div>
                </div>
                <div style="display:flex; align-items:center; gap:12px;">
                    <div style="width:42px; height:42px; border-radius:50%; background:#EFF6FF; display:flex; align-items:center; justify-content:center; color:#0284C7; font-size:20px;">🌐</div>
                    <div>
                        <strong style="font-size:0.95rem; color:#0F172A; display:block;">28 organisms monitored</strong>
                        <span style="font-size:0.75rem; color:#64748B;">across sentinel sites</span>
                    </div>
                </div>
                <div style="display:flex; align-items:center; gap:12px;">
                    <div style="width:42px; height:42px; border-radius:50%; background:#EFF6FF; display:flex; align-items:center; justify-content:center; color:#0284C7; font-size:20px;">🏥</div>
                    <div>
                        <strong style="font-size:0.95rem; color:#0F172A; display:block;">48 healthcare sites</strong>
                        <span style="font-size:0.75rem; color:#64748B;">in sample dataset</span>
                    </div>
                </div>
                <div style="display:flex; align-items:center; gap:12px;">
                    <div style="width:42px; height:42px; border-radius:50%; background:#EFF6FF; display:flex; align-items:center; justify-content:center; color:#0284C7; font-size:20px;">📈</div>
                    <div>
                        <strong style="font-size:0.95rem; color:#0F172A; display:block;">Real-time insights</strong>
                        <span style="font-size:0.75rem; color:#64748B;">Track trends, detect hotspots and respond faster</span>
                    </div>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )


# ========================================================
# 2. LOGIN PAGE — Matching Reference Screenshot 2
# ========================================================
def render_login_page():
    st.markdown(
        """
        <style>
            .stApp {
                background: #061124 !important;
                color: #FFFFFF !important;
            }
            .login-left-box {
                background: radial-gradient(circle at 70% 35%, #0B2247 0%, #061226 65%, #040D1C 100%);
                padding: 32px 36px;
                border-radius: 16px;
                border: 1px solid rgba(255, 255, 255, 0.08);
            }
            .login-card-white {
                background: #FFFFFF;
                border-radius: 16px;
                padding: 36px 32px;
                color: #0F172A !important;
                box-shadow: 0 20px 45px rgba(0, 0, 0, 0.35);
            }
            .feat-grid-card {
                background: rgba(11, 26, 54, 0.85);
                border: 1px solid #162B55;
                border-radius: 10px;
                padding: 12px 14px;
                margin-bottom: 10px;
            }
            .feat-grid-card h4 {
                color: #FFFFFF !important;
                font-size: 0.85rem;
                font-weight: 700;
                margin: 0 0 4px 0;
            }
            .feat-grid-card p {
                color: #94A3B8;
                font-size: 0.75rem;
                margin: 0;
                line-height: 1.35;
            }
        </style>
        """,
        unsafe_allow_html=True
    )

    col_l, col_r = st.columns([1.2, 1], gap="large")

    # Left Panel: Dark Navy with 6 Feature Cards
    with col_l:
        st.markdown(
            """
            <div class="login-left-box">
                <div style="display:flex; align-items:center; gap:10px; margin-bottom:24px;">
                    <div style="width:42px; height:42px; border-radius:10px; background:linear-gradient(135deg, #0284C7, #00E5FF); display:flex; align-items:center; justify-content:center; color:#FFF; font-size:20px; box-shadow:0 0 16px rgba(0,229,255,0.4);">🛡️</div>
                    <div>
                        <strong style="font-size:1.25rem; color:#FFF; display:block; line-height:1.1;">AMR Sentinel</strong>
                        <span style="font-size:0.75rem; color:#00E5FF; font-weight:600;">Antimicrobial Resistance Surveillance & Early Warning</span>
                    </div>
                </div>

                <div style="font-size:0.75rem; font-weight:700; letter-spacing:1px; color:#38BDF8; text-transform:uppercase; margin-bottom:8px;">
                    SMARTER SURVEILLANCE. HEALTHIER TOMORROWS.
                </div>

                <div style="font-size:2.4rem; font-weight:800; line-height:1.15; margin-bottom:14px; color:#FFFFFF;">
                    See Resistance Earlier.<br>
                    <span style="color:#00E5FF;">Respond with Evidence.</span>
                </div>

                <p style="font-size:0.9rem; color:#94A3B8; line-height:1.6; margin-bottom:24px;">
                    AI-powered surveillance, real-time alerts and actionable insights for a safer, healthier tomorrow. Track resistance patterns, monitor geographic trends, and get AI-assisted analysis for faster, smarter decisions.
                </p>
            </div>
            """,
            unsafe_allow_html=True
        )

        st.markdown("<div style='height:14px;'></div>", unsafe_allow_html=True)

        # 6 Feature Cards Grid
        fc1, fc2 = st.columns(2)
        with fc1:
            st.markdown(
                """
                <div class="feat-grid-card">
                    <h4>📍 Geographic Surveillance →</h4>
                    <p>Monitor resistance patterns across regions and healthcare systems.</p>
                </div>
                <div class="feat-grid-card">
                    <h4>🔔 Alert Center →</h4>
                    <p>Get early warnings and investigate unusual increases.</p>
                </div>
                <div class="feat-grid-card">
                    <h4>🗄️ Data Quality →</h4>
                    <p>Validate, enrich and ensure reliable data sources.</p>
                </div>
                """,
                unsafe_allow_html=True
            )
        with fc2:
            st.markdown(
                """
                <div class="feat-grid-card">
                    <h4>📈 Resistance Trends →</h4>
                    <p>Track temporal trends and identify emerging patterns.</p>
                </div>
                <div class="feat-grid-card">
                    <h4>🤖 AI Copilot →</h4>
                    <p>Ask questions, get insights, and analyze your data.</p>
                </div>
                <div class="feat-grid-card">
                    <h4>📑 Intelligence Briefs →</h4>
                    <p>Generate concise reports and actionable summaries.</p>
                </div>
                """,
                unsafe_allow_html=True
            )

        st.markdown(
            """
            <div style="margin-top:16px;">
                <span style="display:inline-flex; align-items:center; gap:6px; padding:6px 14px; background:rgba(14,165,233,0.1); border:1px solid rgba(0,229,255,0.3); border-radius:20px; color:#00E5FF; font-size:0.75rem; font-weight:600;">
                    🧪 Synthetic Demo Data · Non-Diagnostic
                </span>
            </div>
            """,
            unsafe_allow_html=True
        )

    # Right Panel: White Rounded Card
    with col_r:
        st.markdown(
            """
            <div class="login-card-white">
                <div style="display:flex; align-items:center; gap:8px; margin-bottom:12px;">
                    <div style="width:32px; height:32px; border-radius:8px; background:linear-gradient(135deg, #0284C7, #00B4D8); display:flex; align-items:center; justify-content:center; color:#FFF; font-size:16px;">🛡️</div>
                    <div>
                        <strong style="font-size:0.95rem; color:#0F172A; display:block;">AMR Sentinel</strong>
                        <span style="font-size:0.65rem; color:#0284C7; font-weight:600;">Antimicrobial Resistance Surveillance & Early Warning</span>
                    </div>
                </div>

                <h3 style="font-size:1.6rem; font-weight:800; color:#0F172A; margin:0 0 4px 0;">Welcome Back</h3>
                <p style="font-size:0.82rem; color:#64748B; margin:0 0 18px 0;">Sign in to access the surveillance dashboard and analytics platform.</p>
            </div>
            """,
            unsafe_allow_html=True
        )

        with st.form("login_form"):
            email_input = st.text_input("Email Address", value="dvnsabhiram071@gmail.com")
            pwd_input = st.text_input("Password", value="Amr@135", type="password")

            col_sub1, col_sub2 = st.columns([1, 1])
            with col_sub1:
                remember = st.checkbox("Remember me", value=True)
            with col_sub2:
                st.markdown("<div style='text-align:right; font-size:0.8rem; color:#0284C7; padding-top:4px;'>Forgot password?</div>", unsafe_allow_html=True)

            btn_submit = st.form_submit_button("Sign In →", type="primary", use_container_width=True)

            if btn_submit:
                success, user_dict, msg = authenticate_user(email_input, pwd_input)
                if not success:
                    st.error(f"❌ {msg}")
                else:
                    st.session_state.authenticated_user = user_dict
                    if user_dict.get("must_change_password"):
                        st.query_params["page"] = "change_password"
                        st.session_state.auth_view = "change_password"
                        st.session_state.temp_pwd_cache = pwd_input
                        st.rerun()
                    else:
                        st.query_params["page"] = "dashboard"
                        st.session_state.auth_view = "dashboard"
                        st.rerun()

        st.markdown("<div style='text-align:center; color:#94A3B8; font-size:0.75rem; margin:10px 0;'>OR</div>", unsafe_allow_html=True)

        if st.button("👤 Try Demo Access (Surveillance Analyst)", key="login_demo_btn", use_container_width=True):
            st.session_state.authenticated_user = {
                "email": "analyst@amrsentinel.org",
                "name": "Dr. Priya Sharma",
                "role": ROLE_SURVEILLANCE_ANALYST,
                "must_change_password": False
            }
            st.query_params["page"] = "dashboard"
            st.session_state.auth_view = "dashboard"
            st.rerun()

        if st.button("← Back to Home", key="login_back_home_btn", use_container_width=True):
            st.query_params["page"] = "landing"
            st.session_state.auth_view = "landing"
            st.rerun()

        st.markdown(
            """
            <div style="text-align:center; color:#94A3B8; font-size:0.72rem; margin-top:16px;">
                🔒 Secure Access · Role-Based Permissions · Protected System
            </div>
            """,
            unsafe_allow_html=True
        )


# ========================================================
# 3. MANDATORY PASSWORD CHANGE — First Login Flow
# ========================================================
def render_password_change_page():
    user = get_current_user()
    if not user:
        st.session_state.auth_view = "login"
        st.rerun()

    st.markdown(
        """
        <div style="max-width:540px; margin:40px auto; background:#FFFFFF; border-radius:16px; padding:36px; box-shadow:0 20px 45px rgba(0,0,0,0.3); color:#0F172A;">
            <div style="display:flex; align-items:center; gap:8px; margin-bottom:12px;">
                <span style="font-size:24px;">🛡️</span>
                <div>
                    <strong style="font-size:1.1rem; color:#0F172A; display:block;">AMR Sentinel Security Policy</strong>
                    <span style="font-size:0.75rem; color:#0284C7; font-weight:600;">First-Login Administrative Credential Replacement</span>
                </div>
            </div>
            <h3 style="font-size:1.5rem; font-weight:800; color:#0F172A; margin:10px 0 6px 0;">Set Permanent Password</h3>
            <p style="font-size:0.85rem; color:#64748B; margin-bottom:18px;">
                You are logging in with a temporary administrative password (<strong>Amr@135</strong>).
                Security policy mandates setting a permanent password before surveillance dashboard access is permitted.
            </p>
        </div>
        """,
        unsafe_allow_html=True
    )

    col_wrap1, col_wrap2, col_wrap3 = st.columns([1, 2, 1])
    with col_wrap2:
        with st.form("pwd_change_form"):
            curr_pwd = st.text_input("Current Temporary Password", value=st.session_state.get("temp_pwd_cache", "Amr@135"), type="password")
            new_pwd = st.text_input("New Permanent Password", placeholder="Minimum 12 characters", type="password")
            conf_pwd = st.text_input("Confirm New Password", placeholder="Re-type new password", type="password")

            st.markdown(
                """
                <div style="background:#F8FAFC; border:1px solid #E2E8F0; border-radius:8px; padding:12px; font-size:0.78rem; color:#475569; margin:10px 0;">
                    <strong style="color:#0F172A; display:block; margin-bottom:4px;">Password Policy Requirements:</strong>
                    • Minimum 12 characters<br>
                    • At least one uppercase letter (A-Z)<br>
                    • At least one lowercase letter (a-z)<br>
                    • At least one number (0-9)<br>
                    • At least one special symbol (!@#$%^&*...)
                </div>
                """,
                unsafe_allow_html=True
            )

            btn_change = st.form_submit_button("Update Password & Enter Dashboard →", type="primary", use_container_width=True)

            if btn_change:
                success, msg = change_user_password(user["email"], curr_pwd, new_pwd, conf_pwd)
                if not success:
                    st.error(f"❌ {msg}")
                else:
                    st.success("✅ Permanent password set successfully! Redirecting to System Administrator dashboard...")
                    user["must_change_password"] = False
                    st.session_state.authenticated_user = user
                    st.session_state.auth_view = "dashboard"
                    time.sleep(1)
                    st.rerun()


# ========================================================
# 4. OVERVIEW DASHBOARD — Full Preserved Functionality
# ========================================================
def render_overview_dashboard():
    render_header("Overview Dashboard", "Real-time antimicrobial susceptibility analytics and signal monitoring")

    # Sidebar Filters & Authentication Profile
    raw_df = st.session_state.active_df
    filtered_df, filter_meta = render_sidebar_filters(raw_df)

    if filtered_df.empty:
        st.warning("⚠️ No records match the active filter criteria. Please adjust your date range or filters.")
        st.stop()

    # 1. KPI Calculations
    kpi_res = calculate_resistance_rate(filtered_df, min_denominator=30)
    active_alerts = detect_alerts_from_dataframe(filtered_df)
    crit_alerts = [a for a in active_alerts if a.severity in ["Critical", "High"]]

    if crit_alerts:
        top_c = crit_alerts[0]
        st.markdown(
            f"""
            <div style="background: rgba(239, 68, 68, 0.15); border: 2px solid #EF4444; border-radius: 8px; padding: 12px 16px; margin-bottom: 16px; display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 8px;">
                <div style="display:flex; align-items:center; gap:8px;">
                    <span style="font-size:20px;">🚨</span>
                    <div>
                        <strong style="color:#FFF;">HIGH-PRIORITY SURVEILLANCE ALARM: {top_c.id}</strong> —
                        <span style="color:#CBD5E1;">{top_c.organism} vs {top_c.antibiotic} ({top_c.department}) observed at <span style="color:#EF4444; font-weight:700;">{top_c.current_rate:.1f}%</span> (Shift: {top_c.pct_point_change:+.1f} pp, N={top_c.current_tested})</span>
                    </div>
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.markdown(
            f"""
            <div class="amr-card">
                <div class="kpi-title">Eligible Tested Isolates</div>
                <div class="kpi-val">{kpi_res.valid_tested:,}</div>
                <div class="kpi-sub">Total verified AST records</div>
            </div>
            """,
            unsafe_allow_html=True
        )

    with col2:
        rate_display = f"{kpi_res.resistance_rate:.1f}%" if kpi_res.resistance_rate is not None else "N/A"
        denom_text = f"Resistant: {kpi_res.resistant_count} / N={kpi_res.valid_tested}"
        st.markdown(
            f"""
            <div class="amr-card">
                <div class="kpi-title">Overall Resistance Rate</div>
                <div class="kpi-val">{rate_display}</div>
                <div class="kpi-sub">{denom_text}</div>
            </div>
            """,
            unsafe_allow_html=True
        )

    with col3:
        st.markdown(
            f"""
            <div class="amr-card">
                <div class="kpi-title">Active Signals / Alerts</div>
                <div class="kpi-val">{len(active_alerts)}</div>
                <div class="kpi-sub">Automated rule triggers</div>
            </div>
            """,
            unsafe_allow_html=True
        )

    with col4:
        crit_color = "#EF4444" if len(crit_alerts) > 0 else "#10B981"
        st.markdown(
            f"""
            <div class="amr-card">
                <div class="kpi-title">High & Critical Priority</div>
                <div class="kpi-val" style="color: {crit_color};">{len(crit_alerts)}</div>
                <div class="kpi-sub">Urgent stewardship review</div>
            </div>
            """,
            unsafe_allow_html=True
        )

    st.markdown("---")

    # 2. Charts Row
    chart_col1, chart_col2 = st.columns([1.2, 1])

    with chart_col1:
        st.subheader("📈 Longitudinal Resistance Trend")
        trend_df = filtered_df.copy()
        trend_df["year_month"] = pd.to_datetime(trend_df["test_date"]).dt.to_period("M").astype(str)
        
        monthly_stats = []
        for ym, group in trend_df.groupby("year_month"):
            m_res = calculate_resistance_rate(group)
            monthly_stats.append({
                "Month": ym,
                "Resistance Rate (%)": m_res.resistance_rate,
                "Sample Size (N)": m_res.valid_tested,
            })
        
        m_df = pd.DataFrame(monthly_stats)
        if not m_df.empty:
            fig_trend = go.Figure()
            fig_trend.add_trace(go.Scatter(
                x=m_df["Month"],
                y=m_df["Resistance Rate (%)"],
                mode="lines+markers",
                name="Resistance Rate (%)",
                line=dict(color=ACCENT_TEAL, width=3),
                marker=dict(size=8, color="#FFFFFF"),
                hovertemplate="<b>%{x}</b><br>Rate: %{y:.1f}%<extra></extra>"
            ))
            fig_trend.update_layout(
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(17, 24, 39, 0.7)",
                margin=dict(l=20, r=20, t=20, b=20),
                yaxis=dict(title="Resistance Proportion (%)", gridcolor=BORDER_DARK, range=[0, 100]),
                xaxis=dict(title="Reporting Period", gridcolor=BORDER_DARK),
                font=dict(color="#D1D5DB"),
                height=320,
            )
            st.plotly_chart(fig_trend, use_container_width=True)

    with chart_col2:
        st.subheader("📊 Top Pathogen Resistance Comparison")
        top_orgs = compute_grouped_summary(filtered_df, group_cols=["organism"], min_denominator=10)
        if not top_orgs.empty:
            top_orgs = top_orgs.head(6)
            fig_bar = px.bar(
                top_orgs,
                x="resistance_rate",
                y="organism",
                orientation="h",
                color="resistance_rate",
                color_continuous_scale=["#14B8A6", "#F59E0B", "#EF4444"],
                labels={"resistance_rate": "Resistance Rate (%)", "organism": "Pathogen"},
            )
            fig_bar.update_layout(
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(17, 24, 39, 0.7)",
                margin=dict(l=20, r=20, t=20, b=20),
                xaxis=dict(title="Rate (%)", gridcolor=BORDER_DARK, range=[0, 100]),
                yaxis=dict(autorange="reversed"),
                coloraxis_showscale=False,
                font=dict(color="#D1D5DB"),
                height=320,
            )
            st.plotly_chart(fig_bar, use_container_width=True)

    # 3. Antibiogram Heatmap
    st.subheader("🧬 Antibiogram Matrix (Organism × Antimicrobial)")
    rate_mat, count_mat = build_antibiogram_matrix(filtered_df, min_denominator=5)

    if not rate_mat.empty:
        fig_heat = px.imshow(
            rate_mat,
            text_auto=".1f",
            aspect="auto",
            color_continuous_scale=["#14B8A6", "#F59E0B", "#EF4444"],
            labels=dict(x="Antimicrobial Agent", y="Pathogen", color="Resistant %"),
        )
        fig_heat.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(17, 24, 39, 0.7)",
            font=dict(color="#D1D5DB"),
            margin=dict(l=20, r=20, t=20, b=20),
            height=320,
        )
        st.plotly_chart(fig_heat, use_container_width=True)
        st.caption("ℹ️ Cells display calculated resistance proportions (%). Minimum 5 tested isolates required per cell.")
    else:
        st.info("Insufficient overlapping organism and antibiotic pairings for matrix view.")

    st.markdown("---")

    # 4. Active Surveillance Alerts
    st.subheader("🚨 Active Surveillance Signals & Anomaly Detection")

    if not active_alerts:
        st.success("✅ No statistically significant anomalies or threshold breaches detected in the filtered data.")
    else:
        for a in active_alerts:
            sev_class = f"badge-{a.severity.lower()}"
            col_a, col_b = st.columns([4, 1])
            with col_a:
                st.markdown(
                    f"""
                    <div style="background: {PANEL_BG}; border: 1px solid {BORDER_DARK}; border-radius: 6px; padding: 12px 16px; margin-bottom: 8px;">
                        <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 4px;">
                            <span class="{sev_class}">{a.severity.upper()}</span>
                            <strong style="color: #FFFFFF; font-size: 1rem;">{a.title}</strong>
                            <span style="color: {TEXT_MUTED}; font-size: 0.8rem;">({a.id})</span>
                        </div>
                        <div style="color: #D1D5DB; font-size: 0.88rem;">
                            <strong>Trigger Reason:</strong> {a.trigger_reason}
                        </div>
                        <div style="color: {TEXT_MUTED}; font-size: 0.82rem; margin-top: 4px;">
                            Current: <strong style="color: #FFFFFF;">{a.current_rate:.1f}%</strong> (N={a.current_tested}) · 
                            Baseline: <strong style="color: #FFFFFF;">{a.baseline_rate:.1f}%</strong> (N={a.baseline_tested}) · 
                            Shift: <strong style="color: {ACCENT_TEAL};">{a.pct_point_change:+.1f}% pt</strong>
                            {f" · <em style='color:#F59E0B;'>Caveat: {a.caveats}</em>" if a.caveats else ""}
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True
                )
            with col_b:
                if st.button(f"🔍 Investigate {a.id}", key=f"inv_{a.id}", use_container_width=True):
                    st.session_state.selected_alert_id = a.id
                    st.switch_page("pages/2_Alert_Investigation.py")


# ========================================================
# MAIN ROUTER
# ========================================================
user = get_current_user()

if user is not None:
    if user.get("must_change_password"):
        render_password_change_page()
    else:
        render_overview_dashboard()
else:
    if st.session_state.auth_view == "login":
        render_login_page()
    else:
        render_landing_page()
