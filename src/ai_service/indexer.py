#!/usr/bin/env python3
"""
Watchlist index builder CLI.

Input: JSONL or CSV with fields: core_id, canonical_text, entity_type, metadata(json)
Output: snapshot directory containing vectorizer/svd/docs/faiss index (if available)
"""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Dict, List, Tuple

from ai_service.services.vector_index_service import VectorIndexConfig
from ai_service.services.watchlist_index_service import WatchlistIndexService
from ai_service.utils import get_logger, setup_logging


def read_jsonl(path: Path) -> List[Tuple[str, str, str, Dict]]:
    items = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            obj = json.loads(line)
            cid = str(obj.get("core_id") or obj.get("id"))
            text = str(obj.get("canonical_text") or obj.get("text") or "")
            et = str(obj.get("entity_type") or "unknown")
            md = obj.get("metadata") or {}
            items.append((cid, text, et, md))
    return items


def read_csv(path: Path) -> List[Tuple[str, str, str, Dict]]:
    items = []
    with path.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            cid = str(row.get("core_id") or row.get("id"))
            text = str(row.get("canonical_text") or row.get("text") or "")
            et = str(row.get("entity_type") or "unknown")
            md = row.get("metadata")
            try:
                md = json.loads(md) if isinstance(md, str) else (md or {})
            except Exception:
                md = {}
            items.append((cid, text, et, md))
    return items


def main():
    setup_logging()
    logger = get_logger(__name__)
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--input", required=True, help="Path to JSONL or CSV watchlist corpus"
    )
    ap.add_argument("--out", required=True, help="Output snapshot directory")
    ap.add_argument("--svd-dim", type=int, default=128)
    args = ap.parse_args()

    inp = Path(args.input)
    if not inp.exists():
        raise SystemExit(f"Input not found: {inp}")
    if inp.suffix.lower() == ".jsonl":
        corpus = read_jsonl(inp)
    else:
        corpus = read_csv(inp)
    logger.info(f"Loaded corpus: {len(corpus)} records")

    svc = WatchlistIndexService(VectorIndexConfig(svd_dim=args.svd_dim))
    svc.build_from_corpus(corpus, index_id=str(inp))
    info = svc.save_snapshot(args.out)
    logger.info(f"Snapshot saved: {info}")


if __name__ == "__main__":
    main()
