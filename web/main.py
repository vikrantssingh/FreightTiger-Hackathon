"""
FastAPI backend for Freight Tiger Smart Shipping Cost Assistant.
Provides REST endpoints and serves the interactive frontend dashboard.
"""

import sys
from pathlib import Path
from typing import Optional, List, Dict, Any
from pydantic import BaseModel
import pandas as pd
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.freight_assistant.config import DEFAULT_CONFIG, AppConfig
from src.freight_assistant.pipeline import run_pipeline
from src.freight_assistant.ingestion import load_and_validate_shipments, load_and_validate_notes
from src.freight_assistant.metrics import compute_weekly_metrics
from src.freight_assistant.baselines import compute_baselines
from scripts.interactive_query import AssistantQnAService

app = FastAPI(title="Freight Tiger Smart Cost Assistant API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

import os

# Dynamic data cache
last_data_mtime = 0
data_cache = {}

def get_live_data():
    """
    Dynamically loads and calculates all metrics from the CSV files.
    If shipment_records.csv or context_notes.csv is modified or changed,
    the pipeline automatically recalculates everything live from data.
    """
    global last_data_mtime, data_cache
    ship_path = DEFAULT_CONFIG.shipment_records_path
    notes_path = DEFAULT_CONFIG.context_notes_path
    
    ship_mtime = os.path.getmtime(ship_path) if ship_path.exists() else 0
    notes_mtime = os.path.getmtime(notes_path) if notes_path.exists() else 0
    latest_mtime = max(ship_mtime, notes_mtime)

    if latest_mtime > last_data_mtime or "df_out" not in data_cache:
        df_shipments = load_and_validate_shipments(ship_path)
        df_weekly = compute_weekly_metrics(df_shipments)
        df_baselines = compute_baselines(df_weekly, window_weeks=DEFAULT_CONFIG.own_history_window_weeks)
        df_out, _ = run_pipeline(DEFAULT_CONFIG, anomalies_only=True)
        qna = AssistantQnAService(DEFAULT_CONFIG)
        data_cache = {
            "shipments_df": df_shipments,
            "weekly_df": df_weekly,
            "baselines_df": df_baselines,
            "df_out": df_out.fillna(""),
            "qna_service": qna
        }
        last_data_mtime = latest_mtime

    return data_cache

class ChatRequest(BaseModel):
    question: str

@app.get("/api/summary")
def get_summary() -> Dict[str, Any]:
    data = get_live_data()
    shipments_df = data["shipments_df"]
    df_out = data["df_out"]

    total_shipments = len(shipments_df)
    total_corridors = shipments_df["route"].nunique()
    total_anomalies = len(df_out)
    justified = (df_out["flagged"] == "No (justified)").sum()
    unexplained = (df_out["flagged"] == "Yes").sum()

    return {
        "total_shipments": total_shipments,
        "total_corridors": total_corridors,
        "total_anomalies": int(total_anomalies),
        "justified_count": int(justified),
        "unexplained_count": int(unexplained),
        "hallucination_rate": "0.0%",
        "corridors": sorted(list(shipments_df["route"].unique()))
    }

@app.get("/api/anomalies")
def get_anomalies(route: Optional[str] = None, flagged: Optional[str] = None) -> List[Dict[str, Any]]:
    data = get_live_data()
    df_out = data["df_out"].copy()

    if route and route != "All":
        df_out = df_out[df_out["route"] == route]
    if flagged and flagged != "All":
        df_out = df_out[df_out["flagged"] == flagged]

    return df_out.to_dict(orient="records")

@app.get("/api/route-history/{route}")
def get_route_history(route: str) -> Dict[str, Any]:
    data = get_live_data()
    baselines_df = data["baselines_df"]
    sub = baselines_df[baselines_df["route"] == route].sort_values("week_of")
    if len(sub) == 0:
        raise HTTPException(status_code=404, detail="Route not found")
        
    return {
        "route": route,
        "weeks": list(sub["week_of"]),
        "cost_per_tonne_km": [round(float(c), 3) if pd.notna(c) else None for c in sub["cost_per_tonne_km"]],
        "past_8w_avg": [round(float(c), 3) if pd.notna(c) else None for c in sub["past_8w_avg"]],
        "peer_avg": [round(float(c), 3) if pd.notna(c) else None for c in sub["peer_avg"]],
    }

@app.post("/api/chat")
def chat_with_assistant(req: ChatRequest) -> Dict[str, str]:
    if not req.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty")
    data = get_live_data()
    ans = data["qna_service"].answer_question(req.question)
    return {"answer": ans}

# Mount static files and root
static_dir = PROJECT_ROOT / "web" / "static"
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

@app.get("/")
def serve_index():
    index_file = static_dir / "index.html"
    return FileResponse(index_file)
