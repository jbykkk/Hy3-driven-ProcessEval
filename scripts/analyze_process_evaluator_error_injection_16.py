"""Validate and summarize the constructed 16-case controlled-error dataset."""

from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from process_evaluation.step_parser import parse_process_steps


EXPERIMENT_DIR = ROOT / "experiments" / "process_evaluator_error_injection_16"
CASES_PATH = EXPERIMENT_DIR / "cases.jsonl"
SOLVER_PATH = ROOT / "outputs" / "process_evaluator_error_injection_16_solver.jsonl"
ANSWER_PATH = (
    ROOT / "outputs" / "process_evaluator_error_injection_16_answer_verification.jsonl"
)
ANALYSIS_PATH = EXPERIMENT_DIR / "analysis.json"
EVALUATION_ANALYSIS_PATH = EXPERIMENT_DIR / "evaluation_analysis.json"


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def main() -> int:
    cases = load_jsonl(CASES_PATH)
    solver = {str(row["inference_id"]): row for row in load_jsonl(SOLVER_PATH)}
    answers = {str(row["inference_id"]): row for row in load_jsonl(ANSWER_PATH)}
    details: list[dict[str, Any]] = []
    for case in cases:
        inference_id = str(case["injected_inference_id"])
        record = solver.get(inference_id)
        answer = answers.get(inference_id)
        if record is None or answer is None:
            raise ValueError(f"Missing constructed evidence for {inference_id}")
        solver_parse = record["parsed"]
        process_parse = parse_process_steps(str(record["response"]["content"]))
        step_ids = [step.step_id for step in process_parse.steps]
        expected_step = case["injection"]["first_error_step"]
        if expected_step is not None and expected_step not in step_ids:
            raise ValueError(f"Expected Step {expected_step} missing from {case['case_id']}")
        actual_correct = answer["verification"]["verdict"] == "correct"
        expected_correct = bool(case["expected"]["answer_correct"])
        details.append(
            {
                "case_id": case["case_id"],
                "sample_id": case["sample_id"],
                "difficulty": case["difficulty"],
                "subject": case["subject"],
                "error_type": case["injection"]["first_error_type"],
                "first_error_step": expected_step,
                "step_ids": step_ids,
                "solver_parser_warnings": solver_parse["warnings"],
                "process_parse_status": process_parse.parse_status,
                "process_structure_issues": [
                    issue.as_dict() if hasattr(issue, "as_dict") else {
                        "code": issue.code,
                        "message": issue.message,
                        "step_id": issue.step_id,
                    }
                    for issue in process_parse.structure_issues
                ],
                "expected_answer_correct": expected_correct,
                "actual_answer_verdict": answer["verification"]["verdict"],
                "answer_expectation_matches": expected_correct == actual_correct,
                "answer_process_relation": case["expected"]["answer_process_relation"],
            }
        )

    analysis = {
        "schema_version": "1.0",
        "experiment": "process-evaluator-error-injection-16",
        "construction_status": "validated",
        "records": len(details),
        "levels": dict(sorted(Counter(row["difficulty"] for row in details).items())),
        "error_types": dict(sorted(Counter(row["error_type"] for row in details).items())),
        "solver_parser_warning_records": sum(
            bool(row["solver_parser_warnings"]) for row in details
        ),
        "process_structure_issue_records": sum(
            bool(row["process_structure_issues"]) for row in details
        ),
        "answer_expectation_matches": sum(
            bool(row["answer_expectation_matches"]) for row in details
        ),
        "answer_verdicts": dict(
            sorted(Counter(row["actual_answer_verdict"] for row in details).items())
        ),
        "correct_answer_invalid_process_cases": [
            row["case_id"] for row in details if row["expected_answer_correct"]
        ],
        "process_evaluator_status": (
            "complete" if EVALUATION_ANALYSIS_PATH.is_file() else "not_run"
        ),
        "cases": details,
    }
    if len(details) != 16:
        raise ValueError("Expected 16 cases")
    if analysis["solver_parser_warning_records"] != 0:
        raise ValueError("Constructed records contain parser warnings")
    if analysis["process_structure_issue_records"] != 0:
        raise ValueError("Constructed records contain process structure issues")
    if analysis["answer_expectation_matches"] != 16:
        raise ValueError("Answer verification does not match expected labels")
    ANALYSIS_PATH.write_text(
        json.dumps(analysis, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(analysis, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
