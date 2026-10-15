"""
Data Validation and Schema Enforcement Module for AMR Sentinel.
"""
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
import pandas as pd
import numpy as np


COLUMN_ALIASES = {
    "isolate_id": "record_id",
    "sample_date": "test_date",
    "collection_date": "test_date",
    "antimicrobial": "antibiotic",
    "susceptibility": "result_category",
    "ward": "department",
    "hospital_id": "hospital",
}

REQUIRED_CANONICAL_COLUMNS = [
    "record_id",
    "test_date",
    "organism",
    "antibiotic",
    "department",
    "specimen_type",
    "result_category",
]

VALID_CATEGORIES = {"Resistant", "Intermediate", "Susceptible"}


@dataclass
class ValidationReport:
    clean_df: pd.DataFrame
    excluded_df: pd.DataFrame
    total_rows: int
    valid_rows: int
    excluded_rows: int
    missing_values: Dict[str, int] = field(default_factory=dict)
    duplicate_count: int = 0
    invalid_category_count: int = 0
    invalid_date_count: int = 0
    date_min: Optional[str] = None
    date_max: Optional[str] = None


def normalize_column_names(df: pd.DataFrame) -> pd.DataFrame:
    """Standardize column names to canonical schema."""
    df = df.copy()
    rename_map = {}
    for col in df.columns:
        clean_col = col.strip().lower()
        if clean_col in COLUMN_ALIASES:
            rename_map[col] = COLUMN_ALIASES[clean_col]
        else:
            rename_map[col] = clean_col
    return df.rename(columns=rename_map)


def validate_and_clean_amr_data(raw_df: pd.DataFrame) -> ValidationReport:
    """
    Validates, cleans, and standardizes an incoming AMR dataframe.
    Quarantines rejected records with explicit reasons.
    """
    if raw_df is None or raw_df.empty:
        empty_clean = pd.DataFrame(columns=REQUIRED_CANONICAL_COLUMNS)
        empty_excluded = pd.DataFrame(columns=REQUIRED_CANONICAL_COLUMNS + ["exclusion_reason"])
        return ValidationReport(
            clean_df=empty_clean,
            excluded_df=empty_excluded,
            total_rows=0,
            valid_rows=0,
            excluded_rows=0,
            missing_values={},
            duplicate_count=0,
            invalid_category_count=0,
            invalid_date_count=0,
        )

    df = normalize_column_names(raw_df)

    # Check for missing required canonical columns
    missing_required = [col for col in REQUIRED_CANONICAL_COLUMNS if col not in df.columns]
    if missing_required:
        raise ValueError(f"Uploaded dataset is missing required column(s): {', '.join(missing_required)}")

    total_rows = len(df)
    missing_counts = df[REQUIRED_CANONICAL_COLUMNS].isna().sum().to_dict()

    reasons: List[Optional[str]] = [None] * total_rows

    # 1. Blank required fields
    for idx, row in df.iterrows():
        blank_fields = []
        for col in ["record_id", "organism", "antibiotic", "department"]:
            val = row[col]
            if pd.isna(val) or str(val).strip() == "":
                blank_fields.append(col)
        if blank_fields:
            reasons[idx] = f"Missing required field(s): {', '.join(blank_fields)}"

    # 2. Date parsing check
    parsed_dates = []
    invalid_date_count = 0
    for idx, val in enumerate(df["test_date"]):
        if reasons[idx] is not None:
            parsed_dates.append(pd.NaT)
            continue
        try:
            dt = pd.to_datetime(val)
            parsed_dates.append(dt)
        except Exception:
            parsed_dates.append(pd.NaT)
            reasons[idx] = f"Invalid date format: '{val}'"
            invalid_date_count += 1

    df["parsed_test_date"] = parsed_dates

    # 3. Category validation (S/I/R)
    invalid_category_count = 0
    normalized_categories = []
    for idx, val in enumerate(df["result_category"]):
        if reasons[idx] is not None:
            normalized_categories.append(str(val))
            continue
        if pd.isna(val) or str(val).strip() == "":
            reasons[idx] = "Result category is blank"
            normalized_categories.append("Blank")
            invalid_category_count += 1
            continue

        str_val = str(val).strip().capitalize()
        if str_val in VALID_CATEGORIES:
            normalized_categories.append(str_val)
        elif str_val in {"R", "Res"}:
            normalized_categories.append("Resistant")
        elif str_val in {"I", "Int"}:
            normalized_categories.append("Intermediate")
        elif str_val in {"S", "Sus"}:
            normalized_categories.append("Susceptible")
        else:
            reasons[idx] = f"Invalid result category: '{val}' (must be Resistant, Intermediate, Susceptible)"
            normalized_categories.append(str_val)
            invalid_category_count += 1

    df["result_category"] = normalized_categories

    # 4. Duplicate record check (same record_id or identical test entry)
    duplicate_count = 0
    seen_keys = set()
    for idx, row in df.iterrows():
        if reasons[idx] is not None:
            continue
        # Use record_id as key
        rec_id = str(row["record_id"]).strip()
        composite_key = (rec_id, str(row["organism"]).strip(), str(row["antibiotic"]).strip())
        if composite_key in seen_keys:
            reasons[idx] = f"Duplicate test entry detected for record_id '{rec_id}'"
            duplicate_count += 1
        else:
            seen_keys.add(composite_key)

    df["exclusion_reason"] = reasons

    clean_mask = df["exclusion_reason"].isna()
    clean_df = df[clean_mask].copy()
    clean_df["test_date"] = clean_df["parsed_test_date"].dt.strftime("%Y-%m-%d")
    clean_df = clean_df.drop(columns=["parsed_test_date", "exclusion_reason"])

    # Ensure clean string values
    for col in ["organism", "antibiotic", "department", "specimen_type", "state", "district"]:
        if col in clean_df.columns:
            clean_df[col] = clean_df[col].astype(str).str.strip()

    excluded_df = df[~clean_mask].copy()
    if "parsed_test_date" in excluded_df.columns:
        excluded_df = excluded_df.drop(columns=["parsed_test_date"])

    date_min = clean_df["test_date"].min() if not clean_df.empty else None
    date_max = clean_df["test_date"].max() if not clean_df.empty else None

    return ValidationReport(
        clean_df=clean_df,
        excluded_df=excluded_df,
        total_rows=total_rows,
        valid_rows=len(clean_df),
        excluded_rows=len(excluded_df),
        missing_values=missing_counts,
        duplicate_count=duplicate_count,
        invalid_category_count=invalid_category_count,
        invalid_date_count=invalid_date_count,
        date_min=date_min,
        date_max=date_max,
    )
