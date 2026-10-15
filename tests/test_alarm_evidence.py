"""
End-to-End Automated Test Suite for AMR Sentinel Alarm & 10-Point Evidence Features.
Covers all 9 required verification scenarios.
"""
import pytest
import io
import pandas as pd
from src.metrics import WindowComparison
from src.alerts import evaluate_window_alerts, detect_alerts_from_dataframe, AlertRuleConfig, AMRAlert
from src.alarm_manager import AlarmManager, GLOBAL_ALARM_MANAGER
from src.validation import validate_and_clean_amr_data


def make_test_comparison(
    org="E. coli",
    abx="Ciprofloxacin",
    dept="ICU",
    curr_n=50,
    curr_res=25,
    base_n=100,
    base_res=20,
    pct_change=30.0
) -> WindowComparison:
    """Helper to create a reproducible WindowComparison fixture."""
    return WindowComparison(
        group_key=(org, abx, dept),
        organism=org,
        antibiotic=abx,
        department=dept,
        current_start="2025-10-01",
        current_end="2025-12-31",
        baseline_start="2025-06-01",
        baseline_end="2025-08-31",
        current_tested=curr_n,
        current_resistant=curr_res,
        current_rate=(curr_res / curr_n * 100) if curr_n > 0 else 0.0,
        baseline_tested=base_n,
        baseline_resistant=base_res,
        baseline_rate=(base_res / base_n * 100) if base_n > 0 else 0.0,
        pct_point_change=pct_change,
        relative_change_pct=150.0,
        is_current_low_volume=(curr_n < 15),
        is_baseline_low_volume=(base_n < 15),
    )


# ==============================================================================
# Scenario 1: Qualifying HIGH alert triggers alarm
# ==============================================================================
def test_scenario_1_qualifying_high_alert_triggers_alarm():
    manager = AlarmManager()
    comp = make_test_comparison(org="Klebsiella pneumoniae", abx="Meropenem", curr_n=60, curr_res=30, base_n=100, base_res=15, pct_change=35.0)
    alerts = evaluate_window_alerts([comp])
    assert len(alerts) >= 1
    high_alert = alerts[0]
    assert high_alert.severity in ("Critical", "High")

    csv_mock = "isolate_id,date,state,organism,antibiotic,susceptibility\n1,2025-11-01,KA,K. pneumoniae,Meropenem,R\n"
    should_sound, active_alert, high_alerts = manager.process_dataset_alerts(alerts, file_content=csv_mock)

    assert should_sound is True
    assert active_alert is not None
    assert active_alert.id == high_alert.id
    assert manager.is_alarm_sounding is True
    assert manager.active_alarm_alert_id == high_alert.id


# ==============================================================================
# Scenario 2: STOP ALARM silences it immediately
# ==============================================================================
def test_scenario_2_stop_alarm_silences_immediately():
    manager = AlarmManager()
    comp = make_test_comparison()
    alerts = evaluate_window_alerts([comp])
    should_sound, active_alert, _ = manager.process_dataset_alerts(alerts, file_content="sample_content_1")
    assert should_sound is True
    assert manager.is_alarm_sounding is True

    # User clicks STOP ALARM
    success = manager.stop_alarm(active_alert.id)
    assert success is True
    assert manager.is_alarm_sounding is False
    assert active_alert.id in manager.silenced_alert_ids


# ==============================================================================
# Scenario 3: Alert remains visible and active after sound stops
# ==============================================================================
def test_scenario_3_alert_remains_active_after_stop():
    manager = AlarmManager()
    comp = make_test_comparison()
    alerts = evaluate_window_alerts([comp])
    target_id = alerts[0].id
    manager.process_dataset_alerts(alerts)
    manager.stop_alarm(target_id)

    # The alert itself is not deleted or removed from alerts list
    assert len(alerts) == 1
    assert alerts[0].id == target_id
    assert alerts[0].organism == "E. coli"
    assert alerts[0].antibiotic == "Ciprofloxacin"
    # State inspection
    state = manager.get_alarm_state()
    assert state["is_sounding"] is False
    assert target_id in state["silenced_alert_ids"]
    assert target_id not in state["acknowledged_alert_ids"]


