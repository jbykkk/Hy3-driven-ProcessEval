from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from evaluation.runner import evaluate_records


class EvaluationRunnerTests(unittest.TestCase):
    def test_length_response_is_not_scored_even_with_parser_candidate(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            benchmark = root / "benchmark.jsonl"
            output = root / "solver.jsonl"
            benchmark.write_text(
                json.dumps(
                    {
                        "id": "math-example",
                        "dataset": "math",
                        "reference_answer": "20",
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            output.write_text(
                json.dumps(
                    {
                        "status": "success",
                        "inference_id": "inference-1",
                        "sample": {"id": "math-example"},
                        "response": {
                            "finish_reason": "length",
                            "content": "Step 1: Partial calculation.\nAnswer: 21",
                        },
                    }
                )
                + "\n",
                encoding="utf-8",
            )

            records = evaluate_records(
                benchmark_path=benchmark,
                solver_output_path=output,
            )

        self.assertEqual(len(records), 1)
        record = records[0]
        self.assertFalse(record["eligible_for_scoring"])
        self.assertEqual(record["finish_reason"], "length")
        self.assertIsNone(record["prediction"]["value"])
        self.assertEqual(record["prediction"]["parser_candidate"], "21")
        self.assertIn(
            "generation_not_complete:length", record["prediction"]["warnings"]
        )
        self.assertEqual(record["verification"]["verdict"], "unverified")


if __name__ == "__main__":
    unittest.main()
