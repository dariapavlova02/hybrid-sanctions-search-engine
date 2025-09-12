#!/usr/bin/env python3
"""
CLI: Offline threshold calibration.

Input CSV columns required:
 - score (float)
 - label (int: 1/0)
Optional:
 - has_strong_meta (bool/int)

Usage:
  python -m ai_service.eval.cli_calibrate --input scores.csv --recall 0.98 --objective min_review
"""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

from .threshold_calibration import Sample, grid_search_thresholds


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--input", required=True, help="Path to CSV with score,label[,has_strong_meta]"
    )
    ap.add_argument("--recall", type=float, default=0.98)
    ap.add_argument(
        "--objective", choices=["min_review", "max_precision"], default="min_review"
    )
    ap.add_argument("--step", type=float, default=0.01)
    args = ap.parse_args()

    p = Path(args.input)
    if not p.exists():
        raise SystemExit(f"Input not found: {p}")

    samples = []
    with p.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                score = float(row["score"])
                label = int(row["label"])
                strong = False
                if "has_strong_meta" in row and row["has_strong_meta"] != "":
                    v = row["has_strong_meta"]
                    strong = (
                        bool(int(v))
                        if v in ("0", "1")
                        else (str(v).lower() in ("true", "yes", "y", "t", "1"))
                    )
                samples.append(Sample(score=score, label=label, has_strong_meta=strong))
            except Exception:
                continue

    res = grid_search_thresholds(
        samples, recall_target=args.recall, objective=args.objective, step=args.step
    )
    print("Calibration result:")
    print(f" clear={res.clear:.2f} review={res.review:.2f} auto_hit={res.auto_hit:.2f}")
    print(
        f" recall@review={res.recall_at_review:.4f} auto_hit_precision={res.auto_hit_precision:.4f} review_rate={res.review_rate:.4f}"
    )


if __name__ == "__main__":
    main()