# ==============================================================================
# Scenario 4: Acknowledging and stopping sound remain separate
# ==============================================================================
def test_scenario_4_separate_acknowledge_action():
    manager = AlarmManager()
    comp = make_test_comparison()
    alerts = evaluate_window_alerts([comp])
    target_id = alerts[0].id
    manager.process_dataset_alerts(alerts)

    # First: stop the alarm sound
    manager.stop_alarm(target_id)
    assert target_id in manager.silenced_alert_ids
    assert target_id not in manager.acknowledged_alert_ids

    # Second: separately acknowledge the alert with reviewer notes
    manager.acknowledge_alert(target_id, reviewer_email="analyst@amrsentinel.org", notes="Verified with microbiology ward.")
    assert target_id in manager.acknowledged_alert_ids
    assert manager.is_alarm_sounding is False


# ==============================================================================
# Scenario 5: Re-uploading same file hash does not restart alarm
# ==============================================================================
def test_scenario_5_reupload_same_file_hash_does_not_restart_alarm():
    manager = AlarmManager()
    comp = make_test_comparison()
    alerts = evaluate_window_alerts([comp])
    file_csv = "isolate_id,date,state,organism,antibiotic,susceptibility\n101,2025-10-15,KA,E. coli,Ciprofloxacin,R\n"

    # Initial upload triggers alarm
    should_sound, active_alert, _ = manager.process_dataset_alerts(alerts, file_content=file_csv)
    assert should_sound is True
    assert manager.is_alarm_sounding is True

    # User silences alarm
    manager.stop_alarm(active_alert.id)
    assert manager.is_alarm_sounding is False

    # User re-uploads the exact same file (or dashboard re-renders)
    should_sound_again, active_again, _ = manager.process_dataset_alerts(alerts, file_content=file_csv)
    assert should_sound_again is False
    assert active_again is None
    assert manager.is_alarm_sounding is False


# ==============================================================================
# Scenario 6: Medium and Low alerts do not trigger high-priority alarm
# ==============================================================================
def test_scenario_6_medium_and_low_alerts_never_trigger_alarm():
    manager = AlarmManager()
    # Create moderate alert (+16 pp surge on standard pathogen, curr_rate < 40%)
    comp_moderate = WindowComparison(
        group_key=("Proteus mirabilis", "Ampicillin", "General Medicine"),
        organism="Proteus mirabilis",
        antibiotic="Ampicillin",
        department="General Medicine",
        current_start="2025-10-01",
        current_end="2025-12-31",
        baseline_start="2025-06-01",
        baseline_end="2025-08-31",
        current_tested=40,
        current_resistant=10,
        current_rate=25.0,
        baseline_tested=80,
        baseline_resistant=10,
        baseline_rate=12.5,
        pct_point_change=12.5,
        relative_change_pct=100.0,
        is_current_low_volume=False,
        is_baseline_low_volume=False,
    )
    alerts = evaluate_window_alerts([comp_moderate])
    assert len(alerts) >= 1
    assert alerts[0].severity in ("Moderate", "Watch")

    should_sound, active_alert, high_alerts = manager.process_dataset_alerts(alerts)
    assert should_sound is False
    assert active_alert is None
    assert len(high_alerts) == 0
    assert manager.is_alarm_sounding is False


# ==============================================================================
# Scenario 7: Insufficient sample sizes and invalid files
# ==============================================================================
def test_scenario_7_insufficient_sample_size_and_invalid_data():
    manager = AlarmManager()

    # Case 7A: Small sample size (N=8 < 15) must be demoted and NEVER trigger high alarm
    comp_small = make_test_comparison(curr_n=8, curr_res=6, base_n=50, base_res=10, pct_change=55.0)
    alerts_small = evaluate_window_alerts([comp_small])
    assert len(alerts_small) == 1
    # Severity demoted from Critical to Moderate
    assert alerts_small[0].severity not in ("Critical", "High")
    assert alerts_small[0].severity in ("Moderate", "Watch")

    should_sound, _, _ = manager.process_dataset_alerts(alerts_small)
    assert should_sound is False
    assert manager.is_alarm_sounding is False

    # Case 7B: Very small isolated volume floor (N < 5) suppressed from window alerts
    comp_tiny = make_test_comparison(curr_n=3, curr_res=3, base_n=4, base_res=1)
    alerts_tiny = evaluate_window_alerts([comp_tiny])
    assert len(alerts_tiny) == 0

    # Case 7C: Invalid CSV with empty or zero valid rows
    empty_df = pd.DataFrame(columns=["isolate_id", "collection_date", "organism"])
    report = validate_and_clean_amr_data(empty_df)
    assert report.valid_rows == 0
    # No alerts or alarm should be produced on invalid data
    raw_alerts = detect_alerts_from_dataframe(report.clean_df)
    assert len(raw_alerts) == 0


