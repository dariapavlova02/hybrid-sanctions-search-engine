"""CLI tool for running normalization parity checks."""

from __future__ import annotations

import argparse
import concurrent.futures
import csv
import json
import sys
from html import escape
from pathlib import Path
from typing import Any, Dict, Iterable, List, Sequence

# Add src and tests to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))
sys.path.insert(0, str(project_root))

from ai_service.contracts.base_contracts import NormalizationResult
from tests.parity.parity_runner import (
    NormalizationFlags,
    compare_results,
    measure_latency,
    run_factory,
    run_legacy,
)


def _parse_args(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run legacy vs factory normalization parity checks")
    parser.add_argument(
        "--input",
        required=True,
        help="Path to NDJSON/JSONL file or directory containing such files",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=8,
        help="Number of cases to submit to the worker pool at once",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=4,
        help="Thread pool size for processing cases",
    )
    parser.add_argument(
        "--output-dir",
        default="artifacts/parity",
        help="Where to place CSV/HTML/JSON artifacts",
    )
    return parser.parse_args(argv)


def _iter_input_files(root: Path) -> Iterable[Path]:
    if root.is_file():
        yield root
        return

    for candidate in sorted(root.rglob("*")):
        if candidate.suffix.lower() in {".jsonl", ".ndjson"}:
            yield candidate


def _load_records(path: Path) -> List[Dict[str, Any]]:
    records: List[Dict[str, Any]] = []
    for file_path in _iter_input_files(path):
        with file_path.open("r", encoding="utf-8") as handle:
            for line_number, line in enumerate(handle, start=1):
                line = line.strip()
                if not line:
                    continue
                try:
                    payload = json.loads(line)
                except json.JSONDecodeError as exc:
                    record_id = f"{file_path.name}:{line_number}"
                    records.append(
                        {
                            "id": record_id,
                            "text": "",
                            "lang": "auto",
                            "error": f"JSON decode error: {exc}",
                        }
                    )
                    continue

                text = payload.get("text")
                if not isinstance(text, str):
                    record_id = payload.get("id") or f"{file_path.name}:{line_number}"
                    records.append(
                        {
                            "id": str(record_id),
                            "text": "",
                            "lang": "auto",
                            "error": "Missing 'text' field",
                        }
                    )
                    continue

                record_id = payload.get("id") or f"{file_path.name}:{line_number}"
                records.append(
                    {
                        "id": str(record_id),
                        "text": text,
                        "lang": payload.get("lang", "auto"),
                        "error": None,
                    }
                )
    return records


def _chunked(items: Sequence[Dict[str, Any]], chunk_size: int) -> Iterable[List[Dict[str, Any]]]:
    chunk: List[Dict[str, Any]] = []
    for item in items:
        chunk.append(item)
        if len(chunk) >= chunk_size:
            yield chunk
            chunk = []
    if chunk:
        yield chunk


def _safe_model_dump(result: NormalizationResult) -> Dict[str, Any]:
    if hasattr(result, "model_dump"):
        return result.model_dump()
    if hasattr(result, "dict"):
        return result.dict()  # type: ignore[return-value]
    raise TypeError("Unsupported normalization result type")


def _process_case(record: Dict[str, Any], flags: NormalizationFlags) -> Dict[str, Any]:
    if record.get("error"):
        return {
            "id": record["id"],
            "lang": record.get("lang", "auto"),
            "error": record["error"],
            "legacy": None,
            "factory": None,
            "legacy_timing": None,
            "factory_timing": None,
            "comparison": None,
        }

    text = record["text"]
    try:
        legacy_result, legacy_timing = run_legacy(text, flags)
        factory_result, factory_timing = run_factory(text, flags)
        comparison = compare_results(legacy_result, factory_result)
        return {
            "id": record["id"],
            "lang": record.get("lang", "auto"),
            "error": None,
            "legacy": _safe_model_dump(legacy_result),
            "factory": _safe_model_dump(factory_result),
            "legacy_timing": legacy_timing,
            "factory_timing": factory_timing,
            "comparison": comparison,
        }
    except Exception as exc:  # pragma: no cover - defensive fallback
        return {
            "id": record["id"],
            "lang": record.get("lang", "auto"),
            "error": str(exc),
            "legacy": None,
            "factory": None,
            "legacy_timing": None,
            "factory_timing": None,
            "comparison": None,
        }


def _score_divergence(case_result: Dict[str, Any]) -> float:
    comparison = case_result.get("comparison")
    if not comparison:
        return -1.0
    score = 0.0
    if not comparison.get("equal_text", False):
        score += 1.0
    if not comparison.get("equal_roles", False):
        score += 1.0
    score += float(len(comparison.get("diff_tokens", [])))
    return score


def _write_csv(results: Sequence[Dict[str, Any]], destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["id", "equal_text", "equal_roles", "diff_tokens_cnt", "notes"],
        )
        writer.writeheader()
        for item in results:
            comparison = item.get("comparison") or {}
            notes: List[str] = []
            if item.get("error"):
                notes.append(f"error={item['error']}")
            else:
                if not comparison.get("equal_text", False):
                    notes.append("normalized_mismatch")
                if not comparison.get("equal_roles", False):
                    notes.append("roles_mismatch")
                diff_count = len(comparison.get("diff_tokens", []))
                if diff_count:
                    notes.append(f"diff_tokens={diff_count}")
            writer.writerow(
                {
                    "id": item.get("id"),
                    "equal_text": comparison.get("equal_text"),
                    "equal_roles": comparison.get("equal_roles"),
                    "diff_tokens_cnt": len(comparison.get("diff_tokens", [])),
                    "notes": ";".join(notes),
                }
            )


def _render_case_block(item: Dict[str, Any]) -> str:
    case_id = escape(str(item.get("id")))
    status = "OK"
    comparison = item.get("comparison")
    if item.get("error"):
        status = "ERROR"
    elif not comparison or not comparison.get("equal_text", False):
        status = "DIFF"

    legacy_json = json.dumps(item.get("legacy", {}), ensure_ascii=False, indent=2)
    factory_json = json.dumps(item.get("factory", {}), ensure_ascii=False, indent=2)
    comparison_json = json.dumps(comparison or {}, ensure_ascii=False, indent=2)

    return (
        f"<details><summary><strong>{case_id}</strong> — {status}</summary>"
        f"<pre class='payload legacy'>LEGACY\n{escape(legacy_json)}</pre>"
        f"<pre class='payload factory'>FACTORY\n{escape(factory_json)}</pre>"
        f"<pre class='payload comparison'>COMPARISON\n{escape(comparison_json)}</pre>"
        "</details>"
    )


def _write_html(
    results: Sequence[Dict[str, Any]],
    destination: Path,
    metrics: Dict[str, Any],
) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)

    parity_percent = metrics.get("parity_percent", 0.0)
    total_cases = metrics.get("total_cases", 0)
    legacy_latency = metrics.get("latency", {}).get("legacy", {})
    factory_latency = metrics.get("latency", {}).get("factory", {})
    divergences = metrics.get("divergences", [])

    case_blocks = "\n".join(_render_case_block(item) for item in results)
    divergence_rows = "".join(
        f"<tr><td>{escape(str(entry['id']))}</td><td>{entry['score']:.2f}</td>"
        f"<td>{len(entry.get('diff_tokens', []))}</td></tr>"
        for entry in divergences
    )

    html = f"""
    <html>
    <head>
        <meta charset='utf-8'>
        <title>Normalization Parity Report</title>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 2rem; }}
            table {{ border-collapse: collapse; margin-bottom: 2rem; }}
            th, td {{ border: 1px solid #ccc; padding: 0.5rem 1rem; }}
            details {{ margin-bottom: 1rem; }}
            pre.payload {{ background: #f8f8f8; padding: 1rem; overflow-x: auto; }}
            summary {{ cursor: pointer; }}
        </style>
    </head>
    <body>
        <h1>Normalization Parity Report</h1>
        <section>
            <h2>Summary</h2>
            <p>Total cases: {total_cases}<br>
               Parity (equal text): {parity_percent:.2f}%</p>
            <table>
                <tr><th></th><th>p50 (ms)</th><th>p95 (ms)</th><th>p99 (ms)</th></tr>
                <tr><th>Legacy</th><td>{legacy_latency.get('p50_ms', 0.0):.2f}</td><td>{legacy_latency.get('p95_ms', 0.0):.2f}</td><td>{legacy_latency.get('p99_ms', 0.0):.2f}</td></tr>
                <tr><th>Factory</th><td>{factory_latency.get('p50_ms', 0.0):.2f}</td><td>{factory_latency.get('p95_ms', 0.0):.2f}</td><td>{factory_latency.get('p99_ms', 0.0):.2f}</td></tr>
            </table>
            <h3>Top divergences</h3>
            <table>
                <tr><th>ID</th><th>Score</th><th>Diff tokens</th></tr>
                {divergence_rows}
            </table>
        </section>
        <section>
            <h2>Cases</h2>
            {case_blocks}
        </section>
    </body>
    </html>
    """

    destination.write_text(html, encoding="utf-8")


