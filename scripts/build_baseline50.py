"""Build the deterministic, proportionally stratified 50-sample baseline experiment."""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data" / "benchmark" / "benchmark.jsonl"
OUTPUT_DIR = ROOT / "experiments" / "baseline_50"
SELECTION = OUTPUT_DIR / "selection.jsonl"
MANIFEST = OUTPUT_DIR / "manifest.json"
SEED = 20260825
TARGETS = {
    "gsm8k": 13,
    "math:Level 1": 7,
    "math:Level 2": 6,
    "math:Level 3": 6,
    "math:Level 4": 6,
    "math:Level 5": 6,
    "aime:2024": 3,
    "aime:2025": 3,
}


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def stratum(row: dict[str, Any]) -> str:
    dataset = row["dataset"]
    if dataset == "gsm8k":
        return dataset
    if dataset == "math":
        return f"math:{row['metadata']['difficulty']}"
    if dataset == "aime":
        return f"aime:{row['metadata']['year']}"
    raise ValueError(f"Unsupported dataset: {dataset!r}")


def rank(row: dict[str, Any]) -> str:
    material = f"{SEED}:{row['id']}".encode()
    return hashlib.sha256(material).hexdigest()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
    rows = load_jsonl(SOURCE)
    selected: list[dict[str, Any]] = []
    for name, count in TARGETS.items():
        candidates = sorted((row for row in rows if stratum(row) == name), key=rank)
        if len(candidates) < count:
            raise ValueError(f"Stratum {name!r} has only {len(candidates)} samples")
        selected.extend(candidates[:count])

    source_order = {row["id"]: index for index, row in enumerate(rows)}
    selected.sort(key=lambda row: source_order[row["id"]])
    if len(selected) != 50 or len({row["id"] for row in selected}) != 50:
        raise ValueError("Selection must contain 50 unique samples")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    with SELECTION.open("w", encoding="utf-8") as handle:
        for row in selected:
            handle.write(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n")

    manifest = {
        "schema_version": "1.0",
        "experiment": "baseline_50",
        "seed": SEED,
        "source": str(SOURCE.relative_to(ROOT)),
        "selection_method": "ascending SHA-256 rank of '<seed>:<stable-id>' per stratum",
        "targets": TARGETS,
        "counts": dict(Counter(stratum(row) for row in selected)),
        "total": len(selected),
        "selection_sha256": sha256(SELECTION),
        "sample_ids": [row["id"] for row in selected],
    }
    MANIFEST.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
