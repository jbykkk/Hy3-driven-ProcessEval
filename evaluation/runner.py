"""Evaluate every successful inference against its benchmark reference answer."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

from evaluation.answer_verifier import verify_answer
from solver.parser import parse_solution


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BENCHMARK = ROOT / "data" / "benchmark" / "math_text.jsonl"
DEFAULT_INPUT = ROOT / "outputs" / "solver_outputs.jsonl"
DEFAULT_OUTPUT = ROOT / "outputs" / "answer_verification.jsonl"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--benchmark", type=Path, default=DEFAULT_BENCHMARK)
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--id", action="append", dest="sample_ids")
    return parser.parse_args()


def load_jsonl(path: Path) -> Iterator[tuple[int, dict[str, Any]]]:
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            try:
                yield line_number, json.loads(line)
            except json.JSONDecodeError as error:
                raise ValueError(f"Invalid JSONL at {path}:{line_number}") from error


def load_references(path: Path) -> dict[str, dict[str, str]]:
    references: dict[str, dict[str, str]] = {}
    for line_number, row in load_jsonl(path):
        try:
            sample_id = str(row["id"])
            entry = {
                "dataset": str(row["dataset"]),
                "reference_answer": str(row["reference_answer"]),
            }
        except KeyError as error:
            raise ValueError(f"Missing benchmark field at {path}:{line_number}") from error
        if sample_id in references:
            raise ValueError(f"Duplicate benchmark ID {sample_id!r}")
        references[sample_id] = entry
    return references


def evaluate_records(
    *,
    benchmark_path: Path,
    solver_output_path: Path,
    sample_ids: set[str] | None = None,
) -> list[dict[str, Any]]:
    references = load_references(benchmark_path)
    evaluated_at = datetime.now(timezone.utc).isoformat()
    results = []
    for line_number, inference in load_jsonl(solver_output_path):
        if inference.get("status") != "success":
            continue
        try:
            sample_id = str(inference["sample"]["id"])
            inference_id = str(inference["inference_id"])
            content = str(inference["response"]["content"])
            finish_reason = str(inference["response"]["finish_reason"])
        except (KeyError, TypeError) as error:
            raise ValueError(
                f"Invalid successful inference at {solver_output_path}:{line_number}"
            ) from error
        if sample_ids and sample_id not in sample_ids:
            continue
        if sample_id not in references:
            raise ValueError(f"Inference references unknown benchmark ID {sample_id!r}")

        current_parse = parse_solution(content)
        eligible_for_scoring = finish_reason == "stop"
        prediction = current_parse.final_answer if eligible_for_scoring else None
        warnings = list(current_parse.warnings)
        if not eligible_for_scoring:
            warnings.append(f"generation_not_complete:{finish_reason}")
        reference = references[sample_id]
        verification = verify_answer(reference["reference_answer"], prediction)
        results.append(
            {
                "schema_version": "1.0",
                "evaluated_at": evaluated_at,
                "inference_id": inference_id,
                "sample_id": sample_id,
                "dataset": reference["dataset"],
                "finish_reason": finish_reason,
                "eligible_for_scoring": eligible_for_scoring,
                "prediction": {
                    "value": prediction,
                    "parser_candidate": current_parse.final_answer,
                    "parser_version": current_parse.as_dict()["parser_version"],
                    "warnings": warnings,
                },
                "reference_answer": reference["reference_answer"],
                "verification": verification.as_dict(),
            }
        )
    return results


def write_jsonl(path: Path, records: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False, separators=(",", ":")) + "\n")


def main() -> int:
    args = parse_args()
    try:
        records = evaluate_records(
            benchmark_path=args.benchmark,
            solver_output_path=args.input,
            sample_ids=set(args.sample_ids) if args.sample_ids else None,
        )
        write_jsonl(args.output, records)
        equivalent_formats = sum(
            row["verification"]["format_mismatch_but_equivalent"] for row in records
        )
        counts: dict[str, int] = {}
        for row in records:
            verdict = row["verification"]["verdict"]
            counts[verdict] = counts.get(verdict, 0) + 1
        print(
            json.dumps(
                {
                    "evaluated": len(records),
                    "verdicts": counts,
                    "format_mismatch_but_equivalent": equivalent_formats,
                    "output": str(args.output),
                },
                ensure_ascii=False,
            )
        )
        return 0
    except (OSError, ValueError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
