"""
Baseline computation module.
Computes trailing 8-week rolling average and peer route average according to exact specifications.
"""

import pandas as pd
import numpy as np
from typing import Optional

def format_vs_own_history(pct: Optional[float]) -> str:
    """Formats percentage change vs route's own history."""
    if pct is None or np.isnan(pct):
        return "N/A (no prior history)"
    return f"{pct:+.1f}% vs this route's past average"

def format_vs_similar_routes(pct: Optional[float]) -> str:
    """Formats percentage change vs peer routes."""
    if pct is None or np.isnan(pct):
        return "N/A (no peer routes)"
    return f"{pct:+.1f}% vs similar-length routes this week"

def compute_baselines(df_weekly: pd.DataFrame, window_weeks: int = 8) -> pd.DataFrame:
    """
    Computes:
    1. vs. own history: Trailing N-week (default 8) rolling average cost per tonne-km,
       using strictly weeks before the current week (no lookahead).
       If fewer than N prior weeks exist, uses all prior weeks available.
    2. vs. similar routes: Same-week average cost per tonne-km across all OTHER routes
       sharing the same route_type (Short / Medium / Long), excluding the route itself.
    """
    df = df_weekly.sort_values(["route", "week_of"]).reset_index(drop=True)
    
    rows = []
    
    for idx, row in df.iterrows():
        route = row["route"]
        route_type = row["route_type"]
        week = row["week_of"]
        current_cost = row["cost_per_tonne_km"]
        
        # 1. Trailing prior weeks for own history
        prior_records = df[(df["route"] == route) & (df["week_of"] < week)].sort_values("week_of")
        trailing_records = prior_records.tail(window_weeks)
        prior_count = len(trailing_records)
        
        if prior_count > 0:
            past_8w_avg = trailing_records["cost_per_tonne_km"].mean()
            vs_own_pct = ((current_cost - past_8w_avg) / past_8w_avg) * 100.0
        else:
            past_8w_avg = np.nan
            vs_own_pct = np.nan
            
        # 2. Similar routes (same week_of, same route_type, route != current_route)
        peers = df[
            (df["week_of"] == week) &
            (df["route_type"] == route_type) &
            (df["route"] != route)
        ]
        peer_count = len(peers)
        
        if peer_count > 0:
            peer_avg = peers["cost_per_tonne_km"].mean()
            vs_peer_pct = ((current_cost - peer_avg) / peer_avg) * 100.0
        else:
            peer_avg = np.nan
            vs_peer_pct = np.nan
            
        rows.append({
            "route": route,
            "route_type": route_type,
            "week_of": week,
            "cost_per_tonne_km": current_cost,
            "past_8w_avg": past_8w_avg,
            "vs_own_history_pct": vs_own_pct,
            "prior_weeks_count": prior_count,
            "peer_avg": peer_avg,
            "vs_similar_routes_pct": vs_peer_pct,
            "peer_count": peer_count,
            "vs_own_history": format_vs_own_history(vs_own_pct),
            "vs_similar_routes": format_vs_similar_routes(vs_peer_pct)
        })
        
    return pd.DataFrame(rows)
