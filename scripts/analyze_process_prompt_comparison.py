"""Aggregate the 25-sample solver/process prompt comparison without copying reasoning text."""

from __future__ import annotations

import hashlib
import json
import statistics
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable

ROOT = Path(__file__).resolve().parents[1]
EXPERIMENT_DIR = ROOT / "experiments" / "process_evaluator_v1v2_25"
SELECTION = EXPERIMENT_DIR / "selection.jsonl"
OUTPUT = EXPERIMENT_DIR / "analysis.json"
VERSIONS = ("v1", "v2")


def output_path(version: str, kind: str) -> Path:
    return ROOT / "outputs" / f"process_v1v2_25_{version}_{kind}.jsonl"


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            try:
                value = json.loads(line)
            except json.JSONDecodeError as error:
                raise ValueError(f"Invalid JSONL at {path}:{line_number}") from error
            if not isinstance(value, dict):
                raise ValueError(f"Expected object at {path}:{line_number}")
            records.append(value)
    return records


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def nonempty_line_count(path: Path) -> int:
    with path.open("r", encoding="utf-8") as handle:
        return sum(bool(line.strip()) for line in handle)


def number(value: Any) -> int:
    return int(value) if isinstance(value, (int, float)) else 0


def mean(values: Iterable[int | float]) -> float:
    items = list(values)
    return round(statistics.mean(items), 3) if items else 0.0


def median(values: Iterable[int | float]) -> float:
    items = list(values)
    return round(statistics.median(items), 3) if items else 0.0


def percent_change(old: int | float, new: int | float) -> float | None:
    if old == 0:
        return None
    return round((new - old) / old * 100, 3)


def usage_metrics(usage: dict[str, Any] | None) -> dict[str, int]:
    usage = usage or {}
    completion = number(usage.get("completion_tokens"))
    details = usage.get("completion_tokens_details") or {}
    reasoning = number(details.get("reasoning_tokens"))
    return {
        "prompt_tokens": number(usage.get("prompt_tokens")),
        "completion_tokens": completion,
        "reasoning_tokens": reasoning,
        "non_reasoning_completion_tokens": max(0, completion - reasoning),
        "total_tokens": number(usage.get("total_tokens")),
    }


def sum_metrics(items: Iterable[dict[str, int]]) -> dict[str, int]:
    keys = (
        "prompt_tokens",
        "completion_tokens",
        "reasoning_tokens",
        "non_reasoning_completion_tokens",
        "total_tokens",
    )
    result = {key: 0 for key in keys}
    for item in items:
        for key in keys:
            result[key] += item[key]
    return result


def paired_direction(values: list[tuple[int | float, int | float]]) -> dict[str, int]:
    return {
        "v2_lower": sum(new < old for old, new in values),
        "equal": sum(new == old for old, new in values),
        "v2_higher": sum(new > old for old, new in values),
    }


