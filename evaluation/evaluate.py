"""
Evaluation harness: scores pipeline outputs against curated ground-truth cases.
"""

from pathlib import Path
import pandas as pd
from typing import Dict, Any

from src.freight_assistant.config import DEFAULT_CONFIG, AppConfig
from src.freight_assistant.pipeline import run_pipeline

def run_evaluation(
    eval_csv_path: Path = DEFAULT_CONFIG.labeled_eval_set_path,
    config: AppConfig = DEFAULT_CONFIG
) -> Dict[str, Any]:
    """
    Evaluates pipeline accuracy against known labeled scenarios:
    - Flag decision accuracy (Justified vs Unexplained)
    - Note attribution accuracy (Exact note cited or correctly blank)
    - Numeric cost calculation match
    - Hallucination rate (false claims of justification)
    """
    df_eval = pd.read_csv(eval_csv_path)
    df_pipeline, _ = run_pipeline(config=config, anomalies_only=False)

    total_cases = len(df_eval)
    flag_matches = 0
    note_matches = 0
    numeric_matches = 0
    hallucinations = 0

    case_results = []

    for _, row in df_eval.iterrows():
        route = row["route"]
        week = row["week_of"]
        exp_flagged = row["expected_flagged"]
        exp_note = str(row["expected_note_id"]) if pd.notna(row["expected_note_id"]) else ""
        exp_cost = float(row["expected_cost"])

        match = df_pipeline[(df_pipeline["route"] == route) & (df_pipeline["week_of"] == week)]
        if len(match) == 0:
            case_results.append({
                "scenario": row["scenario_description"],
                "route": route,
                "week_of": week,
                "status": "FAIL",
                "reason": "Route-week missing from pipeline output"
            })
            continue

        p_row = match.iloc[0]
        actual_flagged = p_row["flagged"]
        actual_note = str(p_row["matched_note_id"]) if pd.notna(p_row["matched_note_id"]) else ""
        actual_cost = float(p_row["cost_per_tonne_km"])

        is_flag_correct = (actual_flagged == exp_flagged)
        is_note_correct = (actual_note == exp_note)
        is_cost_correct = (abs(actual_cost - exp_cost) <= 0.02)

        if is_flag_correct:
            flag_matches += 1
        if is_note_correct:
            note_matches += 1
        if is_cost_correct:
            numeric_matches += 1

        # Check for hallucination: claiming a note justified it when none should apply
        if exp_note == "" and actual_note != "":
            hallucinations += 1
            is_hallucination = True
        else:
            is_hallucination = False

        status = "PASS" if (is_flag_correct and is_note_correct and is_cost_correct) else "FAIL"
        case_results.append({
            "scenario": row["scenario_description"],
            "route": route,
            "week_of": week,
            "expected_flag": exp_flagged,
            "actual_flag": actual_flagged,
            "expected_note": exp_note,
            "actual_note": actual_note,
            "expected_cost": exp_cost,
            "actual_cost": actual_cost,
            "hallucination": is_hallucination,
            "status": status
        })

    flag_acc = (flag_matches / total_cases) * 100.0
    note_acc = (note_matches / total_cases) * 100.0
    num_acc = (numeric_matches / total_cases) * 100.0
    hallucination_rate = (hallucinations / total_cases) * 100.0

    return {
        "total_test_cases": total_cases,
        "flag_accuracy_pct": flag_acc,
        "note_attribution_accuracy_pct": note_acc,
        "numeric_cost_accuracy_pct": num_acc,
        "hallucination_rate_pct": hallucination_rate,
        "case_details": case_results
    }
