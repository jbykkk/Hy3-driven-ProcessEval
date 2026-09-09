from __future__ import annotations

import hashlib
import json
import unittest
from pathlib import Path
from typing import Any

from scripts.build_benchmark import select_math_text_variant


ROOT = Path(__file__).resolve().parents[1]


def make_record(identifier: str, level: str, *, asy: bool = False) -> dict[str, Any]:
    return {
        "id": identifier,
        "problem": "Problem [asy] draw(); [/asy]" if asy else "Text-only problem",
        "metadata": {"difficulty": level},
    }


class MathTextSelectionTests(unittest.TestCase):
    def test_replaces_asy_records_with_new_text_records_in_same_level(self) -> None:
        grouped: dict[str, list[dict[str, Any]]] = {}
        base_records: list[dict[str, Any]] = []
        for number in range(1, 6):
            level = f"Level {number}"
            base_level = [
                make_record(f"base-{number}-text", level),
                make_record(f"base-{number}-asy", level, asy=True),
            ]
            base_records.extend(base_level)
            grouped[level] = [
                *base_level,
                make_record(f"candidate-{number}-a", level),
                make_record(f"candidate-{number}-b", level),
            ]

        selected, replacements = select_math_text_variant(grouped, base_records, seed=7)

        self.assertEqual(len(selected), 10)
        self.assertFalse(any("[asy]" in row["problem"] for row in selected))
        self.assertTrue(all(len(entry["excluded_ids"]) == 1 for entry in replacements.values()))
        self.assertTrue(all(len(entry["replacement_ids"]) == 1 for entry in replacements.values()))
        selected_ids = {row["id"] for row in selected}
        self.assertTrue(all(f"base-{number}-text" in selected_ids for number in range(1, 6)))
        self.assertTrue(all(f"base-{number}-asy" not in selected_ids for number in range(1, 6)))


class BenchmarkArtifactsTests(unittest.TestCase):
    def test_committed_math_files_match_manifest(self) -> None:
        benchmark_dir = ROOT / "data" / "benchmark"
        manifest = json.loads((benchmark_dir / "manifest.json").read_text())

        self.assertEqual(set(manifest["files"]), {"math.jsonl", "math_text.jsonl"})
        for filename, expected in manifest["files"].items():
            path = benchmark_dir / filename
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            with path.open(encoding="utf-8") as handle:
                records = sum(1 for line in handle if line.strip())
            self.assertEqual(digest, expected["sha256"])
            self.assertEqual(records, expected["records"])


if __name__ == "__main__":
    unittest.main()
