"""
Unit tests for data validation, schema enforcement, and quarantine logging.
"""
import pytest
import pandas as pd
from src.validation import validate_and_clean_amr_data, normalize_column_names


def test_normalize_column_names():
    df = pd.DataFrame(columns=["isolate_id", "sample_date", "antimicrobial", "susceptibility", "ward"])
    normalized = normalize_column_names(df)
    assert "record_id" in normalized.columns
    assert "test_date" in normalized.columns
    assert "antibiotic" in normalized.columns
    assert "result_category" in normalized.columns
    assert "department" in normalized.columns


def test_validation_clean_data():
    raw_data = {
        "record_id": ["REC-001", "REC-002", "REC-003"],
        "test_date": ["2025-05-01", "2025-05-02", "2025-05-03"],
        "organism": ["Escherichia coli", "Klebsiella pneumoniae", "Pseudomonas aeruginosa"],
        "antibiotic": ["Ciprofloxacin", "Meropenem", "Gentamicin"],
        "department": ["ICU", "General Medicine", "Surgery"],
        "specimen_type": ["Urine", "Blood", "Wound Swab"],
        "result_category": ["Resistant", "Susceptible", "Intermediate"],
    }
    df = pd.DataFrame(raw_data)
    report = validate_and_clean_amr_data(df)
    assert report.total_rows == 3
    assert report.valid_rows == 3
    assert report.excluded_rows == 0
    assert report.duplicate_count == 0


def test_validation_quarantines_invalid_category():
    raw_data = {
        "record_id": ["REC-001", "REC-002"],
        "test_date": ["2025-05-01", "2025-05-02"],
        "organism": ["E. coli", "E. coli"],
        "antibiotic": ["Cipro", "Cipro"],
        "department": ["ICU", "ICU"],
        "specimen_type": ["Blood", "Blood"],
        "result_category": ["Resistant", "INVALID_VAL"],
    }
    df = pd.DataFrame(raw_data)
    report = validate_and_clean_amr_data(df)
    assert report.valid_rows == 1
    assert report.excluded_rows == 1
    assert "Invalid result category" in report.excluded_df.iloc[0]["exclusion_reason"]


def test_validation_quarantines_duplicate_records():
    raw_data = {
        "record_id": ["REC-001", "REC-001"],  # Duplicate
        "test_date": ["2025-05-01", "2025-05-01"],
        "organism": ["E. coli", "E. coli"],
        "antibiotic": ["Cipro", "Cipro"],
        "department": ["ICU", "ICU"],
        "specimen_type": ["Blood", "Blood"],
        "result_category": ["Resistant", "Resistant"],
    }
    df = pd.DataFrame(raw_data)
    report = validate_and_clean_amr_data(df)
    assert report.valid_rows == 1
    assert report.excluded_rows == 1
    assert "Duplicate" in report.excluded_df.iloc[0]["exclusion_reason"]


def test_validation_quarantines_blank_fields():
    raw_data = {
        "record_id": ["REC-001", "REC-002"],
        "test_date": ["2025-05-01", "2025-05-02"],
        "organism": ["E. coli", ""],  # Blank organism
        "antibiotic": ["Cipro", "Cipro"],
        "department": ["ICU", "ICU"],
        "specimen_type": ["Blood", "Blood"],
        "result_category": ["Resistant", "Susceptible"],
    }
    df = pd.DataFrame(raw_data)
    report = validate_and_clean_amr_data(df)
    assert report.valid_rows == 1
    assert report.excluded_rows == 1
