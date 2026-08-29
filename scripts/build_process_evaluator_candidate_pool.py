"""Index the earlier 25 and new Level 4/5 20 v2 Solver inferences."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
POOL_DIR = ROOT / "experiments" / "process_evaluator_candidate_pool_45"
INDEX = POOL_DIR / "index.jsonl"
MANIFEST = POOL_DIR / "manifest.json"
NEW_ANALYSIS = (
    ROOT / "experiments" / "process_evaluator_v2_level45_20" / "analysis.json"
)

SOURCES = (
    {
        "name": "v1v2-25-v2",
        "selection": ROOT
        / "experiments"
        / "process_evaluator_v1v2_25"
        / "selection.jsonl",
        "solver": ROOT / "outputs" / "process_v1v2_25_v2_solver.jsonl",
        "verification": ROOT
        / "outputs"
        / "process_v1v2_25_v2_answer_verification.jsonl",
        "expected": 25,
    },
    {
        "name": "level45-20-v2",
        "selection": ROOT
        / "experiments"
        / "process_evaluator_v2_level45_20"
        / "selection.jsonl",
        "solver": ROOT / "outputs" / "process_v2_level45_20_solver.jsonl",
        "verification": ROOT
        / "outputs"
        / "process_v2_level45_20_answer_verification.jsonl",
        "expected": 20,
    },
)


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError as error:
                raise ValueError(f"Invalid JSONL at {path}:{line_number}") from error
    return records


def successful_by_sample(path: Path) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for row in load_jsonl(path):
        if row.get("request_status") != "success":
            continue
        sample_id = str(row["sample"]["id"])
        if sample_id in result:
            raise ValueError(f"Multiple successful inferences for {sample_id} in {path}")
        result[sample_id] = row
    return result


def verification_by_inference(path: Path) -> dict[str, dict[str, Any]]:
    return {str(row["inference_id"]): row for row in load_jsonl(path)}


def relative(path: Path) -> str:
    return str(path.relative_to(ROOT))


def write_jsonl(path: Path, records: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False, separators=(",", ":")) + "\n")


def main() -> int:
    index: list[dict[str, Any]] = []
    new_solver_rows: list[dict[str, Any]] = []
    new_verifications: list[dict[str, Any]] = []
    source_counts: dict[str, int] = {}

    for source in SOURCES:
        selection = load_jsonl(source["selection"])
        successful = successful_by_sample(source["solver"])
        verifications = verification_by_inference(source["verification"])
        if len(selection) != source["expected"] or len(successful) != source["expected"]:
            raise ValueError(f"Incomplete source {source['name']}")
        source_counts[str(source["name"])] = len(selection)
        for sample in selection:
            sample_id = str(sample["id"])
            inference = successful.get(sample_id)
            if inference is None:
                raise ValueError(f"Missing successful v2 inference for {sample_id}")
            inference_id = str(inference["inference_id"])
            verification = verifications.get(inference_id)
            if verification is None:
                raise ValueError(f"Missing answer verification for {inference_id}")
            prompt_version = str(inference["prompt"]["template_version"])
            if prompt_version != "math-solver-v2":
                raise ValueError(f"Unexpected prompt version for {sample_id}: {prompt_version}")
            if inference.get("generation_status") != "complete":
                raise ValueError(f"Incomplete generation for {sample_id}")
            index.append(
                {
                    "schema_version": "1.0",
                    "sample_id": sample_id,
                    "difficulty": sample["metadata"]["difficulty"],
                    "subject": sample["metadata"]["subject"],
                    "source_group": source["name"],
                    "selection_path": relative(source["selection"]),
                    "solver_output_path": relative(source["solver"]),
                    "inference_id": inference_id,
                    "prompt_version": prompt_version,
                    "generation_status": inference["generation_status"],
                    "answer_verification_path": relative(source["verification"]),
                    "answer_verdict": verification["verification"]["verdict"],
                }
            )
        if source["name"] == "level45-20-v2":
            new_solver_rows = load_jsonl(source["solver"])
            new_verifications = list(verifications.values())

    ids = [row["sample_id"] for row in index]
    if len(index) != 45 or len(ids) != len(set(ids)):
        raise ValueError("Candidate pool must contain 45 unique samples")
    if any(row["answer_verdict"] != "correct" for row in index):
        raise ValueError("Candidate pool contains a non-correct answer")

    write_jsonl(INDEX, index)
    manifest = {
        "schema_version": "1.0",
        "dataset": "process-evaluator-candidate-pool-45",
        "purpose": (
            "Frozen v2 Solver outputs available for controlled error injection and "
            "Process Evaluator development; not an accuracy benchmark without independent labels."
        ),
        "records": len(index),
        "source_groups": source_counts,
        "levels": dict(sorted(Counter(row["difficulty"] for row in index).items())),
        "subjects": dict(sorted(Counter(row["subject"] for row in index).items())),
        "prompt_versions": ["math-solver-v2"],
        "complete_generations": sum(
            row["generation_status"] == "complete" for row in index
        ),
        "correct_answers": sum(row["answer_verdict"] == "correct" for row in index),
        "index": relative(INDEX),
        "evidence_boundary": (
            "The index stores inference references only. Visible solutions and internal "
            "reasoning remain in ignored local outputs and are not copied into Git."
        ),
    }
    MANIFEST.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    successes = [row for row in new_solver_rows if row.get("request_status") == "success"]
    errors = [row for row in new_solver_rows if row.get("request_status") == "error"]
    total_tokens = sum(int(row["response"]["usage"]["total_tokens"]) for row in successes)
    reasoning_tokens = sum(
        int(row["response"]["usage"]["completion_tokens_details"]["reasoning_tokens"])
        for row in successes
    )
    analysis = {
        "schema_version": "1.0",
        "experiment": "process-evaluator-v2-level45-20",
        "selected_samples": 20,
        "preflight_connection_errors": len(errors),
        "api_successes": len(successes),
        "complete_generations": sum(
            row.get("generation_status") == "complete" for row in successes
        ),
        "parser_warning_records": sum(bool(row["parsed"]["warnings"]) for row in successes),
        "answer_verdicts": dict(
            sorted(Counter(row["verification"]["verdict"] for row in new_verifications).items())
        ),
        "format_mismatch_but_equivalent": sum(
            bool(row["verification"]["format_mismatch_but_equivalent"])
            for row in new_verifications
        ),
        "manual_review_recommended": sum(
            bool(row["verification"]["manual_review_recommended"])
            for row in new_verifications
        ),
        "usage": {
            "total_tokens": total_tokens,
            "reasoning_tokens": reasoning_tokens,
            "reasoning_share_of_total": round(reasoning_tokens / total_tokens, 6),
        },
        "artifacts": {
            "solver": "outputs/process_v2_level45_20_solver.jsonl",
            "solver_stream_events": "outputs/process_v2_level45_20_solver_stream_events.jsonl",
            "answer_verification": "outputs/process_v2_level45_20_answer_verification.jsonl",
        },
    }
    NEW_ANALYSIS.write_text(
        json.dumps(analysis, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps({"pool": manifest, "new_experiment": analysis}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
