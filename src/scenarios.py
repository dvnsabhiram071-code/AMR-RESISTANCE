"""
Scenario Management and Timeline Replay Engine for AMR Sentinel.
"""
from typing import Dict, List, Tuple, Optional
import os
import pandas as pd
from src.data_generator import generate_synthetic_amr_dataset
from src.validation import validate_and_clean_amr_data, ValidationReport


SCENARIOS = {
    "stable": {
        "name": "Stable Baseline",
        "description": "Consistent historical resistance rates across wards with standard epidemiological variance.",
        "expected_signals": "Low to 0 alerts; steady baselines.",
    },
    "gradual_rise": {
        "name": "Gradual Rise",
        "description": "Simulated multi-month upward drift in Pseudomonas aeruginosa resistance to Meropenem.",
        "expected_signals": "High alert in P. aeruginosa / Meropenem across general and surgical wards.",
    },
    "sudden_spike": {
        "name": "Sudden Spike (Outbreak Simulation)",
        "description": "Acute surge in Carbapenem-Resistant Klebsiella pneumoniae (CRKP) in the Intensive Care Unit.",
        "expected_signals": "Critical alert in ICU Klebsiella / Meropenem with high percentage-point jump.",
    },
    "low_volume": {
        "name": "Low-Volume & Sparse Data",
        "description": "Sparse testing records (N < 20 per group) with missingness to test sample-size caveats.",
        "expected_signals": "Alerts flagged with low-denominator warnings and wide uncertainty intervals.",
    },
}


def load_scenario_dataset(scenario_key: str = "sudden_spike", demo_csv_path: Optional[str] = None) -> Tuple[ValidationReport, str]:
    """
    Loads dataset corresponding to the selected scenario or default demo CSV.
    """
    if scenario_key == "demo_file" and demo_csv_path and os.path.exists(demo_csv_path):
        raw_df = pd.read_csv(demo_csv_path)
        report = validate_and_clean_amr_data(raw_df)
        return report, "Demo CSV Bundle (800 Synthetic Isolates)"

    # Synthetic generator scenarios
    key = scenario_key if scenario_key in SCENARIOS else "sudden_spike"
    raw_df = generate_synthetic_amr_dataset(scenario=key, num_records=1200, seed=42)
    report = validate_and_clean_amr_data(raw_df)
    scenario_name = SCENARIOS[key]["name"]
    return report, scenario_name


def slice_timeline(df: pd.DataFrame, max_cutoff_date: str) -> pd.DataFrame:
    """
    Slices dataset up to a timeline cutoff date for simulation replay.
    """
    if df is None or df.empty or "test_date" not in df:
        return df
    return df[df["test_date"] <= max_cutoff_date].copy()
