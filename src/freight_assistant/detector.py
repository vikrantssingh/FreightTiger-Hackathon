"""
Anomaly detection module.
Identifies route-weeks where shipping costs look out of the ordinary.
"""

import pandas as pd
from src.freight_assistant.config import AppConfig, DEFAULT_CONFIG

def detect_anomalies(df_baselines: pd.DataFrame, config: AppConfig = DEFAULT_CONFIG) -> pd.DataFrame:
    """
    Flags route-weeks where cost is rising and exceeds thresholds
    compared to own history (trailing 8w) OR similar routes (same week).
    """
    df = df_baselines.copy()
    
    own_thresh = config.vs_own_threshold * 100.0
    peer_thresh = config.vs_peer_threshold * 100.0
    
    # Anomaly condition:
    # Rising and out of ordinary vs own history OR vs similar routes
    df["is_own_anomaly"] = (df["vs_own_history_pct"].notna()) & (df["vs_own_history_pct"] >= own_thresh)
    df["is_peer_anomaly"] = (df["vs_similar_routes_pct"].notna()) & (df["vs_similar_routes_pct"] >= peer_thresh)
    
    df["is_anomaly"] = df["is_own_anomaly"] | df["is_peer_anomaly"]
    
    return df
