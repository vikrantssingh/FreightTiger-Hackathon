"""
Unit tests for trailing 8-week history and peer comparisons.
"""

import pandas as pd
import pytest
from src.freight_assistant.baselines import compute_baselines

def test_trailing_history_strictly_prior_weeks():
    # 3 consecutive weeks for Route A
    data = {
        "route": ["RouteA", "RouteA", "RouteA"],
        "route_type": ["Short", "Short", "Short"],
        "week_of": ["2024-01-01", "2024-01-08", "2024-01-15"],
        "cost_per_tonne_km": [2.0, 3.0, 4.0]
    }
    df = pd.DataFrame(data)
    res = compute_baselines(df, window_weeks=8)
    
    # Week 1: no prior history
    assert pd.isna(res.iloc[0]["past_8w_avg"])
    assert res.iloc[0]["prior_weeks_count"] == 0
    
    # Week 2: only Week 1 is prior (avg = 2.0)
    assert res.iloc[1]["past_8w_avg"] == 2.0
    assert res.iloc[1]["prior_weeks_count"] == 1
    # diff = (3.0 - 2.0) / 2.0 * 100 = +50.0%
    assert pytest.approx(res.iloc[1]["vs_own_history_pct"], 0.1) == 50.0
    
    # Week 3: Weeks 1 & 2 are prior (avg = (2+3)/2 = 2.5)
    assert res.iloc[2]["past_8w_avg"] == 2.5
    assert res.iloc[2]["prior_weeks_count"] == 2
    # diff = (4.0 - 2.5) / 2.5 * 100 = +60.0%
    assert pytest.approx(res.iloc[2]["vs_own_history_pct"], 0.1) == 60.0

def test_peer_baseline_excludes_self():
    # 3 routes in the same week with same route_type
    data = {
        "route": ["RouteA", "RouteB", "RouteC"],
        "route_type": ["Short", "Short", "Short"],
        "week_of": ["2024-01-01", "2024-01-01", "2024-01-01"],
        "cost_per_tonne_km": [10.0, 4.0, 6.0]
    }
    df = pd.DataFrame(data)
    res = compute_baselines(df, window_weeks=8)
    
    # RouteA peers are RouteB (4.0) and RouteC (6.0) -> peer_avg = 5.0
    row_a = res[res["route"] == "RouteA"].iloc[0]
    assert row_a["peer_avg"] == 5.0
    # vs_peer = (10.0 - 5.0) / 5.0 * 100 = +100.0%
    assert pytest.approx(row_a["vs_similar_routes_pct"], 0.1) == 100.0
