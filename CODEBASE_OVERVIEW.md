# 🛡️ AMR Sentinel — Codebase Overview & Architecture Specification

> **Notice:** This document is prepared for comprehensive architectural and code review.  
> AMR Sentinel is an **epidemiological surveillance and antimicrobial resistance (AMR) decision-support system**. It operates on **synthetic demonstration data** and serves as a surveillance intelligence prototype, not an individual clinical prescription or diagnostic device.

---

## 1. Executive Summary & Purpose

**AMR Sentinel** aggregates, normalizes, and analyzes clinical microbiology Antimicrobial Susceptibility Testing (AST) records to detect emerging pathogen resistance surges, alert infection control teams, and provide evidence-grounded AI briefings.

### Core Architectural Principles:
1. **Pure Mathematical Determinism:**
   - Evaluates pure mathematical resistance rates:
     $$\text{Resistance Proportion (\%)} = \frac{\text{Resistant Isolates (R)}}{\text{Eligible Tested Isolates (N)}} \times 100$$
   - Zero denominator rule: When tested count $N = 0$, rate returns `None` (`N/A`), never `0%`.
   - Low sample size caveats: Automatically flagged whenever sample volume $N < 30$.
2. **Dual-Implementation Strategy:**
   - **Streamlit Analytical Backend:** Multi-page interactive application (`app.py` + `pages/` + `src/`) driven by Python analytical libraries (Pandas, Plotly, NumPy, Pytest).
   - **Standalone Web SPA:** High-fidelity interactive single-page dashboard (`index.html`) utilizing Leaflet.js GIS mapping and Chart.js analytics.
3. **Evidence-Grounded AI Guardrails:**
   - Groq LPU inference strictly constrained to structured numerical evidence.
   - Robust offline deterministic fallback ensuring 100% platform availability without external API dependencies.
4. **Human-in-the-Loop Triage:**
   - Clinical decision audit trails allowing epidemiologists to record investigation notes and state updates.

---

## 2. Complete Repository Directory Tree

```
AMR_Sentinel/
├── app.py                         # [Main Entry Point] Streamlit Executive Overview Dashboard
├── CODEBASE_OVERVIEW.md           # Architecture, module reference & code review guide
├── README.md                      # Presentation runbook & quick-start guide
├── requirements.txt               # Declared Python dependencies
├── .env.example                   # Environment configuration template (safe placeholder)
├── .gitignore                     # Repository git exclusion rules
├── index.html                     # Standalone single-page web dashboard (Leaflet + Chart.js)
├── standalone_prototype.html      # Mirrored standalone build
├── data/                          # Data files & geospatial vector assets
│   ├── demo_isolates.csv          # 800 synthetic clinical AST isolate records
│   ├── demo_alerts.json           # Seed active surveillance alert definitions
│   ├── india_states_data.js       # Vector epidemiologic metrics (Web SPA)
│   ├── india_states_simplified.geojson # Simplified geospatial boundaries
│   ├── india_states.geojson       # Full geospatial boundary polygons
│   └── india_svg_paths.js         # Optimized SVG map paths
├── pages/                         # Streamlit Multi-Page Modules
│   ├── 1_Resistance_Trends.py     # Longitudinal trend analysis & departmental breakdown
│   ├── 2_Alert_Investigation.py   # Signal deep-dive, audit trail & triage management
│   ├── 3_Scenario_Lab.py          # Synthetic scenario switcher & monthly timeline replay
│   ├── 4_AI_Copilot.py            # Evidence-grounded Groq AI explainability assistant
│   ├── 5_Intelligence_Brief.py    # Ranked percentage-point surge analysis ("What Changed")
│   ├── 6_Data_Quality.py          # Ingestion QC, quarantine table & CSV upload
│   └── 7_Reports.py               # Markdown executive report & filtered CSV export center
├── src/                           # Pure Python Domain, Analytical & Utility Modules
│   ├── __init__.py                # Package initialization
│   ├── metrics.py                 # Core AST calculations, rate results & antibiograms
│   ├── alerts.py                  # Anomaly detection, multi-threshold rule evaluation
│   ├── copilot.py                 # Groq LLM integration & offline fallback generator
│   ├── validation.py              # CSV schema validator & quarantine logger
│   ├── scenarios.py               # Scenario catalog & monthly timeline slicer
│   ├── intelligence_brief.py      # Window comparison & shift ranker
│   ├── data_generator.py          # Synthetic outbreak isolate generator
│   ├── exports.py                 # Markdown & CSV reporting utilities
│   └── ui_helpers.py              # Session state initialization, clinical CSS theme & filters
└── tests/                         # Pytest Automated Test Suite (13/13 Passing)
    ├── test_metrics.py            # Mathematical rates & denominator rules
    ├── test_alerts.py             # Rule triggers & priority categorization
    ├── test_copilot.py            # Evidence grounding & fallback testing
    └── test_validation.py         # Schema conformance & quarantine tests
```

