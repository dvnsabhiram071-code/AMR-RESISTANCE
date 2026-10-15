"""
Unit tests for AI Copilot evidence structuring and offline fallback.
"""
import pytest
from src.copilot import generate_offline_explanation, query_amr_copilot


def test_offline_explanation_contains_all_five_sections():
    evidence = {
        "organism": "Klebsiella pneumoniae",
        "antibiotic": "Meropenem",
        "department": "ICU",
        "current_period": "2025-05-01 to 2025-05-31",
        "baseline_period": "2025-01-01 to 2025-04-30",
        "current_rate": 52.5,
        "baseline_rate": 18.0,
        "pct_point_change": 34.5,
        "current_tested": 40,
        "current_resistant": 21,
        "baseline_tested": 100,
        "baseline_resistant": 18,
        "trigger_reason": "Surge of +34.5 percentage points detected in ICU.",
        "caveats": "None. Sufficient sample sizes.",
    }
    explanation = generate_offline_explanation(evidence)
    assert "### 1. What Changed" in explanation
    assert "### 2. Evidence & Validated Metrics" in explanation
    assert "### 3. Why Flagged" in explanation
    assert "### 4. Data-Quality & Sample-Size Caveats" in explanation
    assert "### 5. Suggested Clinical & Epidemiological Verification Steps" in explanation
    assert "Klebsiella pneumoniae" in explanation
    assert "52.5%" in explanation
    assert "34.5%" in explanation


def test_copilot_fallback_when_invalid_key_or_offline():
    evidence = {
        "organism": "Pseudomonas aeruginosa",
        "antibiotic": "Meropenem",
        "department": "General Medicine",
        "current_rate": 35.0,
        "baseline_rate": 20.0,
        "pct_point_change": 15.0,
        "current_tested": 60,
        "current_resistant": 21,
        "baseline_tested": 120,
        "baseline_resistant": 24,
    }
    # Pass invalid key to trigger fallback
    result = query_amr_copilot(evidence, user_query="Explain this alert", api_key="invalid_dummy_key_12345")
    assert "### 1. What Changed" in result
    assert "Pseudomonas aeruginosa" in result
    assert "35.0%" in result
