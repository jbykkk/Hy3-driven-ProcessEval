"""Generate reproducible aggregate metrics and a reviewed baseline issue inventory."""

from __future__ import annotations

import json
import math
import statistics
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
EXPERIMENT_DIR = ROOT / "experiments" / "baseline_50"
SELECTION = EXPERIMENT_DIR / "selection.jsonl"
SOLVER_OUTPUT = ROOT / "outputs" / "baseline_50_solver_outputs.jsonl"
VERIFICATION_OUTPUT = ROOT / "outputs" / "baseline_50_answer_verification.jsonl"
SUMMARY = EXPERIMENT_DIR / "analysis.json"
ISSUES = EXPERIMENT_DIR / "issues.jsonl"


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def percentile(values: list[float], probability: float) -> float:
    ordered = sorted(values)
    position = (len(ordered) - 1) * probability
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[lower]
    return ordered[lower] + (ordered[upper] - ordered[lower]) * (position - lower)


def metric(records: list[dict[str, Any]], key: str) -> dict[str, float]:
    if key == "latency_ms":
        values = [float(record["timing"][key]) for record in records]
    else:
        values = [float((record["response"]["usage"] or {}).get(key) or 0) for record in records]
    return {
        "sum": round(sum(values), 3),
        "mean": round(statistics.mean(values), 3),
        "median": round(statistics.median(values), 3),
        "p95": round(percentile(values, 0.95), 3),
        "max": round(max(values), 3),
    }


def summarize_group(
    records: list[dict[str, Any]], verification_by_inference: dict[str, dict[str, Any]]
) -> dict[str, Any]:
    finish_reasons = Counter(record["response"]["finish_reason"] for record in records)
    verdicts = Counter(
        verification_by_inference[record["inference_id"]]["verification"]["verdict"]
        for record in records
    )
    return {
        "samples": len(records),
        "finish_reasons": dict(finish_reasons),
        "verdicts": dict(verdicts),
        "completion_tokens": metric(records, "completion_tokens"),
        "total_tokens": metric(records, "total_tokens"),
        "latency_ms": metric(records, "latency_ms"),
    }


