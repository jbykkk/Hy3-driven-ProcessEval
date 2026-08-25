"""Summarize the interrupted high/16000 retry without exposing full reasoning."""

from __future__ import annotations

import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parents[1]
SELECTION_PATH = ROOT / "experiments/baseline_50/high_16000_selection.jsonl"
MANIFEST_PATH = ROOT / "experiments/baseline_50/high_16000_manifest.json"
BASELINE_OUTPUT_PATH = ROOT / "outputs/baseline_50_solver_outputs.jsonl"
OUTPUT_PATH = ROOT / "outputs/baseline_50_high16000_rerun_solver_outputs.jsonl"
VERIFICATION_PATH = (
    ROOT / "outputs/baseline_50_high16000_rerun_answer_verification.jsonl"
)
ANALYSIS_PATH = ROOT / "experiments/baseline_50/high_16000_partial_analysis.json"
ISSUES_PATH = ROOT / "experiments/baseline_50/high_16000_partial_issues.jsonl"


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def grouped_counts(
    records: Iterable[dict[str, Any]], key: str
) -> dict[str, dict[str, int]]:
    groups: dict[str, Counter[str]] = defaultdict(Counter)
    for record in records:
        group = str(record[key])
        groups[group][record["finish_reason"]] += 1
        groups[group]["completed"] += 1
    return {group: dict(counts) for group, counts in sorted(groups.items())}


