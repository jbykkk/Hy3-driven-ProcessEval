"""Build the deterministic MATH benchmark and its text-only variant."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable

import pyarrow.parquet as pq


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RAW_DIR = ROOT / "data" / "raw"
DEFAULT_OUTPUT_DIR = ROOT / "data" / "benchmark"
DEFAULT_SEED = 20260824
MATH_SOURCE = {
    "repo": "EleutherAI/hendrycks_math",
    "revision": "21a5633873b6a120296cce3e2df9d5550074f4a3",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw-dir", type=Path, default=DEFAULT_RAW_DIR)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    return parser.parse_args()


def stable_rank(seed: int, source_id: str) -> str:
    return hashlib.sha256(f"{seed}:{source_id}".encode()).hexdigest()


def select_by_hash(
    records: list[dict[str, Any]], count: int, seed: int
) -> list[dict[str, Any]]:
    if len(records) < count:
        raise ValueError(f"Cannot select {count} records from a group of {len(records)}")
    return sorted(records, key=lambda row: stable_rank(seed, row["id"]))[:count]


def read_parquet(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        raise FileNotFoundError(f"Missing raw data file: {path}")
    return pq.read_table(path).to_pylist()


def extract_boxed_answer(solution: str) -> str:
    marker = r"\boxed"
    answers: list[str] = []
    start = 0
    while True:
        marker_index = solution.find(marker, start)
        if marker_index < 0:
            break
        cursor = marker_index + len(marker)
        while cursor < len(solution) and solution[cursor].isspace():
            cursor += 1
        if cursor < len(solution) and solution[cursor] == "{":
            depth = 0
            for end in range(cursor, len(solution)):
                if solution[end] == "{":
                    depth += 1
                elif solution[end] == "}":
                    depth -= 1
                    if depth == 0:
                        answers.append(solution[cursor + 1 : end].strip())
                        start = end + 1
                        break
            else:
                start = cursor + 1
        else:
            match = re.match(r"([^\s$.,;]+)", solution[cursor:])
            if match:
                answers.append(match.group(1).strip())
            start = cursor + 1
    if not answers:
        raise ValueError("Reference solution has no parseable boxed answer")
    return answers[-1]


def load_math_groups(raw_dir: Path) -> dict[str, list[dict[str, Any]]]:
    root = raw_dir / "math_eleutherai"
    paths = sorted(root.glob("*/test-*.parquet"))
    if len(paths) != 7:
        raise ValueError(f"Expected 7 MATH subject test files, found {len(paths)}")

    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    total = 0
    for path in paths:
        subject_config = path.parent.name
        for index, row in enumerate(read_parquet(path)):
            total += 1
            level = row["level"]
            source_id = f"math:test:{subject_config}:{index:04d}"
            grouped[level].append(
                {
                    "schema_version": "1.0",
                    "id": source_id.replace(":", "-"),
                    "dataset": "math",
                    "problem": row["problem"],
                    "reference_answer": extract_boxed_answer(row["solution"]),
                    "reference_solution": row["solution"],
                    "metadata": {
                        "source_repo": MATH_SOURCE["repo"],
                        "source_revision": MATH_SOURCE["revision"],
                        "source_config": subject_config,
                        "source_split": "test",
                        "source_index": index,
                        "difficulty": level,
                        "subject": row["type"],
                    },
                }
            )
    if total != 5000:
        raise ValueError(f"Expected 5,000 MATH test rows, found {total}")
    expected_levels = [f"Level {level}" for level in range(1, 6)]
    if sorted(grouped) != expected_levels:
        raise ValueError(f"Unexpected MATH difficulty levels: {sorted(grouped)}")
    return grouped


def build_math(raw_dir: Path, seed: int) -> list[dict[str, Any]]:
    grouped = load_math_groups(raw_dir)
    selected: list[dict[str, Any]] = []
    for level in (f"Level {number}" for number in range(1, 6)):
        selected.extend(select_by_hash(grouped[level], 50, seed))
    return sorted(selected, key=lambda row: (row["metadata"]["difficulty"], row["id"]))


def select_math_text_variant(
    grouped: dict[str, list[dict[str, Any]]],
    base_records: list[dict[str, Any]],
    seed: int,
) -> tuple[list[dict[str, Any]], dict[str, dict[str, list[str]]]]:
    """Replace selected Asymptote problems with text-only problems in the same level."""

    base_ids = {row["id"] for row in base_records}
    selected: list[dict[str, Any]] = []
    replacements: dict[str, dict[str, list[str]]] = {}
    for level in (f"Level {number}" for number in range(1, 6)):
        base_level = [row for row in base_records if row["metadata"]["difficulty"] == level]
        excluded = [row for row in base_level if "[asy]" in row["problem"]]
        retained = [row for row in base_level if "[asy]" not in row["problem"]]
        candidates = [
            row
            for row in grouped[level]
            if row["id"] not in base_ids and "[asy]" not in row["problem"]
        ]
        added = select_by_hash(candidates, len(excluded), seed)
        selected.extend(retained + added)
        replacements[level] = {
            "excluded_ids": sorted(row["id"] for row in excluded),
            "replacement_ids": sorted(row["id"] for row in added),
        }

    selected.sort(key=lambda row: (row["metadata"]["difficulty"], row["id"]))
    if len(selected) != len(base_records):
        raise ValueError(f"Expected {len(base_records)} records, found {len(selected)}")
    if any("[asy]" in row["problem"] for row in selected):
        raise ValueError("Text-only MATH variant still contains Asymptote source")
    if len({row["id"] for row in selected}) != len(selected):
        raise ValueError("Text-only MATH variant contains duplicate IDs")
    return selected, replacements


def write_jsonl(path: Path, records: Iterable[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False, separators=(",", ":")) + "\n")


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> None:
    args = parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    grouped = load_math_groups(args.raw_dir)
    math_records: list[dict[str, Any]] = []
    for level in (f"Level {number}" for number in range(1, 6)):
        math_records.extend(select_by_hash(grouped[level], 50, args.seed))
    math_records.sort(key=lambda row: (row["metadata"]["difficulty"], row["id"]))
    math_text, replacements = select_math_text_variant(grouped, math_records, args.seed)

    math_path = args.output_dir / "math.jsonl"
    math_text_path = args.output_dir / "math_text.jsonl"
    write_jsonl(math_path, math_records)
    write_jsonl(math_text_path, math_text)
    levels = dict(sorted(Counter(row["metadata"]["difficulty"] for row in math_records).items()))
    selection_rule = (
        "retain selected records without literal '[asy]'; replace excluded records "
        "within the same level by ascending SHA-256 rank from text-only test records "
        "not present in math.jsonl"
    )
    variant = {
        "base_file": "math.jsonl",
        "selection_rule": selection_rule,
        "records": len(math_text),
        "problem_asymptote_records": sum("[asy]" in row["problem"] for row in math_text),
        "reference_solution_asymptote_records": sum(
            "[asy]" in (row["reference_solution"] or "") for row in math_text
        ),
        "replacement_count": sum(len(item["replacement_ids"]) for item in replacements.values()),
        "levels": levels,
    }
    manifest = {
        "schema_version": "1.1",
        "seed": args.seed,
        "selection_method": "ascending SHA-256 rank of '<seed>:<stable-id>' within each MATH level",
        "source": MATH_SOURCE,
        "counts": {"math": len(math_records), "math_text": len(math_text)},
        "levels": levels,
        "variant": variant,
        "files": {
            "math.jsonl": {"records": len(math_records), "sha256": file_sha256(math_path)},
            "math_text.jsonl": {"records": len(math_text), "sha256": file_sha256(math_text_path)},
        },
    }
    (args.output_dir / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    math_text_manifest = {
        "schema_version": "1.0",
        "variant": "math_text",
        "seed": args.seed,
        "source": MATH_SOURCE,
        "base_file": {"path": "math.jsonl", **manifest["files"]["math.jsonl"]},
        "selection_rule": selection_rule,
        "replacements": replacements,
        "output_file": {"path": "math_text.jsonl", **manifest["files"]["math_text.jsonl"]},
        "levels": levels,
        "problem_asymptote_records": variant["problem_asymptote_records"],
        "reference_solution_asymptote_records": variant[
            "reference_solution_asymptote_records"
        ],
    }
    (args.output_dir / "math_text_manifest.json").write_text(
        json.dumps(math_text_manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(manifest["counts"], ensure_ascii=False))
    print(json.dumps(manifest["levels"], ensure_ascii=False))


if __name__ == "__main__":
    main()