---

## 3. Module-by-Module Technical Breakdown

### A. Streamlit Application Entrypoint & Pages

#### `app.py` — Executive Overview Dashboard
- **Role:** Main application entry point for the Streamlit dashboard.
- **Key Functions:**
  - Initializes session state and global clinical dark/teal CSS theme.
  - Computes global surveillance KPIs: Eligible Tested Isolates, Overall Resistance Rate, Active Signals, High & Critical Priority alerts.
  - Renders longitudinal monthly resistance trajectory using Plotly graph objects.
  - Constructs pathogen resistance comparison bar charts and dynamic Antibiogram Matrix (Organism $\times$ Antimicrobial heatmap).
  - Displays high-priority active surveillance alert cards with 1-click investigation navigation.

#### `pages/1_Resistance_Trends.py` — Longitudinal Explorer
- **Role:** Multi-dimensional epidemiological trend analysis across departments, specimens, and bug-drug pairs.
- **Key Visualizations:**
  - Departmental susceptibility comparison (ICU, Surgery, General Medicine, Pediatrics, Oncology).
  - Specimen type distribution donut chart (Blood, Urine, Sputum, Wound Swab).
  - Longitudinal pathogen-specific monthly trend lines.
  - Granular data table with low-volume caveat indicators.

#### `pages/2_Alert_Investigation.py` — Clinical Signal Triage
- **Role:** In-depth audit and closed-loop triage for surveillance signals.
- **Key Features:**
  - Evaluates mathematical current vs. baseline rates and percentage-point shifts.
  - Outlines deterministic trigger rules and statistical caveat checks.
  - Embeds signal-specific historical monthly trajectory plot.
  - **Human-in-the-Loop Triage Form:** Allows clinicians/epidemiologists to transition alert status (`Active`, `Under Review`, `Escalated to IPC Committee`, `Resolved / False Anomaly`), assign responsible officers, and record investigation audit notes.

#### `pages/3_Scenario_Lab.py` — Scenario Simulation & Timeline Replay
- **Role:** Outbreak simulation and chronological timeline progression.
- **Key Features:**
  - **Benchmark Scenarios:** Instantly switch between 4 epidemiological scenarios:
    1. `sudden_spike`: ICU *Klebsiella pneumoniae* Carbapenem surge.
    2. `gradual_rise`: Inpatient *E. coli* Fluoroquinolone creep over 12 months.
    3. `stable_baseline`: Predictable, non-surging endemic resistance patterns.
    4. `sparse_low_volume`: Small-clinic low-denominator dataset stress-testing safety rules.
  - **Timeline Replay Slider:** Step month-by-month through historical data to observe how metrics evolve and when automated alert thresholds fire.

#### `pages/4_AI_Copilot.py` — Groq AI Surveillance Assistant
- **Role:** Plain-language, evidence-grounded interpretation of surveillance signals.
- **Key Features:**
  - Feeds strictly verified numerical evidence (Organism, Drug, Unit, Current/Baseline Rates, Shifts, Rules, Caveats) to Groq.
  - Pre-configured clinical surveillance questions (e.g., sample size bias, trigger reason, infection control steps).
  - Enforces clinical safety disclaimers: Prototype decision aid, zero prescriptive advice.

#### `pages/5_Intelligence_Brief.py` — "What Changed" Analysis
- **Role:** Executive-level surveillance brief ranking the largest observed resistance shifts.
- **Key Features:**
  - Evaluates comparative time windows (e.g., last 60 days vs. preceding 180-day baseline).
  - Ranks bug-drug pairs by absolute percentage-point difference.
  - Annotates shifts with statistical reliability confidence badges (`High Confidence` vs. `Low-Volume Caveat`).

#### `pages/6_Data_Quality.py` — Ingestion & Quarantine Audit
- **Role:** Laboratory data governance, schema validation, and quarantine auditing.
- **Key Features:**
  - Audits total vs. valid accepted records and rejection rates.
  - Integrity violation checks: Duplicate detection, invalid S/I/R category values, malformed dates, missing fields.
  - **Quarantine Log Table:** Inspects excluded rows with explicit rejection reasons.
  - **File Uploader:** Allows ingestion of authorized laboratory CSV files with automated validation.

#### `pages/7_Reports.py` — Reproducible Export Center
- **Role:** Export surveillance audits and filtered datasets.
- **Key Features:**
  - Generates reproducible Markdown surveillance summaries with timestamp, active filter criteria, and alert listings.
  - 1-click downloads for Markdown reports (`.md`) and synchronized CSV datasets (`.csv`).

---

### B. Pure Python Analytics Engine (`src/`)

