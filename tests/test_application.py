from __future__ import annotations

import json
import tempfile
import unittest
from collections.abc import Callable
from pathlib import Path
from typing import Any

from application.service import list_benchmark_cases, run_benchmark_case
from solver.client import Hy3RequestConfig, Hy3Response


def response(content: str) -> Hy3Response:
    return Hy3Response(
        status_code=200,
        headers={},
        body={
            "id": "response",
            "model": "hy3",
            "created": 1,
            "choices": [
                {
                    "finish_reason": "stop",
                    "message": {"content": content, "reasoning_content": "private"},
                }
            ],
            "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
        },
    )


class FakeSolverClient:
    config = Hy3RequestConfig(api_key="hidden")

    def solve(
        self,
        messages: list[dict[str, str]],
        *,
        on_chunk: Callable[[int, dict[str, Any]], None] | None = None,
    ) -> Hy3Response:
        return response("Step 1: Compute $2+3=5$.\nFinal Answer: $\\boxed{5}$")


class FakeEvaluatorClient:
    config = Hy3RequestConfig(api_key="hidden", temperature=0.1, max_tokens=8000)

    def __init__(self) -> None:
        self.visible_responses = iter(
            [
                {
                    "step_id": 1,
                    "status": "valid",
                    "importance": "high",
                    "purpose": "Compute the sum.",
                    "error_type": None,
                    "error_origin": "none",
                    "evidence": "Two plus three equals five.",
                },
                {
                    "global_status": "valid",
                    "process_complete": True,
                    "final_answer_supported": True,
                    "global_error_type": None,
                    "first_error_step_override": None,
                    "evidence": "The visible calculation supports the final answer.",
                },
            ]
        )

    def complete(
        self,
        messages: list[dict[str, str]],
        *,
        on_chunk: Callable[[int, dict[str, Any]], None] | None = None,
    ) -> Hy3Response:
        return response(json.dumps(next(self.visible_responses)))


class ApplicationServiceTests(unittest.TestCase):
    def test_runs_full_workflow_and_emits_local_and_global_results(self) -> None:
        benchmark_row = {
            "id": "math-demo",
            "dataset": "math",
            "problem": "Compute 2+3.",
            "reference_answer": "5",
            "metadata": {"difficulty": "Level 2"},
        }
        events: list[dict[str, Any]] = []
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            benchmark = root / "benchmark.jsonl"
            benchmark.write_text(json.dumps(benchmark_row) + "\n", encoding="utf-8")
            result = run_benchmark_case(
                sample_id="math-demo",
                benchmark_path=benchmark,
                output_root=root / "runs",
                solver_client=FakeSolverClient(),  # type: ignore[arg-type]
                evaluator_client=FakeEvaluatorClient(),  # type: ignore[arg-type]
                on_event=events.append,
            )
            run_dir = Path(result["summary"]["run_dir"])
            artifact_names = {path.name for path in run_dir.iterdir()}

        self.assertEqual(result["summary"]["answer"]["verdict"], "correct")
        self.assertTrue(result["summary"]["process"]["process_correct"])
        self.assertIn("local_step", [event["stage"] for event in events])
        self.assertIn("global_solution", [event["stage"] for event in events])
        local_event = next(event for event in events if event["stage"] == "local_step")
        self.assertEqual(local_event["step"]["text"], "Compute $2+3=5$.")
        self.assertIn("summary.json", artifact_names)
        self.assertIn("solver.json", artifact_names)
        self.assertIn("process_evaluation.json", artifact_names)

    def test_lists_cases_by_level(self) -> None:
        rows = [
            {"id": "l2", "problem": "P2", "metadata": {"difficulty": "Level 2"}},
            {"id": "l3", "problem": "P3", "metadata": {"difficulty": "Level 3"}},
        ]
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "benchmark.jsonl"
            path.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")
            cases = list_benchmark_cases(path, level="Level 3", limit=5)

        self.assertEqual([case["id"] for case in cases], ["l3"])
