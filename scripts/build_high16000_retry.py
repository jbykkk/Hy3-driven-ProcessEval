"""Build the retry set from all baseline_50 generation truncations."""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
EXPERIMENT_DIR = ROOT / "experiments" / "baseline_50"
ISSUES = EXPERIMENT_DIR / "issues.jsonl"
SELECTION = EXPERIMENT_DIR / "high_16000_selection.jsonl"
MANIFEST = EXPERIMENT_DIR / "high_16000_manifest.json"


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    issues = load_jsonl(ISSUES)
    truncations = [
        issue for issue in issues if "generation_truncated" in issue["issue_types"]
    ]
    if len(truncations) != 23:
        raise ValueError(f"Expected 23 truncations, found {len(truncations)}")

    records = [issue["benchmark_record"] for issue in truncations]
    if len({record["id"] for record in records}) != 23:
        raise ValueError("Retry selection contains duplicate sample IDs")
    with SELECTION.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False, separators=(",", ":")) + "\n")

    parent_inferences = {
        issue["sample_id"]: issue["inference"]["inference_id"] for issue in truncations
    }
    dataset_counts = Counter(record["dataset"] for record in records)
    manifest = {
        "schema_version": "1.0",
        "experiment": "baseline_50_high_16000_retry",
        "source_issues": str(ISSUES.relative_to(ROOT)),
        "selection_rule": "all baseline_50 records with generation_truncated",
        "controlled_change": {"max_tokens": {"from": 4096, "to": 16000}},
        "unchanged": {
            "model": "hy3",
            "temperature": 0.9,
            "top_p": 1.0,
            "thinking": {"type": "enabled"},
            "reasoning_effort": "high",
            "prompt_version": "math-solver-v1",
            "stream": False,
        },
        "counts": dict(dataset_counts),
        "total": len(records),
        "selection_sha256": sha256(SELECTION),
        "parent_inference_ids": parent_inferences,
        "sample_ids": [record["id"] for record in records],
    }
    MANIFEST.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
