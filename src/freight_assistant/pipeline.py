"""
End-to-end pipeline runner for Freight Tiger Smart Shipping Cost Assistant.
"""

from pathlib import Path
from typing import Optional, Tuple
import pandas as pd

from src.freight_assistant.config import AppConfig, DEFAULT_CONFIG
from src.freight_assistant.ingestion import load_and_validate_shipments, load_and_validate_notes
from src.freight_assistant.metrics import compute_weekly_metrics
from src.freight_assistant.baselines import compute_baselines
from src.freight_assistant.detector import detect_anomalies
from src.freight_assistant.vector_store import ContextNoteRetriever
from src.freight_assistant.guardrails import evaluate_guardrails
from src.freight_assistant.explainer import generate_explanation
from src.freight_assistant.cost_tracker import CostTracker

def run_pipeline(
    config: AppConfig = DEFAULT_CONFIG,
    anomalies_only: bool = True
) -> Tuple[pd.DataFrame, CostTracker]:
    """
    Executes the full pipeline:
    1. Loads and validates datasets
    2. Aggregates weekly cost per tonne-km
    3. Calculates 8w trailing and peer baselines
    4. Detects unusual cost rises
    5. Retrieves context notes via RAG
    6. Applies hallucination guardrails
    7. Formats output matching sample_output_format.csv
    """
    tracker = CostTracker(
        model_name=config.model_name,
        temperature=config.temperature
    )

    # 1. Ingestion
    df_shipments = load_and_validate_shipments(config.shipment_records_path)
    df_notes = load_and_validate_notes(config.context_notes_path)

    # 2. Weekly Metrics
    df_weekly = compute_weekly_metrics(df_shipments)

    # 3. Baselines
    df_baselines = compute_baselines(df_weekly, window_weeks=config.own_history_window_weeks)

    # 4. Anomaly Detection
    df_flagged = detect_anomalies(df_baselines, config=config)

    # 5. RAG Retriever Setup
    retriever = ContextNoteRetriever(df_notes)

    # 6. Guardrail Verification and Explanations
    output_rows = []

    for _, row in df_flagged.iterrows():
        route = row["route"]
        week_of = row["week_of"]
        cost = row["cost_per_tonne_km"]
        is_anomaly = bool(row["is_anomaly"])

        if is_anomaly:
            # Query vector store for context notes
            candidates = retriever.retrieve_candidates(route, week_of, top_k=5)
            
            # Guardrail evaluation
            is_justified, matched_note, closest_note, rejection_detail = evaluate_guardrails(
                route, week_of, candidates
            )
            
            # Explanation generation
            flagged_val, note_id_val, reason_val = generate_explanation(
                route=route,
                week_of=week_of,
                is_anomaly=True,
                is_justified=is_justified,
                matched_note=matched_note,
                closest_note=closest_note,
                rejection_detail=rejection_detail
            )

            # Record token usage (prompt ~ route/week/notes, completion ~ reason)
            prompt_str = f"Route: {route}, Week: {week_of}, Candidates: {[c['note'].note_id for c in candidates]}"
            p_tok = tracker.estimate_tokens_from_text(prompt_str)
            c_tok = tracker.estimate_tokens_from_text(reason_val)
            tracker.record_call(p_tok, c_tok)
        else:
            flagged_val, note_id_val, reason_val = generate_explanation(
                route=route,
                week_of=week_of,
                is_anomaly=False,
                is_justified=False,
                matched_note=None,
                closest_note=None,
                rejection_detail=None
            )

        output_rows.append({
            "route": route,
            "week_of": week_of,
            "cost_per_tonne_km": round(cost, 2),
            "vs_own_history": row["vs_own_history"],
            "vs_similar_routes": row["vs_similar_routes"],
            "flagged": flagged_val,
            "matched_note_id": note_id_val,
            "reason": reason_val
        })

    df_output = pd.DataFrame(output_rows)

    # Filter to anomalies only if requested (matching sample_output_format.csv behavior)
    if anomalies_only:
        df_output = df_output[df_output["flagged"] != "No"].reset_index(drop=True)

    # Ensure stable deterministic sort: route ASC, week_of ASC
    df_output = df_output.sort_values(["route", "week_of"]).reset_index(drop=True)

    # Save outputs
    config.output_path.parent.mkdir(parents=True, exist_ok=True)
    df_output.to_csv(config.output_path, index=False)
    tracker.save_json(config.token_cost_log_path)

    return df_output, tracker
