"""
CLI entry point to execute Freight Tiger Smart Assistant pipeline.
"""

import sys
import argparse
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.freight_assistant.config import DEFAULT_CONFIG, AppConfig
from src.freight_assistant.pipeline import run_pipeline

def main():
    parser = argparse.ArgumentParser(description="Run Freight Tiger Smart Shipping Cost Assistant")
    parser.add_argument("--shipments", type=str, default=str(DEFAULT_CONFIG.shipment_records_path), help="Path to shipment records CSV")
    parser.add_argument("--notes", type=str, default=str(DEFAULT_CONFIG.context_notes_path), help="Path to context notes CSV")
    parser.add_argument("--output", type=str, default=str(DEFAULT_CONFIG.output_path), help="Path for output CSV")
    parser.add_argument("--log", type=str, default=str(DEFAULT_CONFIG.token_cost_log_path), help="Path for token/cost JSON log")
    parser.add_argument("--all-rows", action="store_true", help="Include normal unflagged rows as well as anomalies")
    
    args = parser.parse_args()

    config = AppConfig(
        shipment_records_path=Path(args.shipments),
        context_notes_path=Path(args.notes),
        output_path=Path(args.output),
        token_cost_log_path=Path(args.log)
    )

    print("==================================================================")
    print("FREIGHT TIGER - Smart Assistant Watching Shipping Costs")
    print("==================================================================")
    print(f"Loading shipments: {config.shipment_records_path}")
    print(f"Loading context notes: {config.context_notes_path}")
    print(f"Running anomaly detection & RAG guardrails...")

    df_output, tracker = run_pipeline(config=config, anomalies_only=not args.all_rows)

    print(f"\nCompleted! Generated {len(df_output)} output rows.")
    print(f"Saved CSV output to: {config.output_path}")
    print(f"Saved token/cost log to: {config.token_cost_log_path}")
    print("\nSummary of Output:")
    print(f"  Flagged (Yes / Unexplained): {(df_output['flagged'] == 'Yes').sum()}")
    print(f"  Flagged (No / Justified)  : {(df_output['flagged'] == 'No (justified)').sum()}")
    if args.all_rows:
        print(f"  Unflagged (Normal)        : {(df_output['flagged'] == 'No').sum()}")

    print("\nSample Output Rows:")
    print(df_output.head(10).to_string(index=False))

    print("\nToken & Cost Metrics:")
    log_dict = tracker.to_dict()
    for k, v in log_dict.items():
        print(f"  {k}: {v}")

if __name__ == "__main__":
    main()
