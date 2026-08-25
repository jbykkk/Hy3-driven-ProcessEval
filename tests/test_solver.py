from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from solver.client import Hy3RequestConfig
from solver.client import Hy3Response
from solver.dataset import SolverSample, load_samples
from solver.parser import parse_solution
from solver.prompt import build_messages
from solver.runner import run_sample


class DatasetLoaderTests(unittest.TestCase):
    def test_loader_exposes_only_model_visible_fields(self) -> None:
        row = {
            "id": "sample-1",
            "dataset": "test",
            "problem": "What is 1 + 1?",
            "reference_answer": "2",
            "reference_solution": "secret solution",
            "metadata": {"difficulty": "secret metadata"},
        }
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "benchmark.jsonl"
            path.write_text(json.dumps(row) + "\n", encoding="utf-8")
            sample = next(load_samples(path))

        self.assertEqual(
            sample.as_dict(),
            {"id": "sample-1", "dataset": "test", "problem": "What is 1 + 1?"},
        )
        self.assertNotIn("2", json.dumps(sample.as_dict()))
        self.assertNotIn("secret", json.dumps(sample.as_dict()))


class PromptTests(unittest.TestCase):
    def test_prompt_contains_problem_and_numbered_step_instruction(self) -> None:
        sample = SolverSample(id="id", dataset="gsm8k", problem="Compute 2 + 3.")
        messages = build_messages(sample)
        self.assertEqual(len(messages), 1)
        self.assertEqual(messages[0]["role"], "user")
        self.assertIn("Compute 2 + 3.", messages[0]["content"])
        self.assertIn("Step 1, Step 2, Step 3", messages[0]["content"])


class ParserTests(unittest.TestCase):
    def test_parser_extracts_steps_and_nested_boxed_answer(self) -> None:
        content = (
            "Step 1: Set up the equation.\n"
            "Step 2: Simplify it.\n"
            "Final Answer: $\\boxed{\\frac{1}{2}}$"
        )
        parsed = parse_solution(content)
        self.assertEqual([step.number for step in parsed.steps], [1, 2])
        self.assertEqual(parsed.final_answer, r"\frac{1}{2}")
        self.assertEqual(parsed.warnings, [])

    def test_parser_extracts_number_from_natural_language_answer(self) -> None:
        content = (
            "Step 1: Compute the distance.\n"
            "**Answer:** The final distance is **45 miles away from home**."
        )
        parsed = parse_solution(content)
        self.assertEqual(parsed.final_answer, "45")

    def test_parser_extracts_concluding_currency_without_answer_label(self) -> None:
        content = (
            "Step 1: Add the two totals.\n"
            "Therefore, the total amount paid is **\\$1,596**."
        )
        parsed = parse_solution(content)
        self.assertEqual(parsed.final_answer, "1596")

    def test_parser_prefers_primary_answer_before_alternative_units(self) -> None:
        content = (
            "Step 1: Compute the distance.\n"
            "**Answer:** The distance is **180,000 meters** (or **180 km**)."
        )
        parsed = parse_solution(content)
        self.assertEqual(parsed.final_answer, "180000")

    def test_parser_extracts_last_parenthesized_math_alternative(self) -> None:
        content = (
            "Step 1: Simplify the fraction.\n"
            "Final Answer: \\(\\frac{28}{56} = \\frac{1}{2}\\) (or \\(0.5\\))."
        )
        parsed = parse_solution(content)
        self.assertEqual(parsed.final_answer, "0.5")

    def test_parser_prefers_answer_stated_in_last_numbered_step(self) -> None:
        content = (
            "Step 1: Compute part of the result. Thus, this part is **40**.\n"
            "Step 2: Add the remaining amount. 20 + 40 = 60.\n"
            "Step 3: State the final answer.\n"
            "The total is **60 instructions**."
        )
        parsed = parse_solution(content)
        self.assertEqual(parsed.final_answer, "60")

    def test_parser_reads_unbolded_percent_from_final_step(self) -> None:
        content = (
            "Step 1: Compute the fraction.\n"
            "Step 2: State the final answer.\n"
            "40% of the spools are blue."
        )
        parsed = parse_solution(content)
        self.assertEqual(parsed.final_answer, "40")

    def test_parser_reads_bold_maximum_from_last_step(self) -> None:
        content = (
            "Step 1: Derive the area formula.\n"
            "Step 2: State the maximum area.\n"
            "The maximum area is **2500 square feet**."
        )
        parsed = parse_solution(content)
        self.assertEqual(parsed.final_answer, "2500")


class ConfigTests(unittest.TestCase):
    def test_public_config_never_contains_api_key(self) -> None:
        config = Hy3RequestConfig(api_key="do-not-persist")
        serialized = json.dumps(config.public_dict())
        self.assertNotIn("do-not-persist", serialized)
        self.assertNotIn("api_key", serialized)


class RunnerTests(unittest.TestCase):
    def test_run_sample_preserves_raw_response_and_parsed_solution(self) -> None:
        class FakeClient:
            config = Hy3RequestConfig(api_key="never-persist-this")

            def solve(self, messages: list[dict[str, str]]) -> Hy3Response:
                self.messages = messages
                return Hy3Response(
                    status_code=200,
                    headers={"x-request-id": "request-1"},
                    body={
                        "id": "chatcmpl-1",
                        "model": "hy3",
                        "created": 1,
                        "choices": [
                            {
                                "finish_reason": "stop",
                                "message": {
                                    "content": (
                                        "Step 1: Add the numbers.\n"
                                        "Final Answer: $\\boxed{5}$"
                                    ),
                                    "reasoning_content": "provider reasoning",
                                },
                            }
                        ],
                        "usage": {"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30},
                    },
                )

        sample = SolverSample(id="id", dataset="test", problem="Compute 2 + 3.")
        client = FakeClient()
        record = run_sample(
            sample=sample,
            client=client,  # type: ignore[arg-type]
            run_id="run-1",
            max_retries=0,
        )

        self.assertEqual(record["status"], "success")
        self.assertEqual(record["parsed"]["final_answer"], "5")
        self.assertEqual(record["response"]["raw"]["id"], "chatcmpl-1")
        self.assertEqual(record["response"]["reasoning_content"], "provider reasoning")
        serialized = json.dumps(record)
        self.assertNotIn("never-persist-this", serialized)
        self.assertNotIn("reference_answer", serialized)


if __name__ == "__main__":
    unittest.main()
