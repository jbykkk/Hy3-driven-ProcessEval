"""Compare the controlled Level-4 error-injection probe with expected labels."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any, Iterator


ROOT = Path(__file__).resolve().parents[1]
EXPERIMENT_DIR = ROOT / "experiments" / "process_evaluator_error_injection_level4"
DEFAULT_CASES = EXPERIMENT_DIR / "cases.jsonl"
DEFAULT_PROCESS = ROOT / "outputs" / "process_error_injection_level4_process_evaluations.jsonl"
DEFAULT_RAW = ROOT / "outputs" / "process_error_injection_level4_process_responses.jsonl"
DEFAULT_ANALYSIS = EXPERIMENT_DIR / "analysis.json"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cases", type=Path, default=DEFAULT_CASES)
    parser.add_argument("--process", type=Path, default=DEFAULT_PROCESS)
    parser.add_argument("--raw", type=Path, default=DEFAULT_RAW)
    parser.add_argument("--output", type=Path, default=DEFAULT_ANALYSIS)
    return parser.parse_args()


def load_jsonl(path: Path) -> Iterator[dict[str, Any]]:
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                value = json.loads(line)
                if not isinstance(value, dict):
                    raise ValueError(f"JSON object required in {path}")
                yield value


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def latest_complete_process(path: Path) -> dict[str, dict[str, Any]]:
    results: dict[str, dict[str, Any]] = {}
    for row in load_jsonl(path):
        if row.get("evaluation_status") == "complete":
            results[str(row["inference_id"])] = row
    return results


def main() -> int:
    args = parse_args()
    cases = list(load_jsonl(args.cases))
    process = latest_complete_process(args.process)
    if len(process) != len(cases):
        raise ValueError(f"Expected {len(cases)} complete results, found {len(process)}")

    comparisons: list[dict[str, Any]] = []
    for case in cases:
        actual = process[case["inference_id"]]
        first_step = int(case["injection"]["first_error_step"])
        local = next(
            result for result in actual["step_results"] if result["step_id"] == first_step
        )
        inherited_steps = [
            result["step_id"]
            for result in actual["step_results"]
            if result["error_origin"] == "inherited"
        ]
        expected = case["expected"]
        matches = {
            "answer_correct": actual["answer_correct"] == expected["answer_correct"],
            "first_error_step": actual["first_error_step"] == first_step,
            "first_error_status": local["status"] == case["injection"]["first_error_status"],
            "first_error_importance": (
                local["importance"] == case["injection"]["first_error_importance"]
            ),
            "first_error_type": (
                actual["first_error_type"] == case["injection"]["first_error_type"]
            ),
            "first_error_origin": (
                local["error_origin"] == case["injection"]["first_error_origin"]
            ),
            "global_status": actual["global_status"] == expected["global_status"],
            "final_answer_supported": (
                actual["final_answer_supported"] == expected["final_answer_supported"]
            ),
            "process_correct": actual["process_correct"] == expected["process_correct"],
            "answer_process_relation": (
                actual["answer_process_relation"] == expected["answer_process_relation"]
            ),
        }
        comparisons.append(
            {
                "case_id": case["case_id"],
                "solver_prompt_version": case["solver_prompt_version"],
                "answer_mode": "correct" if expected["answer_correct"] else "wrong",
                "actual": {
                    "answer_correct": actual["answer_correct"],
                    "first_error_step": actual["first_error_step"],
                    "first_error_type": actual["first_error_type"],
                    "first_error_local_result": local,
                    "inherited_step_ids": inherited_steps,
                    "global_status": actual["global_status"],
                    "process_complete": actual["process_complete"],
                    "final_answer_supported": actual["final_answer_supported"],
                    "global_error_type": actual["global_error_type"],
                    "first_error_step_override": actual["first_error_step_override"],
                    "process_correct": actual["process_correct"],
                    "answer_process_relation": actual["answer_process_relation"],
                    "needs_review": actual["needs_review"],
                },
                "matches": matches,
            }
        )

    successful_calls = [
        row for row in load_jsonl(args.raw) if row.get("request_status") == "success"
    ]
    failed_calls = [row for row in load_jsonl(args.raw) if row.get("request_status") == "error"]
    metric_names = list(comparisons[0]["matches"])
    metric_matches = {
        name: sum(1 for row in comparisons if row["matches"][name])
        for name in metric_names
    }
    analysis = {
        "schema_version": "1.0",
        "experiment": "process-evaluator-error-injection-level4-v1",
        "case_count": len(cases),
        "summary": {
            "complete_process_evaluations": len(process),
            "process_error_detected": sum(
                1 for row in comparisons if row["actual"]["process_correct"] is False
            ),
            "needs_review": sum(1 for row in comparisons if row["actual"]["needs_review"]),
            "metric_matches": metric_matches,
            "metric_total": len(comparisons),
            "final_answer_supported_note": (
                "Under the frozen mathematical-support definition, both wrong-answer "
                "variants must be false. The historical v1 result was false and the "
                "historical v2 result was true, so v2 is a mismatch under the new definition."
            ),
        },
        "api_calls": {
            "successful": len(successful_calls),
            "sandbox_connection_failures_before_escalated_run": len(failed_calls),
            "completion_tokens": sum(
                ((row.get("response") or {}).get("usage") or {}).get("completion_tokens", 0)
                for row in successful_calls
            ),
            "reasoning_tokens": sum(
                ((((row.get("response") or {}).get("usage") or {}).get(
                    "completion_tokens_details"
                ) or {}).get("reasoning_tokens", 0))
                for row in successful_calls
            ),
            "total_tokens": sum(
                ((row.get("response") or {}).get("usage") or {}).get("total_tokens", 0)
                for row in successful_calls
            ),
            "latency_ms": round(
                sum((row.get("timing") or {}).get("latency_ms", 0) for row in successful_calls),
                3,
            ),
        },
        "cases": comparisons,
        "artifacts": {
            "cases": {"path": str(args.cases.relative_to(ROOT)), "sha256": sha256_file(args.cases)},
            "process": {
                "path": str(args.process.relative_to(ROOT)),
                "sha256": sha256_file(args.process),
            },
            "raw": {"path": str(args.raw.relative_to(ROOT)), "sha256": sha256_file(args.raw)},
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(analysis, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(analysis["summary"], ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
