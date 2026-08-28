from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from typing import Any, Callable

from process_evaluation.aggregator import aggregate_process_evaluation
from process_evaluation.prompt import build_global_messages, build_local_messages
from process_evaluation.runner import (
    EvaluationTarget,
    completed_inference_ids,
    evaluate_target,
    load_targets,
)
from process_evaluation.schema import (
    EvaluatorSchemaError,
    GlobalEvaluationResult,
    LocalStepResult,
    parse_global_result,
    parse_local_result,
)
from process_evaluation.step_parser import ProcessStep, parse_process_steps
from solver.client import Hy3RequestConfig, Hy3Response


class ProcessStepParserTests(unittest.TestCase):
    def test_preserves_step_bodies_and_separates_final_answer(self) -> None:
        content = (
            "Introductory text.\n"
            "**Step 1:** Let $x=2$.\nKeep this exact line.\n"
            "Step 2 [Calculation]: $x+3=5$.\n"
            "Final Answer: $\\boxed{5}$"
        )

        parsed = parse_process_steps(content)

        self.assertEqual(parsed.parse_status, "success")
        self.assertEqual([step.step_id for step in parsed.steps], [1, 2])
        self.assertEqual(parsed.steps[0].text, "Let $x=2$.\nKeep this exact line.")
        self.assertEqual(parsed.steps[1].text, "$x+3=5$.")
        self.assertEqual(parsed.final_answer_text, "$\\boxed{5}$")
        self.assertEqual(parsed.final_answer_source, "explicit_label")
        self.assertEqual(parsed.original_content, content)

    def test_reports_duplicate_non_contiguous_empty_and_missing_answer(self) -> None:
        content = "Step 1:\nStep 1: Repeated.\nStep 3: Continue."

        parsed = parse_process_steps(content)
        codes = [issue.code for issue in parsed.structure_issues]

        self.assertEqual(parsed.parse_status, "issues")
        self.assertIn("empty_step_content", codes)
        self.assertIn("duplicate_step_number", codes)
        self.assertIn("non_contiguous_step_numbers", codes)
        self.assertIn("final_answer_missing", codes)

    def test_reports_no_steps_without_inventing_segmentation(self) -> None:
        content = "Compute directly to obtain $\\boxed{7}$."
        parsed = parse_process_steps(content)

        self.assertEqual(parsed.parse_status, "failed")
        self.assertEqual(parsed.steps, [])
        self.assertEqual(parsed.final_answer_text, r"\boxed{7}")
        self.assertEqual(parsed.final_answer_source, "boxed_expression")
        self.assertEqual(parsed.structure_issues[0].code, "no_numbered_steps")


class EvaluatorSchemaTests(unittest.TestCase):
    def test_parses_strict_local_and_global_json(self) -> None:
        local = parse_local_result(
            json.dumps(
                {
                    "step_id": 2,
                    "status": "invalid",
                    "importance": "high",
                    "purpose": "Add two quantities.",
                    "error_type": "calculation_error",
                    "error_origin": "current_step",
                    "evidence": "The visible equality states 2 + 3 = 6.",
                }
            ),
            expected_step_id=2,
        )
        global_result = parse_global_result(
            json.dumps(
                {
                    "global_status": "invalid",
                    "process_complete": True,
                    "final_answer_supported": False,
                    "global_error_type": "calculation_error",
                    "first_error_step_override": 2,
                    "evidence": "The final value depends on the arithmetic error in Step 2.",
                }
            ),
            allowed_step_ids={1, 2, 3},
        )

        self.assertEqual(local.error_origin, "current_step")
        self.assertEqual(global_result.first_error_step_override, 2)

    def test_rejects_markdown_fences_and_extra_fields(self) -> None:
        fenced = "```json\n{}\n```"
        with self.assertRaises(EvaluatorSchemaError):
            parse_local_result(fenced, expected_step_id=1)

        extra = {
            "step_id": 1,
            "status": "valid",
            "importance": "low",
            "purpose": "Compute.",
            "error_type": None,
            "error_origin": "none",
            "evidence": "The arithmetic is correct.",
            "confidence": 0.9,
        }
        with self.assertRaisesRegex(EvaluatorSchemaError, "extra=.*confidence"):
            parse_local_result(json.dumps(extra), expected_step_id=1)


