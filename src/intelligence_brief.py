"""
Intelligence Brief and Automated Epidemiological Ranking Engine for AMR Sentinel.
"""
from typing import List, Dict, Any, Optional
import pandas as pd
from src.metrics import compare_time_windows, WindowComparison


def generate_intelligence_brief(
    df: pd.DataFrame,
    current_days: int = 60,
    baseline_days: int = 180,
    min_denominator: int = 15,
    top_n: int = 10,
) -> Dict[str, Any]:
    """
    Ranks the largest observed shifts across organism-antibiotic-department groups.
    Distinguishes raw percentage-point changes from statistical sample-size confidence.
    """
    if df is None or df.empty or "test_date" not in df:
        return {"rankings": [], "summary_stats": {}}

    dates = pd.to_datetime(df["test_date"]).dropna()
    if dates.empty:
        return {"rankings": [], "summary_stats": {}}

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
        min_denominator=min_denominator
    )

    valid_comparisons = [c for c in comparisons if c.pct_point_change is not None]

    # Sort by absolute percentage point increase descending
    valid_comparisons.sort(key=lambda x: -(x.pct_point_change or 0))

    ranked_items = []
    for rank, comp in enumerate(valid_comparisons[:top_n], start=1):
        is_reliable = (not comp.is_current_low_volume) and (not comp.is_baseline_low_volume)
        classification = "High-Confidence Shift" if is_reliable else "Observed Shift (Low-Volume Caveat)"

        ranked_items.append({
            "rank": rank,
            "organism": comp.organism,
            "antibiotic": comp.antibiotic,
            "department": comp.department,
            "current_period": f"{comp.current_start} to {comp.current_end}",
            "baseline_period": f"{comp.baseline_start} to {comp.baseline_end}",
            "current_rate": comp.current_rate,
            "baseline_rate": comp.baseline_rate,
            "pct_point_change": comp.pct_point_change,
            "current_tested": comp.current_tested,
            "current_resistant": comp.current_resistant,
            "baseline_tested": comp.baseline_tested,
            "baseline_resistant": comp.baseline_resistant,
            "confidence": classification,
            "is_reliable": is_reliable,
            "caveat": comp.caveat,
        })

    summary_stats = {
        "total_groups_compared": len(comparisons),
        "shifts_exceeding_10pct": len([c for c in valid_comparisons if c.pct_point_change and c.pct_point_change >= 10.0]),
        "shifts_exceeding_20pct": len([c for c in valid_comparisons if c.pct_point_change and c.pct_point_change >= 20.0]),
        "current_window": f"{curr_start} to {curr_end}",
        "baseline_window": f"{base_start} to {base_end}",
    }

    return {"rankings": ranked_items, "summary_stats": summary_stats}
