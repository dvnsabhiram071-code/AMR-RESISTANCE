# 🛡️ AMR SENTINEL
### AI-Powered Antimicrobial Resistance Intelligence & Decision-Support Platform

[![Python](https://img.shields.io/badge/Python-3.11%2B-3776AB.svg?logo=python&logoColor=white)](https://www.python.org)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.40%2B-FF4B4B.svg?logo=streamlit&logoColor=white)](https://streamlit.io)
[![Groq](https://img.shields.io/badge/Groq-LPU%20Accelerated-F05A28.svg)](https://groq.com)
[![Pytest](https://img.shields.io/badge/pytest-Passing-0A9EDC.svg?logo=pytest&logoColor=white)](https://pytest.org)

> **Important Clinical Notice:**  
> This platform is an epidemiological surveillance and decision-support prototype. It operates on synthetic demonstration data and does **not** diagnose patients, prescribe antimicrobial therapies, or replace clinical microbiology judgment.

---

## 🌟 Key Capabilities

1. **Deterministic Analytics Engine:**
   - Evaluates pure, verifiable mathematical rates:
     $$\text{Resistance Proportion} = \frac{\text{Resistant Isolates}}{\text{Eligible Isolates Tested}} \times 100$$
   - Enforces denominator rules: Zero tests returns `N/A`, never `0%`.
   - Low-volume caveats flagged automatically when sample sizes $N < 30$.

2. **Organism × Antimicrobial Antibiograms:**
   - Dynamic cross-ward resistance matrices across all tested pathogens and antibiotics.

3. **Configurable Alert & Anomaly Engine:**
   - Multi-threshold detection (Critical, High, Moderate, Watch).
   - Priority pathogen pairing monitoring (e.g. Carbapenem-Resistant *Klebsiella pneumoniae*, MRSA, VRE).

4. **Groq LPU-Accelerated AI Copilot:**
   - Powered by ultra-fast Groq inference (`openai/gpt-oss-120b`).
   - Strictly bounded to structured numerical evidence (zero hallucination).
   - Robust offline/no-key fallback mode ensuring 100% platform uptime.

5. **Closed-Loop Clinical Triage & Audit Trail:**
   - Track alert decisions: `Active`, `Under Review`, `Escalated`, `Resolved`.
   - Record physician/epidemiologist notes and verification steps.

6. **Scenario Lab & Timeline Replay:**
   - Toggle instantly between 4 epidemiological scenarios: *Stable Baseline*, *Gradual Rise*, *Sudden Spike*, and *Low-Volume Sparse Data*.
   - Monthly timeline replay slider simulating chronological outbreak evolution.

7. **Data Quality, Quarantine & Reports:**
   - Multi-stage CSV validation with quarantine logs explaining excluded rows.
   - 1-click Markdown surveillance report & CSV exports with reproducibility metadata.

---

## 🚀 Quick Start Guide

### 1. Installation & Environment Setup
Clone or navigate to the repository directory:
```powershell
cd amr-sentinel
```

Install dependencies:
```powershell
pip install -r requirements.txt
```

### 2. Configure Environment Variables
Copy `.env.example` to `.env`:
```powershell
cp .env.example .env
```
Ensure your `GROQ_API_KEY` is specified in `.env`.

### 3. Run Automated Tests
Verify all 27 unit, analytical, security, and routing tests:
```powershell
python -m pytest -v
```

Run comprehensive headless browser end-to-end verification in Microsoft Edge via CDP:
```powershell
python scratch/verify_pages_headless.py
```

### 4. Launch the Platform

#### Option A: Unified Web Platform (Landing Page + Login Page + Dashboard)
Run via Python:
```powershell
python server.py
```
Or run via npm:
```powershell
npm run dev
# or: npm start
```
- **Landing Page:** `http://localhost:8000/` or `http://localhost:8000/landing.html`
- **Sign In Page:** `http://localhost:8000/login.html`
- **Protected Dashboard:** `http://localhost:8000/index.html` (requires authentication)

#### Option B: Streamlit Surveillance Application
```powershell
streamlit run app.py
```
Open your browser at `http://localhost:8501`.

---

## 🔐 Authentication, Roles & Security Model

The system enforces server-side authentication using salted PBKDF2-HMAC-SHA256 (100,000 rounds) and a strict 3-role permission matrix:

| User Account | Initial Credential | Role | Permissions |
| :--- | :--- | :--- | :--- |
| **`dvnsabhiram071@gmail.com`** | `Amr@135` *(Temporary)* | **System Administrator** | User accounts, security audit logs, platform configuration, and full analyst capabilities. *Mandatory first-login permanent password change required.* |
| **`analyst@amrsentinel.org`** | `Analyst@2026!Secure` | **Surveillance Analyst** | Live surveillance dashboards, geographic maps, alert triage, AST CSV ingestion & validation, AI Copilot, scenario simulation, and exports. |
| **`viewer@amrsentinel.org`** | `Viewer@2026!Access` | **Read-Only Viewer** | Read-only surveillance viewing (dashboards, trends, alerts, maps). Ingestion uploads, alert edits, and administrative settings are blocked. |

### Mandatory First-Login Password Policy:
- Minimum 12 characters
- At least one uppercase letter (`A-Z`)
- At least one lowercase letter (`a-z`)
- At least one number (`0-9`)
- At least one special symbol (`!@#$%^&*...`)

---

## 🧭 3-Minute Demo Sequence (Presentation Walkthrough)

| Time | Step | Action in AMR Sentinel |
| :--- | :--- | :--- |
| **0:00–0:25** | **Landing Page** | Open `http://localhost:8000/`. Walk through the hero statement, feature cards, live interactive dashboard preview, and synthetic disclaimer. |
| **0:25–0:55** | **Secure Sign In** | Click *"Sign In"*, navigate to `/login.html`. Demonstrate the two-column interface, enter initial credentials (`dvnsabhiram071@gmail.com` / `Amr@135`), and show the mandatory permanent password change flow. |
| **0:55–1:35** | **Surveillance Dashboard** | Access `/index.html`. Inspect calculated KPI cards, longitudinal trend charts, and Leaflet India resistance map. |
| **1:35–2:05** | **Alert Investigation & Copilot** | Select `ALT-001` (ICU *K. pneumoniae* vs *Meropenem* surge), verify numerator/denominator rates ($R/N$), and query AI Copilot. |
| **2:05–2:35** | **Scenario Lab & Data QC** | Switch between epidemiological outbreak scenarios (*Gradual Rise*, *Sudden Spike*), and demonstrate quarantine logs. |
| **2:35–3:00** | **Role Management & Logout** | Demonstrate Admin Console user roles and security audit log. Click *"Sign Out"*, verifying immediate session termination and redirection. |

---

## 📁 Repository Structure

```
amr-sentinel/
├── server.py                  # Unified HTTP Web Server & Security Gate (port 8000)
├── package.json               # npm scripts (start, dev, serve, streamlit, test)
├── app.py                     # Streamlit Multipage Surveillance Entry Point
├── landing.html               # Light-themed Landing Page (Reference Design 1)
├── login.html                 # Two-column Login Page (Reference Design 2)
├── index.html                 # Full Standalone Surveillance Web Dashboard
├── standalone_prototype.html  # Synchronized Standalone Dashboard
├── pages/
│   ├── 1_Resistance_Trends.py      # Longitudinal & ward breakdown (Guarded)
│   ├── 2_Alert_Investigation.py    # In-depth signal audit & triage (Guarded)
│   ├── 3_Scenario_Lab.py           # Scenario switcher & timeline replay (Guarded)
│   ├── 4_AI_Copilot.py             # Groq LPU evidence-based assistant (Guarded)
│   ├── 5_Intelligence_Brief.py     # What Changed ranked shifts (Guarded)
│   ├── 6_Data_Quality.py           # Ingestion QC & quarantine logs (Guarded)
│   ├── 7_Reports.py                # Reproducible exports & snapshots (Guarded)
│   └── 8_Admin_Console.py          # User management & audit logs (Admin only)
├── src/
│   ├── auth.py                # PBKDF2 hashing, 3-role permissions & audit logs
│   ├── validation.py          # Schema enforcement & quarantine
│   ├── metrics.py             # Deterministic AST rates & antibiograms
│   ├── alerts.py              # Configurable rule-based signals
│   ├── data_generator.py      # Synthetic outbreak scenario generator
│   ├── scenarios.py           # Scenario state management
│   ├── copilot.py             # Groq LLM integration & offline fallback
│   ├── intelligence_brief.py  # Top percentage-point change ranking
│   ├── exports.py             # Markdown and CSV reporting
│   └── ui_helpers.py          # Theme, role cards & require_authentication guard
├── tests/
│   ├── test_server.py         # HTTP routing, cookie sessions & security tests
│   ├── test_auth.py           # PBKDF2, password policy & role tests
│   ├── test_validation.py     # Schema & quarantine unit tests
│   ├── test_metrics.py        # Mathematical rate calculations
│   ├── test_alerts.py         # Signal threshold triggers
│   └── test_copilot.py        # Evidence structuring & fallback
├── scratch/
│   └── verify_pages_headless.py # End-to-end headless browser verification
├── data/
│   ├── users.json             # Salted PBKDF2 credential directory
│   ├── audit_log.json         # Security audit log
│   ├── demo_isolates.csv      # Synthetic isolate records
│   └── demo_alerts.json       # Example alerts bundle
├── requirements.txt
├── .env                       # Secret Groq API Key (git-ignored)
├── .env.example
├── .gitignore
└── README.md
```
