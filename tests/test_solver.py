from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from typing import Any, Callable

from solver.client import Hy3RequestConfig
from solver.client import Hy3Response
from solver.client import aggregate_stream_chunks
from solver.dataset import SolverSample, load_samples
from solver.parser import parse_solution
from solver.prompt import PROMPT_VERSION_V2, build_messages
from solver.runner import ids_to_skip
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

    def test_v2_requests_process_evaluable_visible_evidence(self) -> None:
        sample = SolverSample(id="id", dataset="math", problem="Solve x+1=3.")
        messages = build_messages(sample, prompt_version=PROMPT_VERSION_V2)
        prompt = messages[0]["content"]

        self.assertIn("one coherent stage", prompt)
        self.assertIn("justify every key intermediate result", prompt)
        self.assertIn("explicitly state and check the relevant condition", prompt)
        self.assertIn("Final Answer: \\boxed{...}", prompt)
        self.assertNotIn("reference_answer", prompt)


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
        self.assertTrue(config.public_dict()["stream"])
        self.assertEqual(
            config.public_dict()["stream_options"],
            {"include_usage": True},
        )


class StreamingClientTests(unittest.TestCase):
    def test_aggregate_stream_chunks_preserves_reasoning_content_and_usage(self) -> None:
        chunks = [
            {
                "id": "chatcmpl-1",
                "object": "chat.completion.chunk",
                "created": 1,
                "model": "hy3",
                "choices": [
                    {
                        "index": 0,
                        "delta": {
                            "role": "assistant",
                            "content": "",
                            "reasoning_content": "internal ",
                        },
                        "finish_reason": None,
                    }
                ],
                "usage": None,
            },
            {
                "id": "chatcmpl-1",
                "object": "chat.completion.chunk",
                "created": 1,
                "model": "hy3",
                "choices": [
                    {
                        "index": 0,
                        "delta": {
                            "content": "Step 1: Compute. ",
                            "reasoning_content": "reasoning",
                        },
                        "finish_reason": None,
                    }
                ],
                "usage": None,
            },
            {
                "id": "chatcmpl-1",
                "object": "chat.completion.chunk",
                "created": 1,
                "model": "hy3",
                "choices": [
                    {
                        "index": 0,
                        "delta": {"content": "Final Answer: 5"},
                        "finish_reason": "stop",
                    }
                ],
                "usage": None,
            },
            {
                "id": "chatcmpl-1",
                "object": "chat.completion.chunk",
                "created": 1,
                "model": "hy3",
                "choices": [],
                "usage": {
                    "prompt_tokens": 10,
                    "completion_tokens": 20,
                    "total_tokens": 30,
                    "completion_tokens_details": {"reasoning_tokens": 8},
                },
            },
        ]

        response = aggregate_stream_chunks(chunks)

        message = response["choices"][0]["message"]
        self.assertEqual(message["reasoning_content"], "internal reasoning")
        self.assertEqual(message["content"], "Step 1: Compute. Final Answer: 5")
        self.assertEqual(response["choices"][0]["finish_reason"], "stop")
        self.assertEqual(response["usage"]["completion_tokens"], 20)
        self.assertEqual(response["stream_chunks"], chunks)

    def test_aggregate_stream_chunks_rejects_incomplete_stream(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "without finish_reason"):
            aggregate_stream_chunks(
                [
                    {
                        "choices": [{"delta": {"content": "partial"}}],
                        "usage": {"completion_tokens": 1},
                    }
                ]
            )


class RunnerTests(unittest.TestCase):
    def test_run_sample_preserves_raw_response_and_parsed_solution(self) -> None:
        class FakeClient:
            config = Hy3RequestConfig(api_key="never-persist-this")

            def solve(
                self,
                messages: list[dict[str, str]],
                *,
                on_chunk: Callable[[int, dict[str, Any]], None] | None = None,
            ) -> Hy3Response:
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
        self.assertEqual(record["request_status"], "success")
        self.assertEqual(record["generation_status"], "complete")
        self.assertEqual(record["parsed"]["final_answer"], "5")
        self.assertEqual(record["response"]["raw"]["id"], "chatcmpl-1")
        self.assertEqual(record["response"]["reasoning_content"], "provider reasoning")
        serialized = json.dumps(record)
        self.assertNotIn("never-persist-this", serialized)
        self.assertNotIn("reference_answer", serialized)

    def test_stream_events_are_persisted_before_final_record(self) -> None:
        class FakeStreamingClient:
            config = Hy3RequestConfig(api_key="never-persist-this")

            def solve(
                self,
                messages: list[dict[str, str]],
                *,
                on_chunk: Callable[[int, dict[str, Any]], None] | None = None,
            ) -> Hy3Response:
                if on_chunk is not None:
                    on_chunk(1, {"choices": [{"delta": {"reasoning_content": "think"}}]})
                    on_chunk(2, {"choices": [{"delta": {"content": "answer"}}]})
                return Hy3Response(
                    status_code=200,
                    headers={},
                    body={
                        "id": "chatcmpl-stream",
                        "model": "hy3",
                        "created": 1,
                        "choices": [
                            {
                                "finish_reason": "length",
                                "message": {
                                    "content": "answer",
                                    "reasoning_content": "think",
                                },
                            }
                        ],
                        "usage": {"completion_tokens": 2},
                    },
                )

        with tempfile.TemporaryDirectory() as directory:
            events_path = Path(directory) / "events.jsonl"
            record = run_sample(
                sample=SolverSample(id="id", dataset="test", problem="Problem"),
                client=FakeStreamingClient(),  # type: ignore[arg-type]
                run_id="run-1",
                max_retries=0,
                stream_events_path=events_path,
            )
            events = [json.loads(line) for line in events_path.read_text().splitlines()]

        self.assertEqual(record["request_status"], "success")
        self.assertEqual(record["generation_status"], "incomplete")
        self.assertEqual(
            [event["event"] for event in events],
            ["stream_started", "stream_chunk", "stream_chunk", "stream_incomplete"],
        )
        self.assertEqual(events[1]["sequence"], 1)
        self.assertEqual(events[-1]["generation_status"], "incomplete")
        self.assertEqual(events[-1]["finish_reason"], "length")


class ResumeTests(unittest.TestCase):
    def test_incomplete_success_is_skipped_unless_explicitly_retried(self) -> None:
        records = [
            {
                "status": "success",
                "sample": {"id": "incomplete"},
                "response": {"finish_reason": "length"},
            },
            {
                "request_status": "success",
                "generation_status": "complete",
                "sample": {"id": "complete"},
                "response": {"finish_reason": "stop"},
            },
            {
                "request_status": "error",
                "generation_status": "unknown",
                "sample": {"id": "error"},
                "response": None,
            },
        ]
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "records.jsonl"
            path.write_text(
                "".join(json.dumps(record) + "\n" for record in records),
                encoding="utf-8",
            )
            default_skip = ids_to_skip(path)
            retry_incomplete_skip = ids_to_skip(path, retry_incomplete=True)

        self.assertEqual(default_skip, {"complete", "incomplete"})
        self.assertEqual(retry_incomplete_skip, {"complete"})


if __name__ == "__main__":
    unittest.main()
