"""Compare Process Evaluator predictions with the 16-case controlled labels."""

from __future__ import annotations

import json
import argparse
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
EXPERIMENT_DIR = ROOT / "experiments" / "process_evaluator_error_injection_16"
CASES_PATH = EXPERIMENT_DIR / "cases.jsonl"
EVALUATIONS_PATH = ROOT / "outputs" / "process_error16_evaluations.jsonl"
RESPONSES_PATH = ROOT / "outputs" / "process_error16_responses.jsonl"
ANALYSIS_PATH = EXPERIMENT_DIR / "evaluation_analysis.json"


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def bool_count(rows: list[dict[str, Any]], key: str) -> int:
    return sum(bool(row[key]) for row in rows)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cases", type=Path, default=CASES_PATH)
    parser.add_argument("--evaluations", type=Path, default=EVALUATIONS_PATH)
    parser.add_argument("--responses", type=Path, default=RESPONSES_PATH)
    parser.add_argument("--analysis", type=Path, default=ANALYSIS_PATH)
    parser.add_argument("--experiment", default="process-evaluator-error-injection-16")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    cases = load_jsonl(args.cases)
    evaluations = {str(row["inference_id"]): row for row in load_jsonl(args.evaluations)}
    responses = load_jsonl(args.responses)
    details: list[dict[str, Any]] = []

    for case in cases:
        inference_id = str(case["injected_inference_id"])
        actual = evaluations.get(inference_id)
        if actual is None:
            raise ValueError(f"Missing evaluation for {inference_id}")
        expected_step = case["injection"]["first_error_step"]
        expected_type = case["injection"]["first_error_type"]
        local_at_expected = next(
            (
                step
                for step in actual["step_results"]
                if step["step_id"] == expected_step
            ),
            None,
        )
        classified_type = (
            actual["global_error_type"]
            if expected_step is None
            else actual["first_error_type"]
        )
        expected = case["expected"]
        row = {
            "case_id": case["case_id"],
            "inference_id": inference_id,
            "sample_id": case["sample_id"],
            "difficulty": case["difficulty"],
            "subject": case["subject"],
            "expected_error_type": expected_type,
            "predicted_first_error_step": actual["first_error_step"],
            "predicted_first_error_type": actual["first_error_type"],
            "predicted_global_error_type": actual["global_error_type"],
            "predicted_classified_type": classified_type,
            "process_error_detected": actual["process_correct"] is False,
            "first_error_step_matches": actual["first_error_step"] == expected_step,
            "error_type_matches": classified_type == expected_type,
            "local_status_matches": (
                None
                if expected_step is None
                else local_at_expected is not None
                and local_at_expected["status"] == case["injection"]["first_error_status"]
            ),
            "local_importance_matches": (
                None
                if expected_step is None
                else local_at_expected is not None
                and local_at_expected["importance"]
                == case["injection"]["first_error_importance"]
            ),
            "local_error_type_matches": (
                None
                if expected_step is None
                else local_at_expected is not None
                and local_at_expected["error_type"] == expected_type
            ),
            "local_error_origin_matches": (
                None
                if expected_step is None
                else local_at_expected is not None
                and local_at_expected["error_origin"]
                == case["injection"]["first_error_origin"]
            ),
            "global_status_matches": actual["global_status"] == expected["global_status"],
            "process_complete_matches": actual["process_complete"]
            == expected["process_complete"],
            "final_answer_supported_matches": actual["final_answer_supported"]
            == expected["final_answer_supported"],
            "process_correct_matches": actual["process_correct"]
            == expected["process_correct"],
            "answer_process_relation_matches": actual["answer_process_relation"]
            == expected["answer_process_relation"],
            "needs_review": actual["needs_review"],
            "actual": {
                "first_error_step": actual["first_error_step"],
                "first_error_type": actual["first_error_type"],
                "global_status": actual["global_status"],
                "process_complete": actual["process_complete"],
                "final_answer_supported": actual["final_answer_supported"],
                "process_correct": actual["process_correct"],
                "answer_process_relation": actual["answer_process_relation"],
            },
        }
        details.append(row)

    local_rows = [row for row in details if row["local_status_matches"] is not None]
    usage_by_stage: dict[str, dict[str, int]] = defaultdict(
        lambda: {"calls": 0, "prompt_tokens": 0, "completion_tokens": 0, "reasoning_tokens": 0, "total_tokens": 0, "latency_ms": 0}
    )
    for response in responses:
        usage = (response.get("response") or {}).get("usage") or {}
        completion_details = usage.get("completion_tokens_details") or {}
        stage = str(response["stage"])
        target = usage_by_stage[stage]
        target["calls"] += 1
        target["prompt_tokens"] += int(usage.get("prompt_tokens") or 0)
        target["completion_tokens"] += int(usage.get("completion_tokens") or 0)
        target["reasoning_tokens"] += int(completion_details.get("reasoning_tokens") or 0)
        target["total_tokens"] += int(usage.get("total_tokens") or 0)
        target["latency_ms"] += round(float(response["timing"]["latency_ms"]))

    total_usage = {
        key: sum(stage[key] for stage in usage_by_stage.values())
        for key in ("calls", "prompt_tokens", "completion_tokens", "reasoning_tokens", "total_tokens", "latency_ms")
    }
    if args.experiment.endswith("v1.1"):
        known_limitations = [
            "The v1.1 visible solutions were manually constructed controlled probes, not naturally generated error solutions; results measure evaluator behavior on these probes.",
            "The case_omission, condition_omission, and invalid_derivation labels are human construction labels. The evaluator may reasonably choose a neighboring fixed category when the same mathematical symptom admits multiple descriptions.",
            "A connection-failure retry occurred before the successful run. Failed attempts contain no model usage or reasoning; they remain in the raw response and stream-event files and are excluded from successful-call metrics.",
        ]
    else:
        known_limitations = [
            "Several injected steps contain self-revealing wording such as incorrect, overlooks, or erroneous, which makes detection and classification easier than natural errors.",
            "The Level 3 nonempty-set and Level 4 excluded-vertex cases explicitly acknowledge the violated condition, so Local treated those statements as valid observations and Global classified the final answer mismatch instead.",
            "The Level 5 negative-radius case received a false-positive Local calculation_error at Step 7 because multiplying an equation by -1 was treated as an unmentioned error; Local Step 7 then conflicted with Global Step 9.",
        ]
    analysis = {
        "schema_version": "1.0",
        "experiment": args.experiment,
        "evaluation_status": "complete",
        "config": {
            "local_prompt": "math-process-evaluator-v1",
            "global_prompt": "math-global-evaluator-v1.1",
            "model": "hy3",
            "temperature": 0.1,
            "top_p": 1.0,
            "max_tokens": 8000,
            "thinking": "enabled",
            "reasoning_effort": "high",
            "timeout_seconds": 300,
            "max_retries": 0,
        },
        "calls": {
            "expected_successful": 95,
            "raw_records": len(responses),
            "recorded_successful": sum(
                row.get("request_status") == "success" for row in responses
            ),
            "recorded_failed_attempts": sum(
                row.get("request_status") == "error" for row in responses
            ),
            "request_success": sum(
                row.get("request_status") == "success" for row in responses
            ),
            "generation_complete": sum(
                row.get("generation_status") == "complete" for row in responses
            ),
            "strict_schema_valid": sum(
                not row.get("attempt_errors") and row.get("generation_status") == "complete"
                for row in responses
            ),
        },
        "metrics": {
            "cases": len(details),
            "process_error_detected": bool_count(details, "process_error_detected"),
            "first_error_step_exact": bool_count(details, "first_error_step_matches"),
            "error_type_exact": bool_count(details, "error_type_matches"),
            "local_denominator": len(local_rows),
            "local_status_exact": bool_count(local_rows, "local_status_matches"),
            "local_importance_exact": bool_count(local_rows, "local_importance_matches"),
            "local_error_type_exact": bool_count(local_rows, "local_error_type_matches"),
            "local_error_origin_exact": bool_count(local_rows, "local_error_origin_matches"),
            "global_status_exact": bool_count(details, "global_status_matches"),
            "process_complete_exact": bool_count(details, "process_complete_matches"),
            "final_answer_supported_exact": bool_count(
                details, "final_answer_supported_matches"
            ),
            "process_correct_exact": bool_count(details, "process_correct_matches"),
            "answer_process_relation_exact": bool_count(
                details, "answer_process_relation_matches"
            ),
            "needs_review": bool_count(details, "needs_review"),
        },
        "predicted_error_types": dict(
            sorted(Counter(row["predicted_classified_type"] or "unresolved" for row in details).items())
        ),
        "usage": {
            "by_stage": dict(usage_by_stage),
            "total": total_usage,
            "reasoning_share_of_total": round(
                total_usage["reasoning_tokens"] / total_usage["total_tokens"], 6
            ),
        },
        "known_limitations": known_limitations,
        "cases": details,
    }
    successful_responses = sum(row.get("request_status") == "success" for row in responses)
    if len(details) != 16 or successful_responses != 95:
        raise ValueError("Incomplete evaluation evidence")
    if analysis["calls"]["request_success"] != 95 or analysis["calls"]["generation_complete"] != 95:
        raise ValueError("Evaluator calls were not all successful and complete")
    args.analysis.write_text(
        json.dumps(analysis, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(analysis, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
