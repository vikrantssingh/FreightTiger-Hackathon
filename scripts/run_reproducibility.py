"""
Script to execute 3 untouched runs and verify bit-for-bit reproducibility.
Generates run_1.csv, run_2.csv, run_3.csv, and reproducibility.diff.
"""

import sys
import hashlib
import difflib
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.freight_assistant.config import DEFAULT_CONFIG, AppConfig
from src.freight_assistant.pipeline import run_pipeline

def main():
    print("==================================================================")
    print("FREIGHT TIGER - 3-Run Reproducibility Verification")
    print("==================================================================")

    runs = []
    hashes = []
    outputs_dir = PROJECT_ROOT / "outputs"
    outputs_dir.mkdir(parents=True, exist_ok=True)

    for i in range(1, 4):
        run_file = outputs_dir / f"run_{i}.csv"
        cfg = AppConfig(output_path=run_file)
        print(f"Executing Run {i}...")
        df_out, _ = run_pipeline(config=cfg, anomalies_only=True)
        
        with open(run_file, "rb") as f:
            content = f.read()
            h = hashlib.sha256(content).hexdigest()
            hashes.append(h)
            runs.append(content.decode("utf-8"))
        print(f"  Run {i} complete: SHA256={h[:16]}... ({len(df_out)} rows)")

    # Compare hashes
    all_matched = (hashes[0] == hashes[1] == hashes[2])

    # Compute diff between Run 1 and Run 2, and Run 2 and Run 3
    diff_1_2 = list(difflib.unified_diff(
        runs[0].splitlines(keepends=True),
        runs[1].splitlines(keepends=True),
        fromfile="run_1.csv",
        tofile="run_2.csv"
    ))

    diff_2_3 = list(difflib.unified_diff(
        runs[1].splitlines(keepends=True),
        runs[2].splitlines(keepends=True),
        fromfile="run_2.csv",
        tofile="run_3.csv"
    ))

    diff_path = outputs_dir / "reproducibility.diff"
    with open(diff_path, "w", encoding="utf-8") as f:
        if all_matched:
            f.write("# 3-Run Reproducibility Diff Report\n")
            f.write(f"# All 3 runs matched byte-for-byte identically!\n")
            f.write(f"# Run 1 SHA256: {hashes[0]}\n")
            f.write(f"# Run 2 SHA256: {hashes[1]}\n")
            f.write(f"# Run 3 SHA256: {hashes[2]}\n")
            f.write("# Zero diff detected between runs.\n")
        else:
            f.writelines(diff_1_2)
            f.writelines(diff_2_3)

    print("\n------------------------------------------------------------------")
    print("REPRODUCIBILITY VERIFICATION REPORT:")
    print(f"  Run 1 SHA256: {hashes[0]}")
    print(f"  Run 2 SHA256: {hashes[1]}")
    print(f"  Run 3 SHA256: {hashes[2]}")
    print(f"  Exact Bit-for-Bit Match: {all_matched}")
    print(f"  Diff report written to: {diff_path}")
    print("------------------------------------------------------------------")

if __name__ == "__main__":
    main()
