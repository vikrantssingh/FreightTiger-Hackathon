"""
Data ingestion and validation module.
"""

from pathlib import Path
import pandas as pd
from typing import Tuple

REQUIRED_SHIPMENT_COLUMNS = [
    "shipment_id", "origin", "destination", "route_type",
    "material", "quantity_tonnes", "distance_km", "freight_cost_inr",
    "shipment_date", "transporter"
]

REQUIRED_NOTE_COLUMNS = [
    "note_id", "date", "applies_to", "note"
]

def calculate_monday_week_of(date_series: pd.Series) -> pd.Series:
    """
    Given a series of dates, returns the ISO formatted Monday date (YYYY-MM-DD)
    for the week containing each date (Monday to Sunday).
    """
    dt = pd.to_datetime(date_series)
    mondays = dt - pd.to_timedelta(dt.dt.weekday, unit="D")
    return mondays.dt.strftime("%Y-%m-%d")

def load_and_validate_shipments(file_path: Path) -> pd.DataFrame:
    """
    Loads shipment records CSV, validates columns and types,
    constructs route and week_of fields.
    """
    if not file_path.exists():
        raise FileNotFoundError(f"Shipment records file not found at: {file_path}")
    
    df = pd.read_csv(file_path)
    
    # Check required columns
    missing = [c for c in REQUIRED_SHIPMENT_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(f"Shipment CSV is missing required columns: {missing}")
    
    # Validate numeric fields
    for col in ["quantity_tonnes", "distance_km", "freight_cost_inr"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
        if (df[col] <= 0).any() or df[col].isna().any():
            raise ValueError(f"Invalid non-positive or null values found in {col}")
            
    # Clean string fields
    df["origin"] = df["origin"].astype(str).str.strip()
    df["destination"] = df["destination"].astype(str).str.strip()
    df["route_type"] = df["route_type"].astype(str).str.strip()
    df["route"] = df["origin"] + "-" + df["destination"]
    
    # Compute Monday week_of
    df["week_of"] = calculate_monday_week_of(df["shipment_date"])
    
    return df

def load_and_validate_notes(file_path: Path) -> pd.DataFrame:
    """
    Loads context notes CSV and validates structure.
    """
    if not file_path.exists():
        raise FileNotFoundError(f"Context notes file not found at: {file_path}")
        
    df = pd.read_csv(file_path)
    missing = [c for c in REQUIRED_NOTE_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(f"Context notes CSV is missing required columns: {missing}")
        
    df["note_id"] = df["note_id"].astype(str).str.strip()
    df["date"] = pd.to_datetime(df["date"]).dt.strftime("%Y-%m-%d")
    df["applies_to"] = df["applies_to"].astype(str).str.strip()
    df["note"] = df["note"].astype(str).str.strip()
    
    return df
