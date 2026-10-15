"""
AMR Surveillance Analytics and Metric Engine.
Deterministic, pure functions for computing AMR statistics.
"""
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple, Any
import pandas as pd
import numpy as np


@dataclass
class AMRRateResult:
    organism: str
    antibiotic: str
    department: Optional[str]
    valid_tested: int
    resistant_count: int
    intermediate_count: int
    susceptible_count: int
    resistance_rate: Optional[float]  # None if valid_tested == 0
    susceptibility_rate: Optional[float]
    is_low_volume: bool
    caveat: Optional[str] = None


@dataclass
class WindowComparison:
    group_key: Tuple[str, str, str]  # (organism, antibiotic, department)
    organism: str
    antibiotic: str
    department: str
    current_start: str
    current_end: str
    baseline_start: str
    baseline_end: str
    current_tested: int
    current_resistant: int
    current_rate: Optional[float]
    baseline_tested: int
    baseline_resistant: int
    baseline_rate: Optional[float]
    pct_point_change: Optional[float]
    relative_change_pct: Optional[float]
    is_current_low_volume: bool
    is_baseline_low_volume: bool
    caveat: Optional[str] = None


def calculate_resistance_rate(
    df: pd.DataFrame,
    min_denominator: int = 30
) -> AMRRateResult:
    """
    Computes resistance and susceptibility rates for a given slice of data.
    Enforces that zero valid tests returns None, NEVER 0.0.
    """
    if df is None or df.empty:
        return AMRRateResult(
            organism="All",
            antibiotic="All",
            department=None,
            valid_tested=0,
            resistant_count=0,
            intermediate_count=0,
            susceptible_count=0,
            resistance_rate=None,
            susceptibility_rate=None,
            is_low_volume=True,
            caveat="No records available for the selected group/period."
        )

    valid_mask = df["result_category"].isin(["Resistant", "Intermediate", "Susceptible"])
    valid_df = df[valid_mask]
    valid_count = len(valid_df)

    if valid_count == 0:
        return AMRRateResult(
            organism=str(df["organism"].iloc[0]) if "organism" in df else "All",
            antibiotic=str(df["antibiotic"].iloc[0]) if "antibiotic" in df else "All",
            department=str(df["department"].iloc[0]) if "department" in df else None,
            valid_tested=0,
            resistant_count=0,
            intermediate_count=0,
            susceptible_count=0,
            resistance_rate=None,
            susceptibility_rate=None,
            is_low_volume=True,
            caveat="Zero valid susceptibility tests found."
        )

    res_count = int((valid_df["result_category"] == "Resistant").sum())
    int_count = int((valid_df["result_category"] == "Intermediate").sum())
    sus_count = int((valid_df["result_category"] == "Susceptible").sum())

    rate = round((res_count / valid_count) * 100, 2)
    sus_rate = round((sus_count / valid_count) * 100, 2)

    is_low = valid_count < min_denominator
    caveat = f"Low sample volume (N={valid_count} < {min_denominator}); interpret with caution." if is_low else None

    org = str(df["organism"].iloc[0]) if df["organism"].nunique() == 1 else "Multiple"
    abx = str(df["antibiotic"].iloc[0]) if df["antibiotic"].nunique() == 1 else "Multiple"
    dept = str(df["department"].iloc[0]) if "department" in df and df["department"].nunique() == 1 else "All"

    return AMRRateResult(
        organism=org,
        antibiotic=abx,
        department=dept,
        valid_tested=valid_count,
        resistant_count=res_count,
        intermediate_count=int_count,
        susceptible_count=sus_count,
        resistance_rate=rate,
        susceptibility_rate=sus_rate,
        is_low_volume=is_low,
        caveat=caveat,
    )


def compute_grouped_summary(
    df: pd.DataFrame,
    group_cols: List[str] = ["organism", "antibiotic", "department"],
    min_denominator: int = 30
) -> pd.DataFrame:
    """
    Computes grouped resistance statistics across specified dimensions.
    """
    if df is None or df.empty:
        cols = group_cols + [
            "valid_tested", "resistant_count", "intermediate_count",
            "susceptible_count", "resistance_rate", "is_low_volume"
        ]
        return pd.DataFrame(columns=cols)

    valid_mask = df["result_category"].isin(["Resistant", "Intermediate", "Susceptible"])
    valid_df = df[valid_mask]

    records = []
    for keys, group in valid_df.groupby(group_cols, dropna=False):
        if not isinstance(keys, tuple):
            keys = (keys,)
        row_dict = {col: keys[i] for i, col in enumerate(group_cols)}
        
        n_total = len(group)
        n_res = int((group["result_category"] == "Resistant").sum())
        n_int = int((group["result_category"] == "Intermediate").sum())
        n_sus = int((group["result_category"] == "Susceptible").sum())
        
        rate = round((n_res / n_total) * 100, 2) if n_total > 0 else np.nan
        is_low = n_total < min_denominator

        row_dict.update({
            "valid_tested": n_total,
            "resistant_count": n_res,
            "intermediate_count": n_int,
            "susceptible_count": n_sus,
            "resistance_rate": rate,
            "is_low_volume": is_low,
        })
        records.append(row_dict)

    res_df = pd.DataFrame(records)
    if not res_df.empty:
        res_df = res_df.sort_values(by=["valid_tested", "resistance_rate"], ascending=[False, False])
    return res_df