- **`src/metrics.py`**:
  - `calculate_resistance_rate(df, min_denominator=30)`: Computes resistant, intermediate, susceptible counts and percentages. Returns `AMRRateResult` dataclass. Enforces zero denominator safety and low-volume caveats.
  - `compute_grouped_summary(df, group_cols, min_denominator)`: Multi-dimensional grouped resistance aggregation.
  - `build_antibiogram_matrix(df, min_denominator=10)`: Constructs rate and isolate count matrices for heatmaps.
  - `compare_time_windows(...)`: Computes absolute and relative shifts between historical windows.
- **`src/alerts.py`**:
  - `detect_alerts_from_dataframe(df, config)`: Runs automated anomaly checks across critical pathogen pairings (e.g., CRE, MRSA, VRE).
  - Classifies alerts into severity tiers: `Critical`, `High`, `Moderate`, `Watch`.
  - Automatically downgrades severity if current sample size is low, appending safety caveats.
- **`src/copilot.py`**:
  - `query_amr_copilot(evidence, user_query, api_key)`: Connects to Groq LPU API.
  - `generate_offline_explanation(evidence)`: 100% deterministic, rule-based fallback generator returning structured 5-section briefings (`1. What Changed`, `2. Evidence & Metrics`, `3. Why Flagged`, `4. Data Caveats`, `5. Suggested Review Steps`).
- **`src/validation.py`**:
  - `validate_and_clean_amr_data(df)`: Multi-pass cleaning pipeline validating required columns, S/I/R categorical values, date formats, and duplicates.
  - Returns `ValidationReport` with clean dataset and quarantine DataFrame.
- **`src/scenarios.py`**:
  - Catalog of synthetic outbreak datasets (`SCENARIOS`).
  - Slices datasets chronologically for timeline replay.
- **`src/data_generator.py`**:
  - Synthesizes realistic microbiology AST records with configurable baseline rates, surge spikes, and random noise.
- **`src/exports.py`**:
  - Formats executive surveillance briefs into Markdown and serializes filtered CSV data.
- **`src/ui_helpers.py`**:
  - Manages Streamlit session state, persistent clinical badges, custom CSS styling, and global sidebar filters.

---

### C. Client-Side Web Application (`index.html`)

A high-performance standalone single-page application (SPA) featuring:
- **12 Integrated Surveillance Modules:** Overview, Geographic Surveillance (India Leaflet Map), Resistance Trends, Alert Center, AI Copilot, Scenario Lab, Intelligence Brief, Data Upload, Source Registry, Data Quality, Reports & Exports, Global Settings.
- **Dynamic Theme Engine:** Instant Light / Dark / System mode switching with 5-color accent palette persistence via CSS variables.

---

## 4. Dependencies & Prerequisites

Declared in `requirements.txt`:
```text
streamlit>=1.35.0      # Web application framework
plotly>=5.20.0         # Interactive charts and heatmaps
pandas>=2.0.0          # Data manipulation and aggregation
numpy>=1.24.0          # Numerical computing
groq>=0.9.0            # Groq LPU inference SDK
python-dotenv>=1.0.0   # Environment variable management
pytest>=8.0.0          # Test runner
scikit-learn>=1.4.0    # Predictive modeling utilities
```

---

## 5. How to Setup, Run & Verify

### Step 1: Install Dependencies
```powershell
pip install -r requirements.txt
```

### Step 2: Configure Environment Variables
Copy the template configuration:
```powershell
cp .env.example .env
```
*(Optional: Add your `GROQ_API_KEY` to `.env`. If omitted, the system operates seamlessly in deterministic offline fallback mode.)*

### Step 3: Run the Automated Test Suite
Execute the full test suite:
```powershell
python -m pytest tests/ -v
```
**Expected Result:** 13 passed in ~7 seconds.

### Step 4: Launch the Streamlit Application
```powershell
streamlit run app.py
```
Access the application in your browser at `http://localhost:8501`.

### Step 5: Launch the Standalone Web SPA (Optional)
```powershell
python -m http.server 8000
```
Access the web dashboard in your browser at `http://localhost:8000/index.html`.

---

## 6. Key Checkpoints for Code Reviewers

When conducting a code review of AMR Sentinel, please examine:
1. **Mathematical Robustness (`src/metrics.py`):**
   - Verify that invalid/missing results do not distort denominators.
   - Confirm that zero denominator cases return `None` rather than `0%`.
2. **Offline Fallback Integrity (`src/copilot.py`):**
   - Ensure the system operates reliably when `GROQ_API_KEY` is absent or network connectivity drops.
3. **Data Governance & Quarantine (`src/validation.py`):**
   - Validate that corrupt isolate records are quarantined with reasons and not silently dropped.
4. **Clinical Boundaries & Guardrails:**
   - Confirm persistent labels distinguishing this prototype from a diagnostic or prescription medical tool.