# ==============================================================================
# Scenario 8: 10-point evidence completeness, accuracy, and no hallucinations
# ==============================================================================
def test_scenario_8_ten_point_evidence_completeness_and_fidelity():
    comp = make_test_comparison(
        org="Acinetobacter baumannii",
        abx="Colistin",
        dept="Burn ICU",
        curr_n=40,
        curr_res=16,
        base_n=80,
        base_res=16,
        pct_change=20.0
    )
    alerts = evaluate_window_alerts([comp])
    assert len(alerts) == 1
    alert = alerts[0]
    ev = alert.evidence

    # 1. What was detected
    assert "what_detected" in ev
    assert "Acinetobacter baumannii" in ev["what_detected"]
    assert "Colistin" in ev["what_detected"]
    assert "Burn ICU" in ev["what_detected"]

    # 2. Organism and antibiotic
    assert ev["organism"] == "Acinetobacter baumannii"
    assert ev["antibiotic"] == "Colistin"

    # 3. Location and time
    assert ev["location"] == "Burn ICU"
    assert "2025-10-01 to 2025-12-31" in ev["reporting_period"]
    assert "2025-06-01 to 2025-08-31" in ev["baseline_period"]

    # 4. Observed resistance (exact counts and formula)
    assert ev["observed_rate"] == 40.0
    assert ev["observed_resistant_count"] == 16
    assert ev["observed_tested_count"] == 40
    assert "16 resistant out of 40 valid tested isolates (40.0%)" in ev["observed_resistance"]

    # 5. Comparison baseline
    assert ev["baseline_rate"] == 20.0
    assert ev["baseline_resistant_count"] == 16
    assert ev["baseline_tested_count"] == 80
    assert "16 resistant out of 80 valid tested isolates (20.0%)" in ev["comparison_baseline"]

    # 6. Change in percentage points
    assert ev["pct_point_change"] == 20.0
    assert "+20.0 percentage points" in ev["change"]

    # 7. Sample size breakdown
    assert ev["current_tested"] == 40
    assert ev["baseline_tested"] == 80
    assert "N=40" in ev["sample_size"]
    assert "N=80" in ev["sample_size"]

    # 8. Trigger rule
    assert "trigger_rule" in ev
    assert len(ev["trigger_rule"]) > 5

    # 9. Data quality and caveats
    assert "data_quality" in ev
    assert "is_low_volume" in ev
    assert ev["is_low_volume"] is False

    # 10. Recommended next step
    assert "recommended_next_step" in ev
    assert "secondary" in ev["recommended_next_step"] or "analyst" in ev["recommended_next_step"]

    # Classification and synthetic disclaimer
    assert "Surveillance signal for investigation" in ev["classification"]
    assert "deterministic AMR Sentinel rule engine" in ev["reproducibility"]


# ==============================================================================
# Scenario 9: Volume control and singleton alarm lifecycle
# ==============================================================================
def test_scenario_9_volume_control_and_singleton_lifecycle():
    manager = AlarmManager()

    # Volume bounds checking
    assert manager.set_volume(0.65) == 0.65
    assert manager.alarm_volume == 0.65
    assert manager.set_volume(1.8) == 1.0  # Clamped to 1.0
    assert manager.set_volume(-0.4) == 0.0  # Clamped to 0.0

    # Singleton alarm loop lock
    comp1 = make_test_comparison(org="E. coli", abx="Cipro", pct_change=30.0)
    comp2 = make_test_comparison(org="K. pneumoniae", abx="Mero", pct_change=40.0)
    alerts = evaluate_window_alerts([comp1, comp2])
    assert len(alerts) == 2

    # Process batch: only one active alarm is returned and tracked as active
    should_sound, active_alert, high_alerts = manager.process_dataset_alerts(alerts)
    assert should_sound is True
    assert len(high_alerts) == 2
    assert active_alert.id == manager.active_alarm_alert_id

    # Repeated calls do not create multiple sounding targets
    should_sound_2, active_2, _ = manager.process_dataset_alerts(alerts)
    assert manager.active_alarm_alert_id == active_alert.id
