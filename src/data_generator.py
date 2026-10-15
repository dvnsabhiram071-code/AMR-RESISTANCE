"""
Synthetic Data Generator for AMR Sentinel.
Generates reproducible, deterministic AMR scenarios for benchmarking and UI demonstration.
"""
from typing import List, Dict, Optional
import pandas as pd
import numpy as np
from datetime import datetime, timedelta


ORGANISMS = [
    "Escherichia coli",
    "Klebsiella pneumoniae",
    "Pseudomonas aeruginosa",
    "Acinetobacter baumannii",
    "Staphylococcus aureus",
    "Enterococcus faecalis",
]

ANTIBIOTICS = {
    "Escherichia coli": ["Ciprofloxacin", "Ampicillin", "Ceftriaxone", "Gentamicin", "Meropenem"],
    "Klebsiella pneumoniae": ["Meropenem", "Imipenem", "Ceftazidime", "Ciprofloxacin", "Amikacin"],
    "Pseudomonas aeruginosa": ["Meropenem", "Piperacillin-Tazobactam", "Ceftazidime", "Ciprofloxacin"],
    "Acinetobacter baumannii": ["Meropenem", "Colistin", "Ampicillin-Sulbactam", "Tigecycline"],
    "Staphylococcus aureus": ["Oxacillin", "Vancomycin", "Linezolid", "Clindamycin", "Erythromycin"],
    "Enterococcus faecalis": ["Ampicillin", "Vancomycin", "Linezolid", "Gentamicin"],
}

DEPARTMENTS = ["ICU", "General Medicine", "General Surgery", "Oncology", "Emergency", "Outpatient"]
SPECIMENS = ["Blood", "Urine", "Sputum", "Wound Swab", "CSF"]


def generate_synthetic_amr_dataset(
    scenario: str = "stable",
    num_records: int = 1200,
    start_date: str = "2025-01-01",
    end_date: str = "2025-10-31",
    seed: int = 42,
) -> pd.DataFrame:
    """
    Generates synthetic AMR records tailored to a specific epidemiological scenario:
    - 'stable': Steady rates with normal minor fluctuations.
    - 'gradual_rise': Linear increase in Pseudomonas / Meropenem resistance.
    - 'sudden_spike': Sharp recent surge in Klebsiella / Meropenem in ICU.
    - 'low_volume': Sparse testing data (N < 20 per group) with missingness.
    """
    rng = np.random.RandomState(seed)

    start_dt = datetime.strptime(start_date, "%Y-%m-%d")
    end_dt = datetime.strptime(end_date, "%Y-%m-%d")
    total_days = (end_dt - start_dt).days

    if scenario == "low_volume":
        num_records = min(num_records, 200)

    records: List[Dict[str, str]] = []

    for i in range(1, num_records + 1):
        rec_id = f"SYN-{i:06d}"
        day_offset = rng.randint(0, total_days + 1)
        test_dt = start_dt + timedelta(days=day_offset)
        test_date_str = test_dt.strftime("%Y-%m-%d")

        # Pick organism and department
        org = rng.choice(ORGANISMS)
        abx = rng.choice(ANTIBIOTICS[org])
        dept = rng.choice(DEPARTMENTS, p=[0.25, 0.25, 0.20, 0.10, 0.15, 0.05])
        specimen = rng.choice(SPECIMENS, p=[0.30, 0.35, 0.15, 0.15, 0.05])

        # Baseline probability of resistance
        base_res_p = 0.22

        if org == "Klebsiella pneumoniae" and abx in ["Meropenem", "Imipenem"]:
            base_res_p = 0.18
            if scenario == "sudden_spike" and dept == "ICU":
                # If in the last 60 days, resistance surges to 65%
                if day_offset >= (total_days - 60):
                    base_res_p = 0.68
                else:
                    base_res_p = 0.15

        elif org == "Pseudomonas aeruginosa" and abx == "Meropenem":
            base_res_p = 0.20
            if scenario == "gradual_rise":
                # Resistance rises linearly from 18% to 52% over the full period
                progression = day_offset / max(total_days, 1)
                base_res_p = 0.18 + (0.34 * progression)

        elif org == "Staphylococcus aureus" and abx == "Oxacillin":
            # MRSA baseline
            base_res_p = 0.35

        elif org == "Escherichia coli" and abx == "Ciprofloxacin":
            base_res_p = 0.30

        # Draw category
        rand_val = rng.rand()
        if rand_val < base_res_p:
            category = "Resistant"
        elif rand_val < (base_res_p + 0.10):
            category = "Intermediate"
        else:
            category = "Susceptible"

        # Occasional missingness in low-volume scenario
        if scenario == "low_volume" and rng.rand() < 0.12:
            category = "Unknown"

        records.append({
            "record_id": rec_id,
            "test_date": test_date_str,
            "hospital": "Metro Central Hospital",
            "department": dept,
            "specimen_type": specimen,
            "organism": org,
            "antibiotic": abx,
            "result_category": category,
        })

    df = pd.DataFrame(records)
    return df.sort_values(by="test_date").reset_index(drop=True)
