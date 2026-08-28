"""Build the deterministic 25-sample MATH prompt-comparison selection."""

from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data" / "benchmark" / "math_text.jsonl"
OUTPUT_DIR = ROOT / "experiments" / "process_evaluator_v1v2_25"
SELECTION = OUTPUT_DIR / "selection.jsonl"
MANIFEST = OUTPUT_DIR / "manifest.json"
SEED = 20260828
PER_LEVEL = 5
EXCLUDED_IDS = {"math-test-algebra-0144"}


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def rank(sample_id: str) -> str:
    return hashlib.sha256(f"{SEED}:{sample_id}".encode()).hexdigest()


def load_records(path: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            try:
                row = json.loads(line)
                str(row["id"])
                str(row["metadata"]["difficulty"])
            except (json.JSONDecodeError, KeyError, TypeError) as error:
                raise ValueError(f"Invalid source row at {path}:{line_number}") from error
            records.append(row)
    return records


def select_records(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in records:
        if row["id"] not in EXCLUDED_IDS:
            grouped[str(row["metadata"]["difficulty"])].append(row)

    selected: list[dict[str, Any]] = []
    expected_levels = [f"Level {level}" for level in range(1, 6)]
    for level in expected_levels:
        candidates = sorted(grouped[level], key=lambda row: (rank(str(row["id"])), row["id"]))
        if len(candidates) < PER_LEVEL:
            raise ValueError(f"Not enough candidates for {level}")
        selected.extend(candidates[:PER_LEVEL])

    ids = [str(row["id"]) for row in selected]
    if len(ids) != 25 or len(ids) != len(set(ids)):
        raise ValueError("Selection must contain 25 unique records")
    return selected


def write_jsonl(path: Path, records: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False, separators=(",", ":")) + "\n")


def main() -> int:
    selected = select_records(load_records(SOURCE))
    write_jsonl(SELECTION, selected)
    levels: dict[str, list[str]] = defaultdict(list)
    subjects: dict[str, int] = defaultdict(int)
    for row in selected:
        levels[str(row["metadata"]["difficulty"])].append(str(row["id"]))
        subjects[str(row["metadata"]["subject"])] += 1
    manifest = {
        "schema_version": "1.0",
        "experiment": "process-evaluator-v1v2-25",
        "seed": SEED,
        "selection_rule": (
            "Exclude the earlier single-probe sample, group math_text.jsonl by official "
            "difficulty, rank by SHA-256(seed:id), and take the first five per level."
        ),
        "source": {
            "path": str(SOURCE.relative_to(ROOT)),
            "sha256": sha256_file(SOURCE),
        },
        "excluded_ids": sorted(EXCLUDED_IDS),
        "records": len(selected),
        "levels": dict(levels),
        "subjects": dict(sorted(subjects.items())),
        "selection": {
            "path": str(SELECTION.relative_to(ROOT)),
            "sha256": sha256_file(SELECTION),
        },
    }
    MANIFEST.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(manifest, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
