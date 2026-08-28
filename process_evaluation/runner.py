"""Run the independent Hy3 Process Evaluator over visible solver solutions."""

from __future__ import annotations

import argparse
import json
import sys
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Iterator

from dotenv import load_dotenv

from process_evaluation.aggregator import aggregate_process_evaluation
from process_evaluation.prompt import (
    GLOBAL_PROMPT_VERSION,
    LOCAL_PROMPT_VERSION,
    build_global_messages,
    build_local_messages,
)
from process_evaluation.schema import (
    EvaluatorSchemaError,
    GlobalEvaluationResult,
    LocalStepResult,
    parse_global_result,
    parse_local_result,
)
from process_evaluation.step_parser import StepParseResult, parse_process_steps
from solver.client import Hy3Client, Hy3RequestConfig, Hy3Response
from solver.runner import append_record, default_stream_events_path, response_fields


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = ROOT / "outputs" / "solver_outputs.jsonl"
DEFAULT_ANSWER_VERIFICATION = ROOT / "outputs" / "answer_verification.jsonl"
DEFAULT_OUTPUT = ROOT / "outputs" / "process_evaluations.jsonl"
DEFAULT_RAW_OUTPUT = ROOT / "outputs" / "process_evaluator_responses.jsonl"
PROCESS_RECORD_SCHEMA_VERSION = "1.0"
RAW_CALL_SCHEMA_VERSION = "1.0"


