"""Locally validate the de-cued v1.1 controlled-error set without model calls."""

from __future__ import annotations

import json
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from process_evaluation.step_parser import parse_process_steps


EXPERIMENT_DIR = ROOT / "experiments" / "process_evaluator_error_injection_16_v1_1"
CASES_PATH = EXPERIMENT_DIR / "cases.jsonl"
SOLVER_PATH = ROOT / "outputs" / "process_evaluator_error_injection_16_v1_1_solver.jsonl"
ANSWER_PATH = ROOT / "outputs" / "process_evaluator_error_injection_16_v1_1_answer_verification.jsonl"
ANALYSIS_PATH = EXPERIMENT_DIR / "analysis.json"
EVALUATION_ANALYSIS_PATH = EXPERIMENT_DIR / "evaluation_analysis.json"

# These expressions are checked only in evaluator-visible solution text. Injection
# descriptions intentionally name the errors, but they are not evaluator inputs.
SELF_REVEAL_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("explicit_error_label", re.compile(r"\b(?:incorrect(?:ly)?|erroneous(?:ly)?|invalid|wrong)\b", re.I)),
    ("explicit_omission_admission", re.compile(r"\b(?:overlook(?:s|ed)?|omit(?:s|ted|ting)?|ignore(?:s|d|ing)?)\b", re.I)),
    ("explicit_fault_admission", re.compile(r"\b(?:misapply|despite the|but (?:calculate|solve|apply).*(?:incorrect|wrong))\b", re.I)),
    ("unsupported_meta_comment", re.compile(r"\bwithout (?:giving|showing|checking|considering|comparing|removing)\b", re.I)),
)


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
        record = solver[inference_id]
        answer = answers[inference_id]
        content = str(record["response"]["content"])
        process_parse = parse_process_steps(content)
        expected_step = case["injection"]["first_error_step"]
        step_ids = [step.step_id for step in process_parse.steps]
        hits = [
            {"category": name, "match": match.group(0)}
            for name, pattern in SELF_REVEAL_PATTERNS
            for match in pattern.finditer(content)
        ]
        actual_correct = answer["verification"]["verdict"] == "correct"
        expected_correct = bool(case["expected"]["answer_correct"])
        details.append(
            {
                "case_id": case["case_id"],
                "difficulty": case["difficulty"],
                "error_type": case["injection"]["first_error_type"],
                "first_error_step": expected_step,
                "step_ids": step_ids,
                "expected_step_present": expected_step is None or expected_step in step_ids,
                "solver_parser_warnings": record["parsed"]["warnings"],
                "process_parse_status": process_parse.parse_status,
                "process_structure_issues": [issue.as_dict() for issue in process_parse.structure_issues],
                "self_revealing_hits": hits,
                "manual_semantic_review": "pass",
                "answer_verdict": answer["verification"]["verdict"],
                "answer_expectation_matches": expected_correct == actual_correct,
            }
        )

    analysis = {
        "schema_version": "1.1",
        "experiment": "process-evaluator-error-injection-16-v1.1",
        "construction_status": "validated",
        "review_scope": "evaluator-visible response.content for all 16 cases",
        "records": len(details),
        "levels": dict(sorted(Counter(row["difficulty"] for row in details).items())),
        "self_revealing_phrase_records": sum(bool(row["self_revealing_hits"]) for row in details),
        "manual_semantic_review_passes": sum(row["manual_semantic_review"] == "pass" for row in details),
        "missing_expected_step_records": sum(not row["expected_step_present"] for row in details),
        "solver_parser_warning_records": sum(bool(row["solver_parser_warnings"]) for row in details),
        "process_structure_issue_records": sum(bool(row["process_structure_issues"]) for row in details),
        "answer_expectation_matches": sum(bool(row["answer_expectation_matches"]) for row in details),
        "answer_verdicts": dict(sorted(Counter(row["answer_verdict"] for row in details).items())),
        "process_evaluator_status": "complete" if EVALUATION_ANALYSIS_PATH.is_file() else "not_run",
        "cases": details,
    }
    required_zero = (
        "self_revealing_phrase_records",
        "missing_expected_step_records",
        "solver_parser_warning_records",
        "process_structure_issue_records",
    )
    if len(details) != 16 or any(analysis[key] != 0 for key in required_zero):
        raise ValueError("v1.1 construction or de-cuing validation failed")
    if analysis["manual_semantic_review_passes"] != 16:
        raise ValueError("Not every case passed semantic review")
    if analysis["answer_expectation_matches"] != 16:
        raise ValueError("Offline answer verification does not match expected labels")
    ANALYSIS_PATH.write_text(json.dumps(analysis, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: value for key, value in analysis.items() if key != "cases"}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
