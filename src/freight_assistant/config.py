"""
Configuration settings for Freight Tiger Smart Assistant.
"""

from pathlib import Path
from dataclasses import dataclass

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

@dataclass(frozen=True)
class AppConfig:
    # File Paths
    shipment_records_path: Path = PROJECT_ROOT / "data" / "shipment_records.csv"
    context_notes_path: Path = PROJECT_ROOT / "data" / "context_notes.csv"
    output_path: Path = PROJECT_ROOT / "outputs" / "output.csv"
    token_cost_log_path: Path = PROJECT_ROOT / "outputs" / "token_cost_log.json"
    labeled_eval_set_path: Path = PROJECT_ROOT / "evaluation" / "labeled_eval_set.csv"

    # Baseline & Anomaly Detection Parameters
    own_history_window_weeks: int = 8
    # A route-week is flagged if cost rises and exceeds either threshold:
    vs_own_threshold: float = 0.15   # 15% increase vs own trailing 8w average
    vs_peer_threshold: float = 0.20  # 20% increase vs same-week peer average
    
    # Retrieval and Guardrail Parameters
    date_proximity_days: int = 21    # Maximum window to consider notes around the week
    random_seed: int = 42

    # Model Parameters
    model_name: str = "deterministic-rag-tfidf"
    temperature: float = 0.0

DEFAULT_CONFIG = AppConfig()