@dataclass(frozen=True)
class EvaluationTarget:
    inference_id: str
    sample_id: str
    dataset: str
    problem: str
    content: str
    finish_reason: str
    generation_status: str


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--answer-verification", type=Path, default=DEFAULT_ANSWER_VERIFICATION)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--raw-output", type=Path, default=DEFAULT_RAW_OUTPUT)
    parser.add_argument("--stream-events-output", type=Path)
    parser.add_argument("--id", action="append", dest="sample_ids")
    parser.add_argument("--inference-id", action="append", dest="inference_ids")
    parser.add_argument("--limit", type=int, default=1)
    parser.add_argument("--all", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--no-resume", action="store_true")
    parser.add_argument("--retry-incomplete", action="store_true")
    parser.add_argument("--max-retries", type=int, default=0)
    parser.add_argument("--temperature", type=float, default=0.1)
    parser.add_argument("--top-p", type=float, default=1.0)
    parser.add_argument("--max-tokens", type=int, default=8000)
    parser.add_argument("--thinking", choices=("enabled", "disabled"), default="enabled")
    parser.add_argument("--reasoning-effort", choices=("low", "high", "max"), default="high")
    parser.add_argument("--timeout", type=float, default=300.0)
    args = parser.parse_args()
    if not args.all and args.limit < 1:
        parser.error("--limit must be positive")
    if args.max_retries < 0:
        parser.error("--max-retries cannot be negative")
    if args.no_resume and args.retry_incomplete:
        parser.error("--no-resume and --retry-incomplete cannot be combined")
    return args


def load_jsonl(path: Path) -> Iterator[tuple[int, dict[str, Any]]]:
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            try:
                value = json.loads(line)
            except json.JSONDecodeError as error:
                raise ValueError(f"Invalid JSONL at {path}:{line_number}") from error
            if not isinstance(value, dict):
                raise ValueError(f"JSONL object required at {path}:{line_number}")
            yield line_number, value


def completed_inference_ids(path: Path, *, retry_incomplete: bool = False) -> set[str]:
    if not path.is_file():
        return set()
    skipped: set[str] = set()
    for line_number, record in load_jsonl(path):
        inference_id = record.get("inference_id")
        status = record.get("evaluation_status")
        if not isinstance(inference_id, str) or not inference_id:
            raise ValueError(f"Invalid process record at {path}:{line_number}")
        if status in {"complete", "skipped"} or not retry_incomplete:
            skipped.add(inference_id)
    return skipped


def load_targets(
    path: Path,
    *,
    sample_ids: set[str] | None = None,
    inference_ids: set[str] | None = None,
) -> list[EvaluationTarget]:
    targets: list[EvaluationTarget] = []
    seen: set[str] = set()
    for line_number, record in load_jsonl(path):
        if record.get("status") != "success":
            continue
        try:
            inference_id = str(record["inference_id"])
            sample = record["sample"]
            response = record["response"]
            sample_id = str(sample["id"])
            finish_reason = str(response["finish_reason"])
            generation_status = record.get("generation_status")
            if not generation_status:
                generation_status = "complete" if finish_reason == "stop" else "incomplete"
            target = EvaluationTarget(
                inference_id=inference_id,
                sample_id=sample_id,
                dataset=str(sample["dataset"]),
                problem=str(sample["problem"]),
                content=str(response["content"]),
                finish_reason=finish_reason,
                generation_status=str(generation_status),
            )
        except (KeyError, TypeError) as error:
            raise ValueError(f"Invalid solver record at {path}:{line_number}") from error
        if inference_id in seen:
            raise ValueError(f"Duplicate inference ID {inference_id!r} at {path}:{line_number}")
        seen.add(inference_id)
        if sample_ids and sample_id not in sample_ids:
            continue
        if inference_ids and inference_id not in inference_ids:
            continue
        targets.append(target)
    return targets


def load_answer_verifications(path: Path) -> dict[str, dict[str, Any]]:
    if not path.is_file():
        return {}
    results: dict[str, dict[str, Any]] = {}
    for line_number, record in load_jsonl(path):
        inference_id = record.get("inference_id")
        if not isinstance(inference_id, str) or not inference_id:
            raise ValueError(f"Invalid answer verification at {path}:{line_number}")
        if inference_id in results:
            raise ValueError(f"Duplicate answer verification for {inference_id!r}")
        results[inference_id] = record
    return results


def answer_correct_from(record: dict[str, Any] | None) -> bool | None:
    if record is None:
        return None
    verdict = (record.get("verification") or {}).get("verdict")
    if verdict == "correct":
        return True
    if verdict == "incorrect":
        return False
    return None


def _raw_call_common(
    *,
    evaluator_call_id: str,
    run_id: str,
    target: EvaluationTarget,
    stage: str,
    prompt_version: str,
    messages: list[dict[str, str]],
    client: Hy3Client,
    step_id: int | None,
    started_at: str,
    elapsed_ms: float,
    errors: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "schema_version": RAW_CALL_SCHEMA_VERSION,
        "task_type": "process_evaluation",
        "stage": stage,
        "prompt_version": prompt_version,
        "run_id": run_id,
        "evaluator_call_id": evaluator_call_id,
        "inference_id": target.inference_id,
        "sample_id": target.sample_id,
        "step_id": step_id,
        "prompt": {"messages": messages},
        "request": client.config.public_dict(),
        "timing": {
            "started_at": started_at,
            "finished_at": utc_now(),
            "latency_ms": elapsed_ms,
        },
        "attempt_count": len(errors),
        "attempt_errors": errors,
    }


def run_evaluator_call(
    *,
    client: Hy3Client,
    messages: list[dict[str, str]],
    target: EvaluationTarget,
    run_id: str,
    stage: str,
    prompt_version: str,
    raw_output_path: Path,
    stream_events_path: Path | None,
    max_retries: int,
    step_id: int | None = None,
) -> dict[str, Any]:
    """Run one evaluator request and persist its raw response before parsing it."""

    evaluator_call_id = str(uuid.uuid4())
    started_at = utc_now()
    start = time.perf_counter()
    errors: list[dict[str, Any]] = []
    response: Hy3Response | None = None
    attempts = 0

    for attempt in range(1, max_retries + 2):
        attempts = attempt
        event_base = {
            "schema_version": "1.0",
            "task_type": "process_evaluation",
            "stage": stage,
            "prompt_version": prompt_version,
            "run_id": run_id,
            "evaluator_call_id": evaluator_call_id,
            "inference_id": target.inference_id,
            "sample_id": target.sample_id,
            "step_id": step_id,
            "attempt": attempt,
        }
        if stream_events_path is not None:
            append_record(
                stream_events_path,
                {**event_base, "event": "stream_started", "recorded_at": utc_now()},
            )

        def persist_chunk(sequence: int, chunk: dict[str, Any]) -> None:
            if stream_events_path is not None:
                append_record(
                    stream_events_path,
                    {
                        **event_base,
                        "event": "stream_chunk",
                        "recorded_at": utc_now(),
                        "sequence": sequence,
                        "chunk": chunk,
                    },
                )

        try:
            response = client.complete(messages, on_chunk=persist_chunk)
            fields = response_fields(response)
            generation_status = (
                "complete" if fields["finish_reason"] == "stop" else "incomplete"
            )
            if stream_events_path is not None:
                append_record(
                    stream_events_path,
                    {
                        **event_base,
                        "event": (
                            "stream_completed"
                            if generation_status == "complete"
                            else "stream_incomplete"
                        ),
                        "recorded_at": utc_now(),
                        "generation_status": generation_status,
                        "finish_reason": fields["finish_reason"],
                        "usage": fields["usage"],
                    },
                )
            break
        except Exception as error:
            error_record = {
                "attempt": attempt,
                "type": type(error).__name__,
                "message": str(error),
            }
            errors.append(error_record)
            if stream_events_path is not None:
                append_record(
                    stream_events_path,
                    {
                        **event_base,
                        "event": "stream_interrupted",
                        "recorded_at": utc_now(),
                        "error_type": error_record["type"],
                        "error_message": error_record["message"],
                    },
                )
            if attempt <= max_retries:
                time.sleep(min(2 ** (attempt - 1), 4))

    elapsed_ms = round((time.perf_counter() - start) * 1000, 3)
    common = _raw_call_common(
        evaluator_call_id=evaluator_call_id,
        run_id=run_id,
        target=target,
        stage=stage,
        prompt_version=prompt_version,
        messages=messages,
        client=client,
        step_id=step_id,
        started_at=started_at,
        elapsed_ms=elapsed_ms,
        errors=errors,
    )
    common["attempt_count"] = attempts
    if response is None:
        record = {
            **common,
            "request_status": "error",
            "generation_status": "unknown",
            "response": None,
        }
    else:
        fields = response_fields(response)
        record = {
            **common,
            "request_status": "success",
            "generation_status": (
                "complete" if fields["finish_reason"] == "stop" else "incomplete"
            ),
            "response": fields,
        }
    append_record(raw_output_path, record)
    return record


def _call_content_or_error(
    record: dict[str, Any],
    *,
    stage: str,
    step_id: int | None,
) -> tuple[str | None, dict[str, Any] | None]:
    if record["request_status"] != "success":
        return None, {
            "stage": stage,
            "step_id": step_id,
            "error": "request_failed",
            "evaluator_call_id": record["evaluator_call_id"],
        }
    if record["generation_status"] != "complete":
        return None, {
            "stage": stage,
            "step_id": step_id,
            "error": "generation_incomplete",
            "finish_reason": record["response"].get("finish_reason"),
            "evaluator_call_id": record["evaluator_call_id"],
        }
    content = record["response"].get("content") or ""
    if not content.strip():
        return None, {
            "stage": stage,
            "step_id": step_id,
            "error": "empty_visible_evaluator_response",
            "evaluator_call_id": record["evaluator_call_id"],
        }
    return str(content), None


def _base_process_record(
    *,
    target: EvaluationTarget,
    run_id: str,
    step_parse: StepParseResult,
    answer_verification: dict[str, Any] | None,
) -> dict[str, Any]:
    verdict = (
        (answer_verification.get("verification") or {}).get("verdict")
        if answer_verification
        else None
    )
    return {
        "schema_version": PROCESS_RECORD_SCHEMA_VERSION,
        "task_type": "process_evaluation",
        "run_id": run_id,
        "evaluated_at": utc_now(),
        "sample_id": target.sample_id,
        "inference_id": target.inference_id,
        "dataset": target.dataset,
        "solver_generation": {
            "finish_reason": target.finish_reason,
            "generation_status": target.generation_status,
        },
        "answer_correct": answer_correct_from(answer_verification),
        "answer_verification": {
            "available": answer_verification is not None,
            "verdict": verdict,
        },
        "step_parse_status": step_parse.parse_status,
        "step_parse": step_parse.as_dict(),
        "versions": {
            "local_prompt": LOCAL_PROMPT_VERSION,
            "global_prompt": GLOBAL_PROMPT_VERSION,
        },
    }


def evaluate_target(
    *,
    target: EvaluationTarget,
    answer_verification: dict[str, Any] | None,
    client: Hy3Client,
    run_id: str,
    raw_output_path: Path,
    stream_events_path: Path | None,
    max_retries: int,
) -> dict[str, Any]:
    step_parse = parse_process_steps(target.content)
    base = _base_process_record(
        target=target,
        run_id=run_id,
        step_parse=step_parse,
        answer_verification=answer_verification,
    )
    answer_correct = answer_correct_from(answer_verification)

    if target.finish_reason != "stop" or target.generation_status != "complete":
        aggregate = aggregate_process_evaluation(
            step_parse=step_parse,
            local_results=[],
            global_result=None,
            answer_correct=answer_correct,
            evaluation_errors=[{"stage": "input", "error": "solver_generation_incomplete"}],
        )
        return {
            **base,
            "evaluation_status": "skipped",
            "skip_reason": "solver_generation_incomplete",
            "step_results": [],
            "global_result": None,
            "evaluation_errors": [{"stage": "input", "error": "solver_generation_incomplete"}],
            **aggregate,
        }

    issue_codes = {issue.code for issue in step_parse.structure_issues}
    if step_parse.parse_status == "failed" or "duplicate_step_number" in issue_codes:
        errors = [{"stage": "step_parser", "error": "structure_not_evaluable"}]
        aggregate = aggregate_process_evaluation(
            step_parse=step_parse,
            local_results=[],
            global_result=None,
            answer_correct=answer_correct,
            evaluation_errors=errors,
        )
        return {
            **base,
            "evaluation_status": "skipped",
            "skip_reason": "step_structure_not_evaluable",
            "step_results": [],
            "global_result": None,
            "evaluation_errors": errors,
            **aggregate,
        }

    local_results: list[LocalStepResult] = []
    errors: list[dict[str, Any]] = []
    for index, step in enumerate(step_parse.steps):
        messages = build_local_messages(
            problem=target.problem,
            previous_steps=step_parse.steps[:index],
            current_step=step,
        )
        raw = run_evaluator_call(
            client=client,
            messages=messages,
            target=target,
            run_id=run_id,
            stage="local_step",
            prompt_version=LOCAL_PROMPT_VERSION,
            raw_output_path=raw_output_path,
            stream_events_path=stream_events_path,
            max_retries=max_retries,
            step_id=step.step_id,
        )
        content, call_error = _call_content_or_error(
            raw, stage="local_step", step_id=step.step_id
        )
        if call_error is not None:
            errors.append(call_error)
            break
        try:
            local_results.append(
                parse_local_result(content or "", expected_step_id=step.step_id)
            )
        except EvaluatorSchemaError as error:
            errors.append(
                {
                    "stage": "local_step",
                    "step_id": step.step_id,
                    "error": "schema_validation_failed",
                    "detail": str(error),
                    "evaluator_call_id": raw["evaluator_call_id"],
                }
            )
            break

    global_result: GlobalEvaluationResult | None = None
    if not errors and len(local_results) == len(step_parse.steps):
        messages = build_global_messages(
            problem=target.problem,
            solution_content=target.content,
            local_results=local_results,
        )
        raw = run_evaluator_call(
            client=client,
            messages=messages,
            target=target,
            run_id=run_id,
            stage="global_solution",
            prompt_version=GLOBAL_PROMPT_VERSION,
            raw_output_path=raw_output_path,
            stream_events_path=stream_events_path,
            max_retries=max_retries,
        )
        content, call_error = _call_content_or_error(
            raw, stage="global_solution", step_id=None
        )
        if call_error is not None:
            errors.append(call_error)
        else:
            try:
                global_result = parse_global_result(
                    content or "",
                    allowed_step_ids={step.step_id for step in step_parse.steps},
                )
            except EvaluatorSchemaError as error:
                errors.append(
                    {
                        "stage": "global_solution",
                        "step_id": None,
                        "error": "schema_validation_failed",
                        "detail": str(error),
                        "evaluator_call_id": raw["evaluator_call_id"],
                    }
                )

    aggregate = aggregate_process_evaluation(
        step_parse=step_parse,
        local_results=local_results,
        global_result=global_result,
        answer_correct=answer_correct,
        evaluation_errors=errors,
    )
    return {
        **base,
        "evaluation_status": "complete" if not errors and global_result else "incomplete",
        "skip_reason": None,
        "step_results": [result.as_dict() for result in local_results],
        "global_result": global_result.as_dict() if global_result else None,
        "evaluation_errors": errors,
        **(global_result.as_dict() if global_result else {
            "global_status": None,
            "process_complete": None,
            "final_answer_supported": None,
            "global_error_type": None,
            "first_error_step_override": None,
        }),
        **aggregate,
    }


def print_dry_run(targets: list[EvaluationTarget]) -> None:
    for target in targets:
        parsed = parse_process_steps(target.content)
        local_prompts = [
            {
                "step_id": step.step_id,
                "prompt_version": LOCAL_PROMPT_VERSION,
                "messages": build_local_messages(
                    problem=target.problem,
                    previous_steps=parsed.steps[:index],
                    current_step=step,
                ),
            }
            for index, step in enumerate(parsed.steps)
        ]
        print(
            json.dumps(
                {
                    "inference_id": target.inference_id,
                    "sample_id": target.sample_id,
                    "step_parse": parsed.as_dict(),
                    "local_prompts": local_prompts,
                    "global_prompt_version": GLOBAL_PROMPT_VERSION,
                    "global_prompt_note": "Built only after all validated local results exist.",
                },
                ensure_ascii=False,
                indent=2,
            )
        )


def select_targets(args: argparse.Namespace) -> list[EvaluationTarget]:
    targets = load_targets(
        args.input,
        sample_ids=set(args.sample_ids) if args.sample_ids else None,
        inference_ids=set(args.inference_ids) if args.inference_ids else None,
    )
    if args.sample_ids:
        found = {target.sample_id for target in targets}
        missing = set(args.sample_ids) - found
        if missing:
            raise ValueError(f"Unknown sample IDs: {sorted(missing)}")
    if args.inference_ids:
        found = {target.inference_id for target in targets}
        missing = set(args.inference_ids) - found
        if missing:
            raise ValueError(f"Unknown inference IDs: {sorted(missing)}")
    if not args.no_resume and not args.dry_run:
        skipped = completed_inference_ids(
            args.output,
            retry_incomplete=args.retry_incomplete,
        )
        targets = [target for target in targets if target.inference_id not in skipped]
    return targets if args.all else targets[: args.limit]


def main() -> int:
    args = parse_args()
    try:
        targets = select_targets(args)
        if not targets:
            print("No pending solver inferences selected.")
            return 0
        if args.dry_run:
            print_dry_run(targets)
            return 0

        load_dotenv(ROOT / ".env", override=False)
        config = Hy3RequestConfig.from_env(
            temperature=args.temperature,
            top_p=args.top_p,
            max_tokens=args.max_tokens,
            thinking=args.thinking,
            reasoning_effort=args.reasoning_effort,
            timeout_seconds=args.timeout,
        )
        client = Hy3Client(config)
        answer_verifications = load_answer_verifications(args.answer_verification)
        run_id = str(uuid.uuid4())
        stream_events_path = args.stream_events_output or default_stream_events_path(
            args.raw_output
        )
        incomplete = 0
        for index, target in enumerate(targets, start=1):
            print(
                f"[{index}/{len(targets)}] Evaluating {target.sample_id} "
                f"({target.inference_id})...",
                flush=True,
            )
            record = evaluate_target(
                target=target,
                answer_verification=answer_verifications.get(target.inference_id),
                client=client,
                run_id=run_id,
                raw_output_path=args.raw_output,
                stream_events_path=stream_events_path,
                max_retries=args.max_retries,
            )
            append_record(args.output, record)
            print(
                "  "
                f"evaluation_status={record['evaluation_status']}; "
                f"process_correct={record['process_correct']}; "
                f"needs_review={record['needs_review']}"
            )
            if record["evaluation_status"] == "incomplete":
                incomplete += 1
        return 1 if incomplete else 0
    except (OSError, RuntimeError, ValueError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
