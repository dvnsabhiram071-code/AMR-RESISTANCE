"""
Unit tests for AMR surveillance metrics and deterministic calculation rules.
"""
import pytest
import pandas as pd
import numpy as np
from src.metrics import calculate_resistance_rate, compute_grouped_summary, compare_time_windows


def test_hand_calculated_resistance_rate():
    # Exactly matching blueprint Page 3: 30 resistant, 10 intermediate, 60 susceptible = 30.0%
    data = (
        [{"organism": "K. pneumoniae", "antibiotic": "Meropenem", "result_category": "Resistant"}] * 30 +
        [{"organism": "K. pneumoniae", "antibiotic": "Meropenem", "result_category": "Intermediate"}] * 10 +
        [{"organism": "K. pneumoniae", "antibiotic": "Meropenem", "result_category": "Susceptible"}] * 60
    )
    df = pd.DataFrame(data)
    result = calculate_resistance_rate(df)
    assert result.valid_tested == 100
    assert result.resistant_count == 30
    assert result.intermediate_count == 10
    assert result.susceptible_count == 60
    assert result.resistance_rate == 30.0
    assert result.susceptibility_rate == 60.0
    assert result.is_low_volume is False
    assert result.caveat is None


def test_zero_valid_tests_returns_none():
    # Acceptance check: zero valid tests returns None, NEVER 0.0%
    empty_df = pd.DataFrame(columns=["organism", "antibiotic", "result_category"])
    result = calculate_resistance_rate(empty_df)
    assert result.valid_tested == 0
    assert result.resistance_rate is None
    assert result.is_low_volume is True


def test_low_volume_caveat():
    # If sample size < min_denominator (default 30)
    data = (
        [{"organism": "E. coli", "antibiotic": "Amikacin", "result_category": "Resistant"}] * 2 +
        [{"organism": "E. coli", "antibiotic": "Amikacin", "result_category": "Susceptible"}] * 8
    )
    df = pd.DataFrame(data)
    result = calculate_resistance_rate(df, min_denominator=30)
    assert result.valid_tested == 10
    assert result.resistance_rate == 20.0
    assert result.is_low_volume is True
    assert "Low sample volume" in (result.caveat or "")


def test_window_comparison_percentage_point_change():
    base_data = [
        {"test_date": "2025-01-15", "organism": "E. coli", "antibiotic": "Cipro", "department": "ICU", "result_category": "Resistant"}
    ] * 20 + [
        {"test_date": "2025-01-15", "organism": "E. coli", "antibiotic": "Cipro", "department": "ICU", "result_category": "Susceptible"}
    ] * 80  # 20.0% rate

    curr_data = [
        {"test_date": "2025-06-15", "organism": "E. coli", "antibiotic": "Cipro", "department": "ICU", "result_category": "Resistant"}
    ] * 40 + [
        {"test_date": "2025-06-15", "organism": "E. coli", "antibiotic": "Cipro", "department": "ICU", "result_category": "Susceptible"}
    ] * 60  # 40.0% rate

    df = pd.DataFrame(base_data + curr_data)
    comparisons = compare_time_windows(
        df=df,
        current_start="2025-06-01",
        current_end="2025-06-30",
        baseline_start="2025-01-01",
        baseline_end="2025-01-31",
        min_denominator=20
    )
    assert len(comparisons) == 1
    comp = comparisons[0]
    assert comp.baseline_rate == 20.0
    assert comp.current_rate == 40.0
    assert comp.pct_point_change == 20.0  # +20.0% point shift
    assert comp.relative_change_pct == 100.0  # Doubled
