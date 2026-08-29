"""Build a deterministic, subject-diverse Level 4/5 MATH selection."""

from __future__ import annotations

import json
import random
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data" / "benchmark" / "math_text.jsonl"
PREVIOUS_SELECTION = (
    ROOT / "experiments" / "process_evaluator_v1v2_25" / "selection.jsonl"
)
OUTPUT_DIR = ROOT / "experiments" / "process_evaluator_v2_level45_20"
SELECTION = OUTPUT_DIR / "selection.jsonl"
MANIFEST = OUTPUT_DIR / "manifest.json"
SEED = 20260829
LEVELS = ("Level 4", "Level 5")
PER_LEVEL = 10


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            try:
                row = json.loads(line)
                str(row["id"])
            except (json.JSONDecodeError, KeyError, TypeError) as error:
                raise ValueError(f"Invalid JSONL row at {path}:{line_number}") from error
            records.append(row)
    return records


def shuffled(rows: list[dict[str, Any]], *, key: str) -> list[dict[str, Any]]:
    result = sorted(rows, key=lambda row: str(row["id"]))
    random.Random(f"{SEED}:{key}").shuffle(result)
    return result


def select_level(
    records: list[dict[str, Any]], level: str, excluded_ids: set[str]
) -> list[dict[str, Any]]:
    by_subject: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in records:
        metadata = row.get("metadata") or {}
        if row["id"] in excluded_ids or metadata.get("difficulty") != level:
            continue
        by_subject[str(metadata["subject"])].append(row)

    ranked = {
        subject: shuffled(rows, key=f"{level}:{subject}")
        for subject, rows in sorted(by_subject.items())
    }
    selected: list[dict[str, Any]] = []
    round_index = 0
    while len(selected) < PER_LEVEL:
        candidates = [
            rows[round_index]
            for rows in ranked.values()
            if round_index < len(rows)
        ]
        if not candidates:
            raise ValueError(f"Not enough candidates for {level}")
        candidates = shuffled(candidates, key=f"{level}:round:{round_index}")
        selected.extend(candidates[: PER_LEVEL - len(selected)])
        round_index += 1
    return selected


def write_jsonl(path: Path, records: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False, separators=(",", ":")) + "\n")


def main() -> int:
    records = load_jsonl(SOURCE)
    previous_ids = {str(row["id"]) for row in load_jsonl(PREVIOUS_SELECTION)}
    selected = [
        row
        for level in LEVELS
        for row in select_level(records, level, previous_ids)
    ]
    ids = [str(row["id"]) for row in selected]
    if len(ids) != 20 or len(ids) != len(set(ids)):
        raise ValueError("Selection must contain 20 unique records")
    if previous_ids.intersection(ids):
        raise ValueError("Selection overlaps the earlier 25-sample experiment")

    write_jsonl(SELECTION, selected)
    levels: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in selected:
        metadata = row["metadata"]
        levels[str(metadata["difficulty"])].append(
            {"id": str(row["id"]), "subject": str(metadata["subject"])}
        )
    manifest = {
        "schema_version": "1.0",
        "experiment": "process-evaluator-v2-level45-20",
        "seed": SEED,
        "selection_rule": (
            "Exclude the earlier v1/v2 25 samples. For each of Level 4 and Level 5, "
            "shuffle candidates deterministically within each official subject, take one "
            "per available subject before taking a second from any subject, and stop at 10."
        ),
        "source": str(SOURCE.relative_to(ROOT)),
        "excluded_selection": str(PREVIOUS_SELECTION.relative_to(ROOT)),
        "records": len(selected),
        "levels": dict(levels),
        "subjects": dict(
            sorted(Counter(str(row["metadata"]["subject"]) for row in selected).items())
        ),
        "solver_config": {
            "prompt_version": "math-solver-v2",
            "model": "hy3",
            "temperature": 0.9,
            "top_p": 1.0,
            "max_tokens": 32000,
            "thinking": "enabled",
            "reasoning_effort": "high",
            "timeout_seconds": 300,
            "max_retries": 0,
        },
        "selection": str(SELECTION.relative_to(ROOT)),
        "planned_output": "outputs/process_v2_level45_20_solver.jsonl",
    }
    MANIFEST.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
