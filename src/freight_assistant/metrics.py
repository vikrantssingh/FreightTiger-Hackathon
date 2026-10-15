"""
Weekly shipment cost metric calculation.
"""

import pandas as pd

def compute_weekly_metrics(df_shipments: pd.DataFrame) -> pd.DataFrame:
    """
    Groups shipment records by route, route_type, and week_of.
    Computes cost per tonne per km:
        cost_per_tonne_km = total_freight_cost / sum(quantity_tonnes * distance_km)
    """
    df = df_shipments.copy()
    df["tonne_km"] = df["quantity_tonnes"] * df["distance_km"]
    
    # Aggregation
    grouped = df.groupby(["route", "route_type", "week_of"], as_index=False).agg(
        total_freight_cost=("freight_cost_inr", "sum"),
        total_tonne_km=("tonne_km", "sum"),
        shipment_count=("shipment_id", "count")
    )
    
    grouped["cost_per_tonne_km"] = grouped["total_freight_cost"] / grouped["total_tonne_km"]
    
    # Sort chronologically by route and week
    grouped = grouped.sort_values(["route", "week_of"]).reset_index(drop=True)
    return grouped
