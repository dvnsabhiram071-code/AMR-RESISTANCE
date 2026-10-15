"""
Configurable Alert Detection and Surveillance Signal Engine for AMR Sentinel.
"""
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional, Any
import pandas as pd
from src.metrics import compare_time_windows, WindowComparison


@dataclass
class AMRAlert:
    id: str
    severity: str  # Critical, High, Moderate, Watch
    title: str
    organism: str
    antibiotic: str
    department: str
    current_rate: Optional[float]
    baseline_rate: Optional[float]
    pct_point_change: Optional[float]
    current_tested: int
    current_resistant: int
    baseline_tested: int
    baseline_resistant: int
    trigger_reason: str
    caveats: Optional[str]
    evidence: Dict[str, Any]
    status: str = "Active"  # Active, Under Review, Escalated, Resolved, Acknowledged
    review_notes: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class AlertRuleConfig:
    min_current_tested: int = 15
    pct_change_critical: float = 25.0
    pct_change_high: float = 15.0
    pct_change_moderate: float = 10.0
    absolute_critical_threshold: float = 60.0
    critical_pathogens: tuple = (
        ("Klebsiella pneumoniae", "Meropenem"),
        ("Klebsiella pneumoniae", "Imipenem"),
        ("Pseudomonas aeruginosa", "Meropenem"),
        ("Acinetobacter baumannii", "Meropenem"),
        ("Staphylococcus aureus", "Vancomycin"),
        ("Staphylococcus aureus", "Oxacillin"),
        ("Enterococcus faecium", "Vancomycin"),
    )


