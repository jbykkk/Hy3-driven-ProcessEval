from __future__ import annotations

import unittest
from collections import Counter

from scripts.build_process_evaluator_level45_20 import select_level


class Level45SelectionTests(unittest.TestCase):
    def test_selection_is_deterministic_diverse_and_excludes_old_ids(self) -> None:
        records = [
            {
                "id": f"sample-{subject}-{index}",
                "metadata": {"difficulty": "Level 4", "subject": subject},
            }
            for subject in ("Algebra", "Geometry", "Number Theory", "Precalculus")
            for index in range(5)
        ]
        excluded = {"sample-Algebra-0", "sample-Geometry-0"}

        first = select_level(records, "Level 4", excluded)
        second = select_level(list(reversed(records)), "Level 4", excluded)

        self.assertEqual([row["id"] for row in first], [row["id"] for row in second])
        self.assertEqual(len(first), 10)
        self.assertFalse(excluded.intersection(row["id"] for row in first))
        counts = Counter(row["metadata"]["subject"] for row in first)
        self.assertEqual(set(counts), {"Algebra", "Geometry", "Number Theory", "Precalculus"})
        self.assertLessEqual(max(counts.values()) - min(counts.values()), 1)


if __name__ == "__main__":
    unittest.main()
