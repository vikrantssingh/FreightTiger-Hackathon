"""
Unit tests for week_of (Monday date) calculations.
"""

import pytest
import pandas as pd
from src.freight_assistant.ingestion import calculate_monday_week_of

def test_monday_stays_monday():
    dates = pd.Series(["2024-01-01", "2024-01-08", "2024-11-11", "2025-01-20"])
    weeks = calculate_monday_week_of(dates)
    expected = ["2024-01-01", "2024-01-08", "2024-11-11", "2025-01-20"]
    assert list(weeks) == expected

def test_midweek_and_sunday_map_to_monday():
    # 2024-01-01 is Monday, 2024-01-03 is Wednesday, 2024-01-07 is Sunday
    dates = pd.Series(["2024-01-02", "2024-01-03", "2024-01-06", "2024-01-07"])
    weeks = calculate_monday_week_of(dates)
    assert all(w == "2024-01-01" for w in weeks)

def test_year_boundary_crossing():
    # 2024-12-30 was Monday, 2025-01-01 was Wednesday, 2025-01-05 was Sunday
    dates = pd.Series(["2024-12-31", "2025-01-01", "2025-01-05"])
    weeks = calculate_monday_week_of(dates)
    assert all(w == "2024-12-30" for w in weeks)
