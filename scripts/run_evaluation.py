"""
CLI entry point to execute the evaluation harness.
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from evaluation.evaluate import run_evaluation

def main():
    print("==================================================================")
    print("FREIGHT TIGER - Evaluation Harness & Ground Truth Verification")
    print("==================================================================")
    results = run_evaluation()

    print(f"\nTotal Ground Truth Scenarios Evaluated: {results['total_test_cases']}")
    print(f"  Flag Decision Accuracy         : {results['flag_accuracy_pct']:.1f}%")
    print(f"  Note Attribution Accuracy      : {results['note_attribution_accuracy_pct']:.1f}%")
    print(f"  Numeric Cost Accuracy          : {results['numeric_cost_accuracy_pct']:.1f}%")
    print(f"  Hallucination Rate             : {results['hallucination_rate_pct']:.1f}%")

    print("\nCase-by-case Breakdown:")
    for c in results["case_details"]:
        print(f"  [{c['status']}] {c['route']} ({c['week_of']}): {c['scenario']}")
        print(f"         Expected: flag='{c['expected_flag']}', note='{c['expected_note']}', cost={c['expected_cost']}")
        print(f"         Actual  : flag='{c['actual_flag']}', note='{c['actual_note']}', cost={c['actual_cost']}")

    if results['flag_accuracy_pct'] == 100.0 and results['note_attribution_accuracy_pct'] == 100.0 and results['hallucination_rate_pct'] == 0.0:
        print("\nAll evaluation guardrails PASSED with 0% hallucinations!")
    else:
        print("\nSome evaluation checks failed.")

if __name__ == "__main__":
    main()
