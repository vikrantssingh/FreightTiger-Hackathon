"""
Unit tests for weekly cost per tonne-km metric calculation.
"""

import pandas as pd
import pytest
from src.freight_assistant.metrics import compute_weekly_metrics

def test_compute_weekly_metrics():
    # 2 sample shipments for the same route and week
    data = {
        "shipment_id": ["S1", "S2"],
        "route": ["Delhi-Jaipur", "Delhi-Jaipur"],
        "route_type": ["Short", "Short"],
        "week_of": ["2024-11-11", "2024-11-11"],
        "quantity_tonnes": [10.0, 20.0],
        "distance_km": [200.0, 200.0],
        "freight_cost_inr": [10000.0, 20000.0]
    }
    df = pd.DataFrame(data)
    result = compute_weekly_metrics(df)
    
    assert len(result) == 1
    row = result.iloc[0]
    assert row["route"] == "Delhi-Jaipur"
    assert row["week_of"] == "2024-11-11"
    # total_freight = 30000
    # total_tonne_km = (10*200) + (20*200) = 2000 + 4000 = 6000
    # cost_per_tonne_km = 30000 / 6000 = 5.0
    assert row["total_freight_cost"] == 30000.0
    assert row["total_tonne_km"] == 6000.0
    assert pytest.approx(row["cost_per_tonne_km"], 0.001) == 5.0
