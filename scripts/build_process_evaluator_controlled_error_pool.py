"""Build a unified index of historical and newly constructed controlled errors."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
OLD_DIR = ROOT / "experiments" / "process_evaluator_error_injection_level4"
NEW_DIR = ROOT / "experiments" / "process_evaluator_error_injection_16"
OUTPUT_DIR = ROOT / "experiments" / "process_evaluator_controlled_error_pool"
INDEX_PATH = OUTPUT_DIR / "index.jsonl"
MANIFEST_PATH = OUTPUT_DIR / "manifest.json"


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def write_jsonl(path: Path, records: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False, separators=(",", ":")) + "\n")


def main() -> int:
    rows: list[dict[str, Any]] = []
    old_analysis = load_json(OLD_DIR / "analysis.json")
    old_actual = {row["case_id"]: row for row in old_analysis["cases"]}
    for case in load_jsonl(OLD_DIR / "cases.jsonl"):
        result = old_actual[case["case_id"]]
        rows.append(
            {
                "schema_version": "1.0",
                "case_id": case["case_id"],
                "sample_id": case["sample_id"],
                "difficulty": case["difficulty"],
                "subject": case["subject"],
                "source_experiment": "process-evaluator-error-injection-level4-v1",
                "source_cases_path": str((OLD_DIR / "cases.jsonl").relative_to(ROOT)),
                "solver_prompt_version": case["solver_prompt_version"],
                "error_type": case["injection"]["first_error_type"],
                "first_error_step": case["injection"]["first_error_step"],
                "expected_answer_correct": case["expected"]["answer_correct"],
                "expected_answer_process_relation": case["expected"]["answer_process_relation"],
                "evaluation_status": "evaluated",
                "evaluation_analysis_path": str((OLD_DIR / "analysis.json").relative_to(ROOT)),
                "evaluation_summary": {
                    "process_error_detected": result["actual"]["process_correct"] is False,
                    "first_error_step": result["actual"]["first_error_step"],
                    "first_error_type": result["actual"]["first_error_type"],
                    "answer_process_relation": result["actual"]["answer_process_relation"],
                    "matches": result["matches"],
                },
            }
        )

    new_evaluation_path = NEW_DIR / "evaluation_analysis.json"
    new_results = (
        {row["case_id"]: row for row in load_json(new_evaluation_path)["cases"]}
        if new_evaluation_path.is_file()
        else {}
    )
    for case in load_jsonl(NEW_DIR / "cases.jsonl"):
        result = new_results.get(case["case_id"])
        rows.append(
            {
                "schema_version": "1.0",
                "case_id": case["case_id"],
                "sample_id": case["sample_id"],
                "difficulty": case["difficulty"],
                "subject": case["subject"],
                "source_experiment": "process-evaluator-error-injection-16",
                "source_cases_path": str((NEW_DIR / "cases.jsonl").relative_to(ROOT)),
                "solver_prompt_version": case["solver_prompt_version"],
                "error_type": case["injection"]["first_error_type"],
                "first_error_step": case["injection"]["first_error_step"],
                "expected_answer_correct": case["expected"]["answer_correct"],
                "expected_answer_process_relation": case["expected"]["answer_process_relation"],
                "evaluation_status": "evaluated" if result is not None else "not_run",
                "evaluation_analysis_path": (
                    str(new_evaluation_path.relative_to(ROOT))
                    if result is not None
                    else None
                ),
                "evaluation_summary": (
                    {
                        "process_error_detected": result["process_error_detected"],
                        "first_error_step": result["actual"]["first_error_step"],
                        "first_error_type": result["actual"]["first_error_type"],
                        "answer_process_relation": result["actual"]["answer_process_relation"],
                        "first_error_step_matches": result["first_error_step_matches"],
                        "error_type_matches": result["error_type_matches"],
                        "needs_review": result["needs_review"],
                    }
                    if result is not None
                    else None
                ),
            }
        )

    case_ids = [row["case_id"] for row in rows]
    if len(rows) != 20 or len(case_ids) != len(set(case_ids)):
        raise ValueError("Controlled-error pool must contain 20 unique cases")
    write_jsonl(INDEX_PATH, rows)
    manifest = {
        "schema_version": "1.0",
        "dataset": "process-evaluator-controlled-error-pool",
        "cases": len(rows),
        "unique_source_samples": len({row["sample_id"] for row in rows}),
        "source_experiments": {
            "process-evaluator-error-injection-level4-v1": 4,
            "process-evaluator-error-injection-16": 16,
        },
        "evaluation_status": dict(
            sorted(Counter(row["evaluation_status"] for row in rows).items())
        ),
        "levels_by_case": dict(sorted(Counter(row["difficulty"] for row in rows).items())),
        "error_types_by_case": dict(
            sorted(Counter(row["error_type"] for row in rows).items())
        ),
        "expected_correct_answer_cases": sum(
            bool(row["expected_answer_correct"]) for row in rows
        ),
        "index": str(INDEX_PATH.relative_to(ROOT)),
        "note": (
            "The historical Level 4 source question contributes four v1/v2 and "
            "correct/wrong-answer variants. The new set contributes sixteen distinct "
            "source questions. Case counts and unique-source counts are not interchangeable."
        ),
    }
    MANIFEST_PATH.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