def main() -> None:
    selection = read_jsonl(SELECTION_PATH)
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    results = read_jsonl(OUTPUT_PATH)
    verifications = {
        record["inference_id"]: record for record in read_jsonl(VERIFICATION_PATH)
    }
    baseline_by_id = {
        record["sample"]["id"]: record for record in read_jsonl(BASELINE_OUTPUT_PATH)
    }
    selection_by_id = {record["id"]: record for record in selection}

    if len(selection) != 23:
        raise ValueError(f"Expected 23 planned retries, found {len(selection)}")
    if len(results) != 16:
        raise ValueError(f"Expected 16 completed retries, found {len(results)}")

    rows: list[dict[str, Any]] = []
    issues: list[dict[str, Any]] = []
    verdicts = Counter[str]()
    stop_verdicts = Counter[str]()

    for result in results:
        sample_id = result["sample"]["id"]
        sample = selection_by_id[sample_id]
        response = result["response"]
        usage = response.get("usage") or {}
        details = usage.get("completion_tokens_details") or {}
        finish_reason = response.get("finish_reason") or "missing"
        verification = verifications[result["inference_id"]]
        verdict = verification["verification"]["verdict"]
        verdicts[verdict] += 1
        if finish_reason == "stop":
            stop_verdicts[verdict] += 1

        row = {
            "sample_id": sample_id,
            "dataset": sample["dataset"],
            "difficulty": sample.get("metadata", {}).get("difficulty"),
            "has_asymptote": "[asy]" in sample["problem"],
            "finish_reason": finish_reason,
            "total_tokens": usage.get("total_tokens", 0),
            "completion_tokens": usage.get("completion_tokens", 0),
            "reasoning_tokens": details.get("reasoning_tokens", 0),
            "latency_ms": result.get("timing", {}).get("latency_ms", 0),
            "content_length": len(response.get("content") or ""),
            "parser_warnings": result.get("parsed", {}).get("warnings", []),
            "verification_verdict": verdict,
        }
        rows.append(row)

        if finish_reason != "stop" or row["parser_warnings"]:
            issue_type = (
                "generation_truncated"
                if finish_reason == "length"
                else "parser_warning"
            )
            issues.append(
                {
                    "schema_version": "1.0",
                    "experiment": "baseline_50_high_16000_partial",
                    "issue_type": issue_type,
                    "sample": sample,
                    "parent_inference_id": manifest["parent_inference_ids"][sample_id],
                    "inference_id": result["inference_id"],
                    "response_shape": {
                        "finish_reason": finish_reason,
                        "content_length": row["content_length"],
                        "usage": usage,
                        "latency_ms": row["latency_ms"],
                        "parser_warnings": row["parser_warnings"],
                        "parsed_final_answer": result.get("parsed", {}).get(
                            "final_answer"
                        ),
                        "verification_verdict": verdict,
                    },
                    "analysis": (
                        "The response is incomplete and must not be scored as a model "
                        "answer, even if the parser extracted a token."
                        if finish_reason == "length"
                        else "The visible response states that profit begins in year 13, "
                        "but parser v1.3 does not recognize the Conclusion label."
                    ),
                }
            )

    finish_reasons = Counter(row["finish_reason"] for row in rows)
    asy_rows = [row for row in rows if row["has_asymptote"]]
    non_asy_rows = [row for row in rows if not row["has_asymptote"]]
    baseline_rows = [baseline_by_id[row["sample_id"]] for row in rows]

    analysis = {
        "schema_version": "1.0",
        "experiment": "baseline_50_high_16000_partial",
        "status": "stopped_by_user_after_16_of_23",
        "scope_decision_after_stop": {
            "primary_evaluation_dataset": "math",
            "primary_sample_count": 250,
            "math_sampling": "50 samples from each official Level 1-5",
            "supplementary_datasets": ["gsm8k", "aime"],
            "planned_high_24000_retry": "cancelled_not_started",
        },
        "configuration": {
            **manifest["unchanged"],
            "max_tokens": 16000,
            "max_retries": 0,
        },
        "planned": len(selection),
        "completed": len(rows),
        "not_started_or_interrupted_without_record": len(selection) - len(rows),
        "finish_reasons": dict(finish_reasons),
        "recovered_from_high_4096_length": finish_reasons.get("stop", 0),
        "still_truncated": finish_reasons.get("length", 0),
        "recovery_rate_among_completed": finish_reasons.get("stop", 0) / len(rows),
        "verification_all_completed": dict(verdicts),
        "verification_stop_only": dict(stop_verdicts),
        "note_on_scoring": (
            "Only finish_reason=stop responses are eligible for answer scoring. "
            "One stop response is parser-unverified but visibly states the correct answer; "
            "all 11 other stop responses verify correct."
        ),
        "tokens": {
            "total": sum(row["total_tokens"] for row in rows),
            "completion": sum(row["completion_tokens"] for row in rows),
            "reasoning": sum(row["reasoning_tokens"] for row in rows),
            "baseline_4096_total_for_same_samples": sum(
                record["response"]["usage"]["total_tokens"] for record in baseline_rows
            ),
        },
        "latency_ms": {
            "sum": sum(row["latency_ms"] for row in rows),
            "mean": sum(row["latency_ms"] for row in rows) / len(rows),
        },
        "by_dataset": grouped_counts(rows, "dataset"),
        "math_by_difficulty": grouped_counts(
            [row for row in rows if row["dataset"] == "math"], "difficulty"
        ),
        "asymptote": {
            "completed": len(asy_rows),
            "stop": sum(row["finish_reason"] == "stop" for row in asy_rows),
            "length": sum(row["finish_reason"] == "length" for row in asy_rows),
        },
        "non_asymptote": {
            "completed": len(non_asy_rows),
            "stop": sum(row["finish_reason"] == "stop" for row in non_asy_rows),
            "length": sum(row["finish_reason"] == "length" for row in non_asy_rows),
        },
        "still_truncated_ids": [
            row["sample_id"] for row in rows if row["finish_reason"] == "length"
        ],
        "completed_sample_ids": [row["sample_id"] for row in rows],
        "source_files": {
            "selection": str(SELECTION_PATH.relative_to(ROOT)),
            "selection_sha256": sha256(SELECTION_PATH),
            "local_solver_output": str(OUTPUT_PATH.relative_to(ROOT)),
            "local_solver_output_sha256": sha256(OUTPUT_PATH),
            "local_verification": str(VERIFICATION_PATH.relative_to(ROOT)),
            "local_verification_sha256": sha256(VERIFICATION_PATH),
        },
    }

    ANALYSIS_PATH.write_text(
        json.dumps(analysis, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    with ISSUES_PATH.open("w", encoding="utf-8") as handle:
        for issue in issues:
            handle.write(json.dumps(issue, ensure_ascii=False) + "\n")

    print(json.dumps(analysis, ensure_ascii=False, indent=2))
    print(f"issues={len(issues)}")


if __name__ == "__main__":
    main()
