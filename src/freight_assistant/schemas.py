"""
Data models and schema definitions.
"""

from dataclasses import dataclass
from typing import Optional

@dataclass
class ShipmentRecord:
    shipment_id: str
    origin: str
    destination: str
    route_type: str
    material: str
    quantity_tonnes: float
    distance_km: float
    freight_cost_inr: float
    shipment_date: str
    transporter: str

@dataclass
class ContextNote:
    note_id: str
    date: str
    applies_to: str
    note: str

@dataclass
class RouteWeekMetrics:
    route: str
    route_type: str
    week_of: str
    cost_per_tonne_km: float
    past_8w_avg: Optional[float]
    vs_own_history_pct: Optional[float]
    prior_weeks_count: int
    peer_avg: Optional[float]
    vs_similar_routes_pct: Optional[float]
    peer_count: int
    is_anomaly: bool

@dataclass
class EvaluationRecord:
    route: str
    week_of: str
    cost_per_tonne_km: float
    vs_own_history_str: str
    vs_similar_routes_str: str
    flagged: str
    matched_note_id: str
    reason: str