def main() -> int:
    selection = load_jsonl(SELECTION)
    level_by_id = {
        str(row["id"]): str(row["metadata"]["difficulty"]) for row in selection
    }
    subject_by_id = {
        str(row["id"]): str(row["metadata"]["subject"]) for row in selection
    }
    expected_ids = set(level_by_id)
    sample_data: dict[str, dict[str, dict[str, Any]]] = defaultdict(dict)
    version_summary: dict[str, dict[str, Any]] = {}
    artifacts: dict[str, dict[str, Any]] = {}

    for version in VERSIONS:
        solver_path = output_path(version, "solver")
        verification_path = output_path(version, "answer_verification")
        process_path = output_path(version, "process_evaluations")
        raw_path = output_path(version, "process_responses")
        artifact_paths = {
            "solver": solver_path,
            "solver_stream_events": output_path(version, "solver_stream_events"),
            "answer_verification": verification_path,
            "process_evaluations": process_path,
            "process_responses": raw_path,
            "process_stream_events": output_path(version, "process_stream_events"),
        }
        artifacts[version] = {
            name: {
                "path": str(path.relative_to(ROOT)),
                "sha256": sha256_file(path),
                "jsonl_records": nonempty_line_count(path),
            }
            for name, path in artifact_paths.items()
        }
        solver_rows = load_jsonl(solver_path)
        verification_rows = load_jsonl(verification_path)
        process_rows = load_jsonl(process_path)
        raw_rows = load_jsonl(raw_path)

        solver_by_id = {str(row["sample"]["id"]): row for row in solver_rows}
        verification_by_inference = {
            str(row["inference_id"]): row for row in verification_rows
        }
        process_by_inference = {str(row["inference_id"]): row for row in process_rows}
        raw_by_inference: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for row in raw_rows:
            raw_by_inference[str(row["inference_id"])].append(row)

        if set(solver_by_id) != expected_ids:
            raise ValueError(f"{version} solver sample IDs do not match selection")
        if len(solver_rows) != 25 or len(process_rows) != 25:
            raise ValueError(f"{version} must contain exactly 25 solver/process records")

        for sample_id in sorted(expected_ids):
            solver = solver_by_id[sample_id]
            inference_id = str(solver["inference_id"])
            verification = verification_by_inference[inference_id]
            process = process_by_inference[inference_id]
            evaluator_calls = raw_by_inference[inference_id]
            parsed = process["step_parse"]
            solver_usage = usage_metrics(solver["response"].get("usage"))
            evaluator_usage = sum_metrics(
                usage_metrics((call.get("response") or {}).get("usage"))
                for call in evaluator_calls
            )
            sample_data[sample_id][version] = {
                "inference_id": inference_id,
                "level": level_by_id[sample_id],
                "subject": subject_by_id[sample_id],
                "solver": {
                    "request_status": solver.get("request_status"),
                    "generation_status": solver.get("generation_status"),
                    "finish_reason": solver["response"].get("finish_reason"),
                    "latency_ms": solver["timing"].get("latency_ms"),
                    "visible_characters": len(str(solver["response"]["content"])),
                    "step_count": len(parsed["steps"]),
                    "step_parse_status": parsed["parse_status"],
                    "structure_issues": [
                        str(issue["code"]) for issue in parsed["structure_issues"]
                    ],
                    "usage": solver_usage,
                },
                "answer_verification": {
                    "verdict": verification["verification"]["verdict"],
                    "format_mismatch_but_equivalent": verification["verification"][
                        "format_mismatch_but_equivalent"
                    ],
                },
                "process": {
                    "evaluation_status": process["evaluation_status"],
                    "process_correct": process["process_correct"],
                    "needs_review": process["needs_review"],
                    "global_status": process["global_status"],
                    "process_complete": process["process_complete"],
                    "final_answer_supported": process["final_answer_supported"],
                    "first_error_step": process["first_error_step"],
                    "answer_process_relation": process["answer_process_relation"],
                    "local_statuses": dict(
                        Counter(result["status"] for result in process["step_results"])
                    ),
                    "local_importance": dict(
                        Counter(result["importance"] for result in process["step_results"])
                    ),
                    "evaluator_calls": len(evaluator_calls),
                    "complete_evaluator_calls": sum(
                        call.get("generation_status") == "complete"
                        for call in evaluator_calls
                    ),
                    "evaluator_latency_ms": round(
                        sum(number(call["timing"].get("latency_ms")) for call in evaluator_calls),
                        3,
                    ),
                    "usage": evaluator_usage,
                },
            }

        rows = [sample_data[sample_id][version] for sample_id in sorted(expected_ids)]
        solver_usages = [row["solver"]["usage"] for row in rows]
        process_usages = [row["process"]["usage"] for row in rows]
        local_statuses = Counter()
        structure_issues = Counter()
        for row in rows:
            local_statuses.update(row["process"]["local_statuses"])
            structure_issues.update(row["solver"]["structure_issues"])
        version_summary[version] = {
            "samples": len(rows),
            "solver_complete": sum(row["solver"]["finish_reason"] == "stop" for row in rows),
            "answer_correct": sum(
                row["answer_verification"]["verdict"] == "correct" for row in rows
            ),
            "format_mismatch_but_equivalent": sum(
                row["answer_verification"]["format_mismatch_but_equivalent"] for row in rows
            ),
            "steps": {
                "total": sum(row["solver"]["step_count"] for row in rows),
                "mean": mean(row["solver"]["step_count"] for row in rows),
                "median": median(row["solver"]["step_count"] for row in rows),
                "min": min(row["solver"]["step_count"] for row in rows),
                "max": max(row["solver"]["step_count"] for row in rows),
            },
            "structure_issues": dict(structure_issues),
            "visible_characters": {
                "total": sum(row["solver"]["visible_characters"] for row in rows),
                "mean": mean(row["solver"]["visible_characters"] for row in rows),
                "median": median(row["solver"]["visible_characters"] for row in rows),
            },
            "solver_usage": sum_metrics(solver_usages),
            "solver_completion_tokens": {
                "mean": mean(item["completion_tokens"] for item in solver_usages),
                "median": median(item["completion_tokens"] for item in solver_usages),
                "max": max(item["completion_tokens"] for item in solver_usages),
                "at_least_8000": sum(item["completion_tokens"] >= 8000 for item in solver_usages),
                "at_least_16000": sum(item["completion_tokens"] >= 16000 for item in solver_usages),
            },
            "solver_latency_ms": {
                "total": round(sum(number(row["solver"]["latency_ms"]) for row in rows), 3),
                "mean": mean(number(row["solver"]["latency_ms"]) for row in rows),
                "median": median(number(row["solver"]["latency_ms"]) for row in rows),
                "max": max(number(row["solver"]["latency_ms"]) for row in rows),
            },
            "process": {
                "evaluation_complete": sum(
                    row["process"]["evaluation_status"] == "complete" for row in rows
                ),
                "process_correct_true": sum(row["process"]["process_correct"] is True for row in rows),
                "process_correct_false": sum(row["process"]["process_correct"] is False for row in rows),
                "process_correct_null": sum(row["process"]["process_correct"] is None for row in rows),
                "needs_review": sum(row["process"]["needs_review"] for row in rows),
                "global_statuses": dict(Counter(row["process"]["global_status"] for row in rows)),
                "local_statuses": dict(local_statuses),
                "evaluator_calls": sum(row["process"]["evaluator_calls"] for row in rows),
                "complete_evaluator_calls": sum(
                    row["process"]["complete_evaluator_calls"] for row in rows
                ),
                "evaluator_usage": sum_metrics(process_usages),
                "evaluator_latency_ms": {
                    "total": round(sum(row["process"]["evaluator_latency_ms"] for row in rows), 3),
                    "mean_per_sample": mean(row["process"]["evaluator_latency_ms"] for row in rows),
                    "median_per_sample": median(row["process"]["evaluator_latency_ms"] for row in rows),
                },
            },
        }

        by_level: dict[str, dict[str, Any]] = {}
        for level in sorted(set(level_by_id.values())):
            level_rows = [row for row in rows if row["level"] == level]
            by_level[level] = {
                "samples": len(level_rows),
                "answer_correct": sum(
                    row["answer_verification"]["verdict"] == "correct" for row in level_rows
                ),
                "steps_mean": mean(row["solver"]["step_count"] for row in level_rows),
                "steps_total": sum(row["solver"]["step_count"] for row in level_rows),
                "structure_issue_samples": sum(
                    bool(row["solver"]["structure_issues"]) for row in level_rows
                ),
                "solver_completion_tokens_total": sum(
                    row["solver"]["usage"]["completion_tokens"] for row in level_rows
                ),
                "solver_completion_tokens_mean": mean(
                    row["solver"]["usage"]["completion_tokens"] for row in level_rows
                ),
                "solver_completion_tokens_median": median(
                    row["solver"]["usage"]["completion_tokens"] for row in level_rows
                ),
                "process_correct_true": sum(
                    row["process"]["process_correct"] is True for row in level_rows
                ),
                "needs_review": sum(row["process"]["needs_review"] for row in level_rows),
                "evaluator_calls": sum(row["process"]["evaluator_calls"] for row in level_rows),
                "evaluator_completion_tokens": sum(
                    row["process"]["usage"]["completion_tokens"] for row in level_rows
                ),
            }
        version_summary[version]["by_level"] = by_level

    paired_rows: list[dict[str, Any]] = []
    for sample_id in sorted(expected_ids):
        old = sample_data[sample_id]["v1"]
        new = sample_data[sample_id]["v2"]
        paired_rows.append(
            {
                "sample_id": sample_id,
                "level": level_by_id[sample_id],
                "subject": subject_by_id[sample_id],
                "v1": old,
                "v2": new,
                "delta_v2_minus_v1": {
                    "steps": new["solver"]["step_count"] - old["solver"]["step_count"],
                    "visible_characters": (
                        new["solver"]["visible_characters"]
                        - old["solver"]["visible_characters"]
                    ),
                    "solver_completion_tokens": (
                        new["solver"]["usage"]["completion_tokens"]
                        - old["solver"]["usage"]["completion_tokens"]
                    ),
                    "solver_total_tokens": (
                        new["solver"]["usage"]["total_tokens"]
                        - old["solver"]["usage"]["total_tokens"]
                    ),
                    "evaluator_calls": (
                        new["process"]["evaluator_calls"]
                        - old["process"]["evaluator_calls"]
                    ),
                    "evaluator_completion_tokens": (
                        new["process"]["usage"]["completion_tokens"]
                        - old["process"]["usage"]["completion_tokens"]
                    ),
                },
            }
        )

    v1 = version_summary["v1"]
    v2 = version_summary["v2"]
    comparison = {
        "delta_v2_minus_v1": {
            "steps_total": v2["steps"]["total"] - v1["steps"]["total"],
            "steps_percent": percent_change(v1["steps"]["total"], v2["steps"]["total"]),
            "visible_characters_total": (
                v2["visible_characters"]["total"] - v1["visible_characters"]["total"]
            ),
            "visible_characters_percent": percent_change(
                v1["visible_characters"]["total"], v2["visible_characters"]["total"]
            ),
            "solver_prompt_tokens": (
                v2["solver_usage"]["prompt_tokens"] - v1["solver_usage"]["prompt_tokens"]
            ),
            "solver_completion_tokens": (
                v2["solver_usage"]["completion_tokens"]
                - v1["solver_usage"]["completion_tokens"]
            ),
            "solver_completion_tokens_percent": percent_change(
                v1["solver_usage"]["completion_tokens"],
                v2["solver_usage"]["completion_tokens"],
            ),
            "solver_total_tokens": (
                v2["solver_usage"]["total_tokens"] - v1["solver_usage"]["total_tokens"]
            ),
            "solver_total_tokens_percent": percent_change(
                v1["solver_usage"]["total_tokens"], v2["solver_usage"]["total_tokens"]
            ),
            "evaluator_calls": (
                v2["process"]["evaluator_calls"] - v1["process"]["evaluator_calls"]
            ),
            "evaluator_calls_percent": percent_change(
                v1["process"]["evaluator_calls"], v2["process"]["evaluator_calls"]
            ),
            "evaluator_completion_tokens": (
                v2["process"]["evaluator_usage"]["completion_tokens"]
                - v1["process"]["evaluator_usage"]["completion_tokens"]
            ),
            "evaluator_completion_tokens_percent": percent_change(
                v1["process"]["evaluator_usage"]["completion_tokens"],
                v2["process"]["evaluator_usage"]["completion_tokens"],
            ),
            "evaluator_total_tokens": (
                v2["process"]["evaluator_usage"]["total_tokens"]
                - v1["process"]["evaluator_usage"]["total_tokens"]
            ),
            "evaluator_total_tokens_percent": percent_change(
                v1["process"]["evaluator_usage"]["total_tokens"],
                v2["process"]["evaluator_usage"]["total_tokens"],
            ),
        },
        "paired_direction": {
            "steps": paired_direction(
                [
                    (row["v1"]["solver"]["step_count"], row["v2"]["solver"]["step_count"])
                    for row in paired_rows
                ]
            ),
            "solver_completion_tokens": paired_direction(
                [
                    (
                        row["v1"]["solver"]["usage"]["completion_tokens"],
                        row["v2"]["solver"]["usage"]["completion_tokens"],
                    )
                    for row in paired_rows
                ]
            ),
            "evaluator_completion_tokens": paired_direction(
                [
                    (
                        row["v1"]["process"]["usage"]["completion_tokens"],
                        row["v2"]["process"]["usage"]["completion_tokens"],
                    )
                    for row in paired_rows
                ]
            ),
        },
    }

    analysis = {
        "schema_version": "1.0",
        "experiment": "process-evaluator-v1v2-25",
        "selection_sha256": sha256_file(SELECTION),
        "config": {
            "solver": {
                "model": "hy3",
                "temperature": 0.9,
                "top_p": 1.0,
                "max_tokens": 32000,
                "thinking": "enabled",
                "reasoning_effort": "high",
                "timeout_seconds": 300,
                "max_retries": 0,
            },
            "process_evaluator": {
                "local_prompt": "math-process-evaluator-v1",
                "global_prompt": "math-global-evaluator-v1",
                "temperature": 0.1,
                "top_p": 1.0,
                "max_tokens": 8000,
                "thinking": "enabled",
                "reasoning_effort": "high",
                "timeout_seconds": 300,
                "max_retries": 0,
            },
        },
        "artifacts": artifacts,
        "versions": version_summary,
        "comparison": comparison,
        "paired_samples": paired_rows,
    }
    OUTPUT.write_text(
        json.dumps(analysis, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "output": str(OUTPUT.relative_to(ROOT)),
                "selection_sha256": analysis["selection_sha256"],
                "v1": version_summary["v1"],
                "v2": version_summary["v2"],
                "comparison": comparison,
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
