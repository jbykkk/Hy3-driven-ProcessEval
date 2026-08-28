from __future__ import annotations

import unittest
from typing import Any

from scripts.build_benchmark import select_math_text_variant


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


if __name__ == "__main__":
    unittest.main()
