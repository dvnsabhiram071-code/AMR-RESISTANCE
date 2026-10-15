"""
Unit tests for alert detection and rule triggers.
"""
import pytest
from src.metrics import WindowComparison
from src.alerts import evaluate_window_alerts, AlertRuleConfig


def test_alert_triggered_by_critical_pathogen_surge():
    comp = WindowComparison(
        group_key=("Klebsiella pneumoniae", "Meropenem", "ICU"),
        organism="Klebsiella pneumoniae",
        antibiotic="Meropenem",
        department="ICU",
        current_start="2025-05-01",
        current_end="2025-05-31",
        baseline_start="2025-01-01",
        baseline_end="2025-04-30",
        current_tested=50,
        current_resistant=25,
        current_rate=50.0,
        baseline_tested=100,
        baseline_resistant=20,
        baseline_rate=20.0,
        pct_point_change=30.0,
        relative_change_pct=150.0,
        is_current_low_volume=False,
        is_baseline_low_volume=False,
    )
    alerts = evaluate_window_alerts([comp])
    assert len(alerts) == 1
    alert = alerts[0]
    assert alert.severity == "Critical"
    assert "Priority pathogen" in alert.trigger_reason
    assert alert.current_rate == 50.0
    assert alert.pct_point_change == 30.0


def test_alert_low_volume_downgrades_severity():
    comp = WindowComparison(
        group_key=("E. coli", "Cipro", "Surgery"),
        organism="E. coli",
        antibiotic="Cipro",
        department="Surgery",
        current_start="2025-05-01",
        current_end="2025-05-31",
        baseline_start="2025-01-01",
        baseline_end="2025-04-30",
        current_tested=8,  # N < 15
        current_resistant=4,
        current_rate=50.0,
        baseline_tested=50,
        baseline_resistant=10,
        baseline_rate=20.0,
        pct_point_change=30.0,
        relative_change_pct=150.0,
        is_current_low_volume=True,
        is_baseline_low_volume=False,
    )
    config = AlertRuleConfig(min_current_tested=15)
    alerts = evaluate_window_alerts([comp], config)
    assert len(alerts) == 1
    alert = alerts[0]
    # Severity should be downgraded due to small current denominator
    assert alert.severity in ["High", "Moderate"]
    assert "Small current denominator" in alert.caveats