def main() -> None:
    selection = load_jsonl(SELECTION)
    solver_records = load_jsonl(SOLVER_OUTPUT)
    verification_records = load_jsonl(VERIFICATION_OUTPUT)
    benchmark_by_id = {record["id"]: record for record in selection}
    verification_by_inference = {
        record["inference_id"]: record for record in verification_records
    }
    if len(solver_records) != 50 or len(verification_records) != 50:
        raise ValueError("Expected exactly 50 solver and verification records")

    stop_records = [
        record for record in solver_records if record["response"]["finish_reason"] == "stop"
    ]
    length_records = [
        record for record in solver_records if record["response"]["finish_reason"] == "length"
    ]
    reasoning_tokens = [
        int(
            record["response"]["usage"]["completion_tokens_details"].get(
                "reasoning_tokens"
            )
            or 0
        )
        for record in solver_records
    ]
    completion_tokens = sum(
        int(record["response"]["usage"].get("completion_tokens") or 0)
        for record in solver_records
    )
    asymptote_ids = {
        record["id"] for record in selection if "[asy]" in record["problem"]
    }
    truncated_ids = {
        record["sample"]["id"] for record in length_records
    }

    by_dataset = {}
    for dataset in ("gsm8k", "math", "aime"):
        records = [
            record for record in solver_records if record["sample"]["dataset"] == dataset
        ]
        by_dataset[dataset] = summarize_group(records, verification_by_inference)

    math_levels = {}
    for level in (f"Level {number}" for number in range(1, 6)):
        records = [
            record
            for record in solver_records
            if record["sample"]["dataset"] == "math"
            and benchmark_by_id[record["sample"]["id"]]["metadata"]["difficulty"] == level
        ]
        math_levels[level] = summarize_group(records, verification_by_inference)

    verdicts = Counter(
        record["verification"]["verdict"] for record in verification_records
    )
    parser_regressions = []
    issues = []
    for inference in solver_records:
        sample_id = inference["sample"]["id"]
        verification = verification_by_inference[inference["inference_id"]]
        current_prediction = verification["prediction"]["value"]
        stored_prediction = (inference.get("parsed") or {}).get("final_answer")
        stored_warnings = (inference.get("parsed") or {}).get("warnings") or []
        issue_types = []
        analyses = []
        if inference["response"]["finish_reason"] == "length":
            issue_types.append("generation_truncated")
            analyses.append(
                "The request reached max_tokens=4096 before a final answer; preserve as unverified."
            )
        if (
            inference["response"]["finish_reason"] == "stop"
            and (stored_prediction != current_prediction or stored_warnings)
        ):
            issue_types.append("parser_v1_2_extraction")
            analyses.append(
                "The stored v1.2 parse missed or mis-selected the answer; v1.3 reparsing recovered it."
            )
            parser_regressions.append(sample_id)
        if inference["attempt_errors"]:
            issue_types.append("api_attempt_error")
            analyses.append("At least one provider attempt failed before the recorded result.")
        if not issue_types:
            continue

        content = inference["response"]["content"]
        reasoning_content = inference["response"].get("reasoning_content") or ""
        issues.append(
            {
                "schema_version": "1.0",
                "sample_id": sample_id,
                "issue_types": issue_types,
                "benchmark_record": benchmark_by_id[sample_id],
                "inference": {
                    "inference_id": inference["inference_id"],
                    "request": inference["request"],
                    "timing": inference["timing"],
                    "attempt_count": inference["attempt_count"],
                    "attempt_errors": inference["attempt_errors"],
                },
                "response_shape": {
                    "finish_reason": inference["response"]["finish_reason"],
                    "visible_content": content,
                    "visible_content_chars": len(content),
                    "reasoning_content_chars": len(reasoning_content),
                    "usage": inference["response"]["usage"],
                },
                "stored_parse": inference["parsed"],
                "current_prediction": verification["prediction"],
                "current_verification": verification["verification"],
                "analysis": analyses,
                "reasoning_content_omitted": True,
            }
        )

    summary = {
        "schema_version": "1.0",
        "experiment": "baseline_50",
        "request_config": solver_records[0]["request"],
        "records": len(solver_records),
        "unique_samples": len({record["sample"]["id"] for record in solver_records}),
        "api": {
            "status_counts": dict(Counter(record["status"] for record in solver_records)),
            "attempt_count": dict(Counter(str(record["attempt_count"]) for record in solver_records)),
            "attempt_errors": sum(len(record["attempt_errors"]) for record in solver_records),
        },
        "outcomes": {
            "finish_reasons": dict(
                Counter(record["response"]["finish_reason"] for record in solver_records)
            ),
            "empty_visible_content": sum(
                not record["response"]["content"] for record in solver_records
            ),
            "verdicts": dict(verdicts),
            "format_mismatch_but_equivalent": sum(
                record["verification"]["format_mismatch_but_equivalent"]
                for record in verification_records
            ),
            "manual_review_recommended": sum(
                record["verification"]["manual_review_recommended"]
                for record in verification_records
            ),
            "answer_yield": round(len(stop_records) / len(solver_records), 6),
        },
        "input_formats": {
            "asymptote_markup_samples": len(asymptote_ids),
            "asymptote_markup_truncated": len(asymptote_ids & truncated_ids),
            "non_asymptote_samples": len(solver_records) - len(asymptote_ids),
            "non_asymptote_truncated": len(truncated_ids - asymptote_ids),
        },
        "usage": {
            "overall": {
                "prompt_tokens": metric(solver_records, "prompt_tokens"),
                "completion_tokens": metric(solver_records, "completion_tokens"),
                "total_tokens": metric(solver_records, "total_tokens"),
                "latency_ms": metric(solver_records, "latency_ms"),
                "reasoning_tokens_sum": sum(reasoning_tokens),
                "reasoning_share_of_completion": round(
                    sum(reasoning_tokens) / completion_tokens, 6
                ),
                "truncated_total_token_share": round(
                    sum(
                        int(record["response"]["usage"].get("total_tokens") or 0)
                        for record in length_records
                    )
                    / sum(
                        int(record["response"]["usage"].get("total_tokens") or 0)
                        for record in solver_records
                    ),
                    6,
                ),
            },
            "stop": summarize_group(stop_records, verification_by_inference),
            "length": summarize_group(length_records, verification_by_inference),
        },
        "by_dataset": by_dataset,
        "math_levels": math_levels,
        "issue_counts": {
            "generation_truncated": len(length_records),
            "parser_v1_2_extraction": len(parser_regressions),
            "issue_records": len(issues),
        },
        "parser_v1_2_affected_sample_ids": parser_regressions,
    }

    SUMMARY.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    with ISSUES.open("w", encoding="utf-8") as handle:
        for issue in issues:
            handle.write(json.dumps(issue, ensure_ascii=False, separators=(",", ":")) + "\n")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