class ProcessPromptTests(unittest.TestCase):
    def test_prompts_use_visible_evidence_without_answer_correctness(self) -> None:
        steps = [ProcessStep(1, "Set $x=2$."), ProcessStep(2, "Then $x+1=3$.")]
        local_messages = build_local_messages(
            problem="Find x+1 when x=2.",
            previous_steps=steps[:1],
            current_step=steps[1],
        )
        global_messages = build_global_messages(
            problem="Find x+1 when x=2.",
            solution_content="Step 1: Set $x=2$.\nStep 2: Then $x+1=3$.",
            local_results=[
                LocalStepResult(1, "valid", "medium", "Set the value.", None, "none", "Given."),
                LocalStepResult(2, "valid", "high", "Compute.", None, "none", "2+1=3."),
            ],
        )
        serialized = json.dumps(local_messages + global_messages)

        self.assertIn("Find x+1 when x=2.", serialized)
        self.assertIn("previous visible steps", serialized.lower())
        self.assertIn("if and only if", serialized.lower())
        self.assertIn("mere local consistency", serialized.lower())
        self.assertNotIn("answer_correct", serialized)
        self.assertNotIn("reference_solution", serialized)
        self.assertNotIn("reasoning_content", serialized)

    def test_global_prompt_defines_mathematical_final_answer_support(self) -> None:
        messages = build_global_messages(
            problem="Compute 2+3.",
            solution_content="Step 1: 2+3=6.\nFinal Answer: 6",
            local_results=[
                LocalStepResult(
                    1,
                    "invalid",
                    "high",
                    "Add.",
                    "calculation_error",
                    "current_step",
                    "2+3 is 5.",
                )
            ],
        )
        system = messages[0]["content"]

        self.assertIn("mathematically valid", system)
        self.assertIn("provides sufficient information", system)
        self.assertIn("entails the stated final answer", system)


class GlobalSchemaConsistencyTests(unittest.TestCase):
    def test_rejects_supported_answer_from_invalid_process(self) -> None:
        value = {
            "global_status": "invalid",
            "process_complete": True,
            "final_answer_supported": True,
            "global_error_type": "calculation_error",
            "first_error_step_override": 1,
            "evidence": "The answer follows only from an arithmetic error.",
        }

        with self.assertRaisesRegex(
            EvaluatorSchemaError,
            "supported_final_answer_requires_valid_complete_process",
        ):
            parse_global_result(json.dumps(value), allowed_step_ids={1})

    def test_rejects_valid_process_without_supported_final_answer(self) -> None:
        value = {
            "global_status": "valid",
            "process_complete": True,
            "final_answer_supported": False,
            "global_error_type": None,
            "first_error_step_override": None,
            "evidence": "The final answer does not follow from the visible derivation.",
        }

        with self.assertRaisesRegex(
            EvaluatorSchemaError,
            "valid_global_status_requires_complete_supported_process",
        ):
            parse_global_result(json.dumps(value), allowed_step_ids={1})


class AggregatorTests(unittest.TestCase):
    def test_correct_answer_can_have_invalid_process(self) -> None:
        parsed = parse_process_steps(
            "Step 1: $2+3=6$.\nStep 2: State 5 anyway.\nFinal Answer: $\\boxed{5}$"
        )
        local = [
            LocalStepResult(
                1,
                "invalid",
                "high",
                "Add the numbers.",
                "calculation_error",
                "current_step",
                "2+3 is 5, not 6.",
            ),
            LocalStepResult(
                2,
                "invalid",
                "high",
                "State the answer.",
                "invalid_derivation",
                "current_step",
                "The answer does not follow from Step 1.",
            ),
        ]
        global_result = GlobalEvaluationResult(
            "invalid", True, False, "calculation_error", 1, "Step 1 is wrong."
        )

        aggregate = aggregate_process_evaluation(
            step_parse=parsed,
            local_results=local,
            global_result=global_result,
            answer_correct=True,
        )

        self.assertFalse(aggregate["process_correct"])
        self.assertEqual(aggregate["first_error_step"], 1)
        self.assertEqual(
            aggregate["answer_process_relation"],
            "correct_answer_invalid_process",
        )

    def test_inherited_error_is_not_a_new_first_error(self) -> None:
        parsed = parse_process_steps(
            "Step 1: Begin.\nStep 2: $2+3=6$.\nStep 3: $6\\cdot2=12$.\nFinal Answer: 12"
        )
        local = [
            LocalStepResult(1, "valid", "low", "Begin.", None, "none", "No error."),
            LocalStepResult(
                2,
                "invalid",
                "high",
                "Add.",
                "calculation_error",
                "current_step",
                "2+3 is not 6.",
            ),
            LocalStepResult(
                3,
                "valid",
                "high",
                "Multiply inherited value.",
                None,
                "inherited",
                "6 times 2 is 12, but 6 came from the prior error.",
            ),
        ]
        global_result = GlobalEvaluationResult(
            "invalid", True, False, "calculation_error", 2, "Step 2 is the source."
        )

        aggregate = aggregate_process_evaluation(
            step_parse=parsed,
            local_results=local,
            global_result=global_result,
            answer_correct=False,
        )

        self.assertEqual(aggregate["local_first_error_step"], 2)
        self.assertEqual(aggregate["first_error_step"], 2)


