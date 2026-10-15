"""
Exports and Reproducibility Snapshot Generation for AMR Sentinel.
"""
from datetime import datetime
from typing import Dict, Any, List, Optional
import pandas as pd


def generate_export_csv(
    df: pd.DataFrame,
    metadata: Dict[str, Any]
) -> str:
    """
    Exports filtered surveillance dataframe to a standard CSV string.
    """
    if df is None or df.empty:
        return "No data available for export"
    return df.to_csv(index=False)


def generate_executive_report_markdown(
    df: pd.DataFrame,
    alerts: List[Any],
    filters: Dict[str, Any],
    scenario_name: str,
    overall_rate: Optional[float],
    total_tested: int,
) -> str:
    """
    Generates a structured, reproducible executive surveillance report.
    """
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S UTC")

    md = f"""# AMR SENTINEL — EXECUTIVE SURVEILLANCE REPORT
**Report Classification:** Synthetic Demonstration & Decision Support Prototype  
**Generated Timestamp:** {now_str}  
**Active Scenario / Source:** {scenario_name}  

---

## 1. Governance & Surveillance Scope
- **Dataset Classification:** SYNTHETIC DEMO DATA — Not for Clinical Diagnostic Use.
- **Reporting Period:** {filters.get('date_range', 'Full Period')}
- **Department Filter:** {filters.get('department', 'All Departments')}
- **Organism Filter:** {filters.get('organism', 'All Pathogens')}
- **Antimicrobial Filter:** {filters.get('antibiotic', 'All Agents')}

---

## 2. Executive Surveillance Summary
- **Total Valid Isolates Analyzed ($N$):** {total_tested}
- **Overall Resistance Proportion:** {f'{overall_rate:.1f}%' if overall_rate is not None else 'N/A'}
- **Active Signal Count:** {len(alerts)}
- **High / Critical Priority Signals:** {len([a for a in alerts if getattr(a, 'severity', '') in ['Critical', 'High']])}

---

## 3. Active Resistance Alerts & Investigation Evidence
"""
    if not alerts:
        md += "_No active signals or threshold violations detected for current filter settings._\n"
    else:
        for a in alerts:
            md += f"""### [{a.severity}] {a.title}
- **Organism & Drug:** {a.organism} vs {a.antibiotic} ({a.department})
- **Current Window:** {a.current_rate:.1f}% resistance ($R={a.current_resistant}$, $N={a.current_tested}$)
- **Baseline Window:** {a.baseline_rate:.1f}% resistance ($R={a.baseline_resistant}$, $N={a.baseline_tested}$)
- **Percentage-Point Shift:** {a.pct_point_change:+.1f}% pt
- **Trigger Rule:** {a.trigger_reason}
- **Data Caveats:** {a.caveats or 'None. Sample size meets standard reporting criteria.'}
- **Review Status:** {a.status}

"""

    md += f"""---

## 4. Reproducibility & Configuration Snapshot
- **Platform Version:** AMR Sentinel v1.0.0 (Python / Streamlit / Groq)
- **Minimum Reporting Denominator:** 15 isolates
- **Critical Threshold:** +15% point surge in priority pathogens or +25% point general surge
- **Deduplication Policy:** Consecutive repeat isolates within 30-day episode quarantined
- **Model In-Use:** Groq LPU Accelerated Inference (`openai/gpt-oss-120b`) with deterministic rule fallback
- **Disclaimer:** This tool provides epidemiological decision support. Clinical intervention requires validation by a qualified medical microbiologist.
"""
    return md