def build_antibiogram_matrix(
    df: pd.DataFrame,
    min_denominator: int = 10
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Generates organism-by-antibiotic matrices:
    1. Resistance rates matrix (%)
    2. Tested count (N) matrix
    """
    if df is None or df.empty:
        return pd.DataFrame(), pd.DataFrame()

    grouped = compute_grouped_summary(df, group_cols=["organism", "antibiotic"], min_denominator=min_denominator)
    if grouped.empty:
        return pd.DataFrame(), pd.DataFrame()

    rate_matrix = grouped.pivot(index="organism", columns="antibiotic", values="resistance_rate")
    count_matrix = grouped.pivot(index="organism", columns="antibiotic", values="valid_tested")

    return rate_matrix, count_matrix


def compare_time_windows(
    df: pd.DataFrame,
    current_start: str,
    current_end: str,
    baseline_start: str,
    baseline_end: str,
    group_cols: List[str] = ["organism", "antibiotic", "department"],
    min_denominator: int = 30
) -> List[WindowComparison]:
    """
    Compares two time intervals and calculates percentage-point shifts.
    """
    if df is None or df.empty:
        return []

    curr_mask = (df["test_date"] >= current_start) & (df["test_date"] <= current_end)
    base_mask = (df["test_date"] >= baseline_start) & (df["test_date"] <= baseline_end)

    curr_df = df[curr_mask]
    base_df = df[base_mask]

    curr_grouped = compute_grouped_summary(curr_df, group_cols=group_cols, min_denominator=min_denominator)
    base_grouped = compute_grouped_summary(base_df, group_cols=group_cols, min_denominator=min_denominator)

    key_cols = [c for c in group_cols if c in curr_grouped.columns]
    if not key_cols:
        return []

    merged = pd.merge(
        curr_grouped,
        base_grouped,
        on=key_cols,
        how="outer",
        suffixes=("_curr", "_base")
    )

    results = []
    for _, row in merged.iterrows():
        org = str(row.get("organism", "All"))
        abx = str(row.get("antibiotic", "All"))
        dept = str(row.get("department", "All"))
        group_key = (org, abx, dept)

        n_curr = int(row["valid_tested_curr"]) if pd.notna(row.get("valid_tested_curr")) else 0
        r_curr = int(row["resistant_count_curr"]) if pd.notna(row.get("resistant_count_curr")) else 0
        rate_curr = float(row["resistance_rate_curr"]) if pd.notna(row.get("resistance_rate_curr")) else None

        n_base = int(row["valid_tested_base"]) if pd.notna(row.get("valid_tested_base")) else 0
        r_base = int(row["resistant_count_base"]) if pd.notna(row.get("resistant_count_base")) else 0
        rate_base = float(row["resistance_rate_base"]) if pd.notna(row.get("resistance_rate_base")) else None

        pct_change = None
        rel_change = None
        if rate_curr is not None and rate_base is not None:
            pct_change = round(rate_curr - rate_base, 2)
            if rate_base > 0:
                rel_change = round(((rate_curr - rate_base) / rate_base) * 100, 2)

        curr_low = n_curr < min_denominator
        base_low = n_base < min_denominator

        caveats = []
        if n_curr == 0:
            caveats.append("No isolates in current period")
        elif curr_low:
            caveats.append(f"Current N={n_curr} < {min_denominator}")

        if n_base == 0:
            caveats.append("No isolates in baseline period")
        elif base_low:
            caveats.append(f"Baseline N={n_base} < {min_denominator}")

        caveat_str = "; ".join(caveats) if caveats else None

        results.append(WindowComparison(
            group_key=group_key,
            organism=org,
            antibiotic=abx,
            department=dept,
            current_start=current_start,
            current_end=current_end,
            baseline_start=baseline_start,
            baseline_end=baseline_end,
            current_tested=n_curr,
            current_resistant=r_curr,
            current_rate=rate_curr,
            baseline_tested=n_base,
            baseline_resistant=r_base,
            baseline_rate=rate_base,
            pct_point_change=pct_change,
            relative_change_pct=rel_change,
            is_current_low_volume=curr_low,
            is_baseline_low_volume=base_low,
            caveat=caveat_str
        ))

    return results