class ProcessRunnerTests(unittest.TestCase):
    def test_resume_requires_explicit_retry_for_incomplete_evaluation(self) -> None:
        records = [
            {"inference_id": "complete", "evaluation_status": "complete"},
            {"inference_id": "incomplete", "evaluation_status": "incomplete"},
            {"inference_id": "skipped", "evaluation_status": "skipped"},
        ]
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "process.jsonl"
            path.write_text(
                "".join(json.dumps(record) + "\n" for record in records),
                encoding="utf-8",
            )
            default_skip = completed_inference_ids(path)
            retry_skip = completed_inference_ids(path, retry_incomplete=True)

        self.assertEqual(default_skip, {"complete", "incomplete", "skipped"})
        self.assertEqual(retry_skip, {"complete", "skipped"})

    def test_legacy_stop_record_is_loaded_as_complete(self) -> None:
        legacy = {
            "status": "success",
            "inference_id": "legacy-inference",
            "sample": {"id": "sample", "dataset": "math", "problem": "Problem"},
            "response": {"finish_reason": "stop", "content": "Step 1: Done."},
        }
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "solver.jsonl"
            path.write_text(json.dumps(legacy) + "\n", encoding="utf-8")
            targets = load_targets(path)

        self.assertEqual(targets[0].generation_status, "complete")

    def test_evaluate_target_persists_raw_calls_and_aggregates_separately(self) -> None:
        visible_responses = iter(
            [
                {
                    "step_id": 1,
                    "status": "valid",
                    "importance": "medium",
                    "purpose": "Use the given value.",
                    "error_type": None,
                    "error_origin": "none",
                    "evidence": "The problem gives x=2.",
                },
                {
                    "step_id": 2,
                    "status": "valid",
                    "importance": "high",
                    "purpose": "Add one to x.",
                    "error_type": None,
                    "error_origin": "none",
                    "evidence": "Substituting x=2 gives 2+1=3.",
                },
                {
                    "global_status": "valid",
                    "process_complete": True,
                    "final_answer_supported": True,
                    "global_error_type": None,
                    "first_error_step_override": None,
                    "evidence": "The two visible steps support the stated answer.",
                },
            ]
        )

        class FakeClient:
            config = Hy3RequestConfig(api_key="do-not-persist")

            def complete(
                self,
                messages: list[dict[str, str]],
                *,
                on_chunk: Callable[[int, dict[str, Any]], None] | None = None,
            ) -> Hy3Response:
                if on_chunk:
                    on_chunk(1, {"choices": [{"delta": {"content": "{"}}]})
                content = json.dumps(next(visible_responses))
                return Hy3Response(
                    200,
                    {"x-request-id": "request"},
                    {
                        "id": "response",
                        "model": "hy3",
                        "created": 1,
                        "choices": [
                            {
                                "finish_reason": "stop",
                                "message": {
                                    "content": content,
                                    "reasoning_content": "private evaluator reasoning",
                                },
                            }
                        ],
                        "usage": {"completion_tokens": 10},
                    },
                )

        target = EvaluationTarget(
            inference_id="inference-1",
            sample_id="sample-1",
            dataset="math",
            problem="Find x+1 when x=2.",
            content=(
                "Step 1: Use the given $x=2$.\n"
                "Step 2: Then $x+1=2+1=3$.\n"
                "Final Answer: $\\boxed{3}$"
            ),
            finish_reason="stop",
            generation_status="complete",
        )
        answer_verification = {"verification": {"verdict": "correct"}}

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            raw_path = root / "raw.jsonl"
            events_path = root / "events.jsonl"
            record = evaluate_target(
                target=target,
                answer_verification=answer_verification,
                client=FakeClient(),  # type: ignore[arg-type]
                run_id="run-1",
                raw_output_path=raw_path,
                stream_events_path=events_path,
                max_retries=0,
            )
            raw_calls = [json.loads(line) for line in raw_path.read_text().splitlines()]

        self.assertEqual(record["evaluation_status"], "complete")
        self.assertTrue(record["process_correct"])
        self.assertEqual(record["answer_process_relation"], "correct_answer_valid_process")
        self.assertEqual(len(raw_calls), 3)
        self.assertEqual([call["stage"] for call in raw_calls], ["local_step", "local_step", "global_solution"])
        self.assertNotIn("step_results", raw_calls[0])
        self.assertEqual(
            raw_calls[0]["response"]["reasoning_content"],
            "private evaluator reasoning",
        )
        self.assertNotIn("do-not-persist", json.dumps(raw_calls))

    def test_incomplete_solver_generation_is_skipped_without_api_call(self) -> None:
        class FailIfCalled:
            config = Hy3RequestConfig(api_key="hidden")

            def complete(self, *_: Any, **__: Any) -> Hy3Response:
                raise AssertionError("API must not be called")

        target = EvaluationTarget(
            "inference-2",
            "sample-2",
            "math",
            "Problem",
            "Step 1: Partial text.",
            "length",
            "incomplete",
        )
        with tempfile.TemporaryDirectory() as directory:
            record = evaluate_target(
                target=target,
                answer_verification=None,
                client=FailIfCalled(),  # type: ignore[arg-type]
                run_id="run-1",
                raw_output_path=Path(directory) / "raw.jsonl",
                stream_events_path=None,
                max_retries=0,
            )

        self.assertEqual(record["evaluation_status"], "skipped")
        self.assertIsNone(record["process_correct"])
        self.assertTrue(record["needs_review"])

    def test_schema_failure_keeps_raw_response_and_marks_result_incomplete(self) -> None:
        class InvalidJsonClient:
            config = Hy3RequestConfig(api_key="hidden")

            def complete(
                self,
                messages: list[dict[str, str]],
                *,
                on_chunk: Callable[[int, dict[str, Any]], None] | None = None,
            ) -> Hy3Response:
                return Hy3Response(
                    200,
                    {},
                    {
                        "id": "invalid-json",
                        "model": "hy3",
                        "created": 1,
                        "choices": [
                            {
                                "finish_reason": "stop",
                                "message": {
                                    "content": "```json\n{}\n```",
                                    "reasoning_content": "private",
                                },
                            }
                        ],
                        "usage": {"completion_tokens": 4},
                    },
                )

        target = EvaluationTarget(
            "inference-invalid-json",
            "sample",
            "math",
            "Compute 1+1.",
            "Step 1: $1+1=2$.\nFinal Answer: $\\boxed{2}$",
            "stop",
            "complete",
        )
        with tempfile.TemporaryDirectory() as directory:
            raw_path = Path(directory) / "raw.jsonl"
            record = evaluate_target(
                target=target,
                answer_verification=None,
                client=InvalidJsonClient(),  # type: ignore[arg-type]
                run_id="run",
                raw_output_path=raw_path,
                stream_events_path=None,
                max_retries=0,
            )
            raw = json.loads(raw_path.read_text().splitlines()[0])

        self.assertEqual(record["evaluation_status"], "incomplete")
        self.assertEqual(record["evaluation_errors"][0]["error"], "schema_validation_failed")
        self.assertEqual(raw["response"]["content"], "```json\n{}\n```")
        self.assertNotIn("step_results", raw)


if __name__ == "__main__":
    unittest.main()
