from __future__ import annotations

import unittest

from scripts.analyze_process_prompt_comparison import paired_direction, percent_change
from scripts.build_process_prompt_comparison import select_records


class ProcessPromptSelectionTests(unittest.TestCase):
    def test_selection_is_deterministic_and_balanced_by_level(self) -> None:
        records = [
            {
                "id": f"sample-{level}-{index}",
                "metadata": {"difficulty": f"Level {level}"},
            }
            for level in range(1, 6)
            for index in range(7)
        ]

        first = select_records(records)
        second = select_records(list(reversed(records)))

        self.assertEqual(
            [row["id"] for row in first],
            [row["id"] for row in second],
        )
        self.assertEqual(len(first), 25)
        self.assertEqual(
            [
                sum(row["metadata"]["difficulty"] == f"Level {level}" for row in first)
                for level in range(1, 6)
            ],
            [5, 5, 5, 5, 5],
        )


class ProcessPromptAnalysisTests(unittest.TestCase):
    def test_paired_direction_and_percent_change(self) -> None:
        self.assertEqual(
            paired_direction([(5, 4), (4, 4), (3, 6)]),
            {"v2_lower": 1, "equal": 1, "v2_higher": 1},
        )
        self.assertEqual(percent_change(200, 150), -25.0)
        self.assertIsNone(percent_change(0, 10))


if __name__ == "__main__":
    unittest.main()