def _write_metrics(payload: Dict[str, Any], destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv or sys.argv[1:])
    input_path = Path(args.input)
    output_dir = Path(args.output_dir)
    records = _load_records(input_path)

    if not records:
        print("No records found", file=sys.stderr)
        return 1

    flags = NormalizationFlags()
    processed: List[Dict[str, Any]] = []

    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as executor:
        for batch in _chunked(records, max(args.batch_size, 1)):
            futures = [executor.submit(_process_case, record, flags) for record in batch]
            for future in concurrent.futures.as_completed(futures):
                processed.append(future.result())

    total_cases = len(processed)
    comparisons = [item["comparison"] for item in processed if item.get("comparison")]
    parity_hits = sum(1 for comp in comparisons if comp.get("equal_text"))
    parity_percent = (parity_hits / total_cases) * 100 if total_cases else 0.0

    legacy_times = [item["legacy_timing"]["elapsed_ms"] for item in processed if item.get("legacy_timing")]
    factory_times = [item["factory_timing"]["elapsed_ms"] for item in processed if item.get("factory_timing")]

    legacy_latency = measure_latency(lambda: legacy_times)
    factory_latency = measure_latency(lambda: factory_times)

    divergences_ranked = sorted(
        (
            {
                "id": entry["id"],
                "score": _score_divergence(entry),
                "diff_tokens": entry.get("comparison", {}).get("diff_tokens", []),
                "trace_deltas": entry.get("comparison", {}).get("trace_deltas", []),
            }
            for entry in processed
            if entry.get("comparison")
        ),
        key=lambda item: item["score"],
        reverse=True,
    )
    top_divergences = [item for item in divergences_ranked if item["score"] > 0][:5]

    metrics = {
        "flags": flags.to_dict(),
        "total_cases": total_cases,
        "parity_percent": parity_percent,
        "parity_ratio": parity_percent / 100 if total_cases else 0.0,
        "latency": {
            "legacy": legacy_latency,
            "factory": factory_latency,
            "delta_p95_ms": factory_latency.get("p95_ms", 0.0) - legacy_latency.get("p95_ms", 0.0),
        },
        "divergences": top_divergences,
    }

    _write_csv(processed, output_dir / "parity_diff.csv")
    _write_html(processed, output_dir / "report.html", metrics)
    _write_metrics(metrics, output_dir / "metrics.json")

    print(
        f"Processed {total_cases} cases — parity {parity_percent:.2f}% | "
        f"legacy p95 {legacy_latency.get('p95_ms', 0.0):.2f} ms | "
        f"factory p95 {factory_latency.get('p95_ms', 0.0):.2f} ms",
        file=sys.stderr,
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