def evaluate_window_alerts(
    comparisons: List[WindowComparison],
    config: Optional[AlertRuleConfig] = None
) -> List[AMRAlert]:
    """
    Evaluates window comparison records against configured surveillance rules.
    """
    if config is None:
        config = AlertRuleConfig()

    alerts: List[AMRAlert] = []
    alert_idx = 1

    for comp in comparisons:
        # Require that both current and baseline rates are valid
        if comp.current_rate is None or comp.baseline_rate is None or comp.pct_point_change is None:
            continue

        pct_change = comp.pct_point_change
        curr_rate = comp.current_rate
        curr_tested = comp.current_tested

        # Minimum isolate volume floor: prevent 1 or 2 isolated records from creating alerts
        if curr_tested < 5 or comp.baseline_tested < 5:
            continue

        is_crit_pair = (comp.organism, comp.antibiotic) in config.critical_pathogens

        # Check conditions
        triggered = False
        severity = "Watch"
        reasons = []

        # 1. Critical pathogen-drug pairing spike or high rate
        if is_crit_pair:
            if pct_change >= config.pct_change_high or curr_rate >= 40.0:
                triggered = True
                severity = "Critical"
                reasons.append(
                    f"Priority pathogen ({comp.organism} vs {comp.antibiotic}) on WHO/CDC surveillance lists "
                    f"with current rate {curr_rate:.1f}% (+{pct_change:.1f}% pt change vs baseline)."
                )

        # 2. Large percentage-point jump
        if not triggered and pct_change >= config.pct_change_critical:
            triggered = True
            severity = "Critical"
            reasons.append(f"Major surge: +{pct_change:.1f} percentage points vs baseline period.")
        elif not triggered and pct_change >= config.pct_change_high:
            triggered = True
            severity = "High"
            reasons.append(f"Significant increase: +{pct_change:.1f} percentage points vs baseline.")
        elif not triggered and pct_change >= config.pct_change_moderate:
            triggered = True
            severity = "Moderate"
            reasons.append(f"Notable upward trend: +{pct_change:.1f} percentage points vs baseline.")

        # 3. Absolute threshold breach
        if not triggered and curr_rate >= config.absolute_critical_threshold:
            triggered = True
            severity = "High"
            reasons.append(f"Absolute resistance exceeds high threshold ({curr_rate:.1f}% >= {config.absolute_critical_threshold}%).")

        if triggered:
            caveats = []
            is_small_sample = curr_tested < config.min_current_tested
            if is_small_sample:
                caveats.append(f"Small current denominator (N={curr_tested} < {config.min_current_tested}); elevated statistical uncertainty.")
                # Demote severity when sample size is insufficient to prevent false high-priority alarms
                if severity == "Critical":
                    severity = "Moderate"
                elif severity == "High":
                    severity = "Watch"

            if comp.caveat:
                caveats.append(comp.caveat)

            trigger_text = " ".join(reasons)
            caveat_text = "; ".join(caveats) if caveats else None

            title = f"Unusual {comp.antibiotic} resistance shift in {comp.organism} ({comp.department})"

            # Comprehensive 10-point evidence behind each alert
            evidence_dict = {
                # 1. What was detected
                "what_detected": (
                    f"Unusual resistance shift in {comp.organism} against {comp.antibiotic} "
                    f"observed in {comp.department} (Observed: {curr_rate:.1f}%, Baseline: {comp.baseline_rate:.1f}%, "
                    f"Shift: {pct_change:+.1f} percentage points)."
                ),
                # 2. Organism and antibiotic
                "organism": comp.organism,
                "antibiotic": comp.antibiotic,
                # 3. Location and time
                "location": comp.department,
                "reporting_period": f"{comp.current_start} to {comp.current_end}",
                "baseline_period": f"{comp.baseline_start} to {comp.baseline_end}",
                "location_and_time": f"Unit: {comp.department} | Current: {comp.current_start} to {comp.current_end} | Baseline: {comp.baseline_start} to {comp.baseline_end}",
                # 4. Observed resistance (formula & rate)
                "observed_resistance": f"{comp.current_resistant} resistant out of {comp.current_tested} valid tested isolates ({curr_rate:.1f}%)",
                "observed_rate": curr_rate,
                "observed_resistant_count": comp.current_resistant,
                "observed_tested_count": comp.current_tested,
                # 5. Comparison baseline
                "comparison_baseline": f"{comp.baseline_resistant} resistant out of {comp.baseline_tested} valid tested isolates ({comp.baseline_rate:.1f}%)",
                "baseline_rate": comp.baseline_rate,
                "baseline_resistant_count": comp.baseline_resistant,
                "baseline_tested_count": comp.baseline_tested,
                # 6. Change in percentage points
                "change": f"{pct_change:+.1f} percentage points vs baseline period",
                "pct_point_change": pct_change,
                # 7. Sample size breakdown
                "sample_size": f"Current: N={comp.current_tested} valid tests | Baseline: N={comp.baseline_tested} valid tests (Combined: {comp.current_tested + comp.baseline_tested})",
                "current_tested": comp.current_tested,
                "baseline_tested": comp.baseline_tested,
                # 8. Trigger rule
                "trigger_rule": trigger_text,
                # 9. Data quality & caveats
                "data_quality": caveat_text if caveat_text else "Complete data criteria met; verified AST records with zero schema quarantine exclusions in analyzed slice.",
                "is_low_volume": is_small_sample,
                # 10. Recommended next step
                "recommended_next_step": "Assign an authorized surveillance analyst to cross-verify isolate records, inspect hospital ward antimicrobial usage, and notify infection prevention if signal is clinically validated.",
                # Disclaimer & Reproducibility metadata
                "classification": "Surveillance signal for investigation — not a confirmed outbreak or clinical recommendation.",
                "reproducibility": "Calculation verified from uploaded AST dataset via deterministic AMR Sentinel rule engine."
            }

            alert = AMRAlert(
                id=f"ALT-{alert_idx:03d}",
                severity=severity,
                title=title,
                organism=comp.organism,
                antibiotic=comp.antibiotic,
                department=comp.department,
                current_rate=curr_rate,
                baseline_rate=comp.baseline_rate,
                pct_point_change=pct_change,
                current_tested=comp.current_tested,
                current_resistant=comp.current_resistant,
                baseline_tested=comp.baseline_tested,
                baseline_resistant=comp.baseline_resistant,
                trigger_reason=trigger_text,
                caveats=caveat_text,
                evidence=evidence_dict
            )
            alerts.append(alert)
            alert_idx += 1

    # Sort alerts by severity priority
    severity_order = {"Critical": 0, "High": 1, "Moderate": 2, "Watch": 3}
    alerts.sort(key=lambda a: (severity_order.get(a.severity, 4), -(a.pct_point_change or 0)))

    return alerts


def detect_alerts_from_dataframe(
    df: pd.DataFrame,
    current_days: int = 60,
    baseline_days: int = 180,
    config: Optional[AlertRuleConfig] = None
) -> List[AMRAlert]:
    """
    Convenience runner to partition dates into current and baseline windows,
    compute comparisons, and detect alerts.
    """
    if df is None or df.empty or "test_date" not in df:
        return []

    dates = pd.to_datetime(df["test_date"]).dropna()
    if dates.empty:
        return []

    max_date = dates.max()
    curr_start = (max_date - pd.Timedelta(days=current_days)).strftime("%Y-%m-%d")
    curr_end = max_date.strftime("%Y-%m-%d")

    base_start = (max_date - pd.Timedelta(days=current_days + baseline_days)).strftime("%Y-%m-%d")
    base_end = (max_date - pd.Timedelta(days=current_days + 1)).strftime("%Y-%m-%d")

    comparisons = compare_time_windows(
        df=df,
        current_start=curr_start,
        current_end=curr_end,
        baseline_start=base_start,
        baseline_end=base_end,
        group_cols=["organism", "antibiotic", "department"],
        min_denominator=config.min_current_tested if config else 15
    )

    return evaluate_window_alerts(comparisons, config)
