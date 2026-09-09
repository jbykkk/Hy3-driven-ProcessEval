"""Orchestrate Solver, answer verification, and process evaluation for one case."""

from __future__ import annotations

import json
import uuid
from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from evaluation.answer_verifier import verify_answer
from process_evaluation.runner import EvaluationTarget, evaluate_target
from solver.client import Hy3Client, Hy3RequestConfig
from solver.dataset import SolverSample
from solver.prompt import PROMPT_VERSION
from solver.runner import run_sample


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BENCHMARK = ROOT / "data" / "benchmark" / "math_text.jsonl"
DEFAULT_OUTPUT_ROOT = ROOT / "outputs" / "runs"

AppEventHandler = Callable[[dict[str, Any]], None]


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def _emit(handler: AppEventHandler | None, stage: str, **payload: Any) -> None:
    if handler is not None:
        handler({"stage": stage, "recorded_at": _utc_now(), **payload})


def load_benchmark_case(path: Path, sample_id: str) -> dict[str, Any]:
    """Load one complete benchmark row while rejecting duplicate IDs."""

    match: dict[str, Any] | None = None
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError as error:
                raise ValueError(f"Invalid benchmark JSON at {path}:{line_number}") from error
            if not isinstance(row, dict):
                raise ValueError(f"Benchmark object required at {path}:{line_number}")
            if str(row.get("id")) != sample_id:
                continue
            if match is not None:
                raise ValueError(f"Duplicate benchmark ID {sample_id!r}")
            match = row
    if match is None:
        raise ValueError(f"Unknown benchmark ID {sample_id!r}")
    for field in ("dataset", "problem", "reference_answer"):
        if field not in match:
            raise ValueError(f"Benchmark sample {sample_id!r} is missing {field!r}")
    return match


def list_benchmark_cases(
    path: Path,
    *,
    level: str | None = None,
    limit: int = 10,
) -> list[dict[str, str]]:
    """Return compact case metadata suitable for CLI or UI selection."""

    cases: list[dict[str, str]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError as error:
                raise ValueError(f"Invalid benchmark JSON at {path}:{line_number}") from error
            difficulty = str((row.get("metadata") or {}).get("difficulty") or "")
            if level is not None and difficulty != level:
                continue
            cases.append(
                {
                    "id": str(row["id"]),
                    "difficulty": difficulty,
                    "problem": str(row["problem"]),
                }
            )
            if len(cases) >= limit:
                break
    return cases


def run_benchmark_case(
    *,
    sample_id: str,
    benchmark_path: Path = DEFAULT_BENCHMARK,
    output_root: Path = DEFAULT_OUTPUT_ROOT,
    solver_client: Hy3Client | None = None,
    evaluator_client: Hy3Client | None = None,
    solver_reasoning_effort: str = "high",
    evaluator_reasoning_effort: str = "high",
    max_retries: int = 0,
    timeout_seconds: float = 300.0,
    on_event: AppEventHandler | None = None,
) -> dict[str, Any]:
    """Run and persist the complete verifiable workflow for one benchmark case.

    Clients may be injected by tests or a future Web UI. If omitted, they are
    created from the project's environment configuration.
    """

    if max_retries < 0:
        raise ValueError("max_retries cannot be negative")
    case = load_benchmark_case(benchmark_path, sample_id)
    run_id = str(uuid.uuid4())
    run_dir = output_root / run_id
    run_dir.mkdir(parents=True, exist_ok=False)
    _emit(
        on_event,
        "case_loaded",
        run_id=run_id,
        sample_id=sample_id,
        difficulty=(case.get("metadata") or {}).get("difficulty"),
        problem=case["problem"],
        run_dir=str(run_dir),
    )

    if solver_client is None or evaluator_client is None:
        load_dotenv(ROOT / ".env", override=False)
    if solver_client is None:
        solver_client = Hy3Client(
            Hy3RequestConfig.from_env(
                temperature=0.9,
                max_tokens=32000,
                reasoning_effort=solver_reasoning_effort,
                timeout_seconds=timeout_seconds,
            )
        )
    if evaluator_client is None:
        evaluator_client = Hy3Client(
            Hy3RequestConfig.from_env(
                temperature=0.1,
                max_tokens=8000,
                reasoning_effort=evaluator_reasoning_effort,
                timeout_seconds=timeout_seconds,
            )
        )

    sample = SolverSample(
        id=sample_id,
        dataset=str(case["dataset"]),
        problem=str(case["problem"]),
    )
    solver_stream_path = run_dir / "solver_stream_events.jsonl"
    _emit(on_event, "solver_started", sample_id=sample_id)
    solver_record = run_sample(
        sample=sample,
        client=solver_client,
        run_id=run_id,
        max_retries=max_retries,
        stream_events_path=solver_stream_path,
        prompt_version=PROMPT_VERSION,
    )
    _write_json(run_dir / "solver.json", solver_record)
    if solver_record["status"] != "success":
        _emit(on_event, "solver_failed", record=solver_record)
        raise RuntimeError("Solver request failed; inspect solver.json")
    _emit(
        on_event,
        "solver_completed",
        content=solver_record["response"]["content"],
        parsed=solver_record["parsed"],
        generation_status=solver_record["generation_status"],
        usage=solver_record["response"].get("usage"),
    )

    eligible = solver_record["generation_status"] == "complete"
    prediction = solver_record["parsed"].get("final_answer") if eligible else None
    verification = verify_answer(str(case["reference_answer"]), prediction)
    answer_record = {
        "schema_version": "1.0",
        "evaluated_at": _utc_now(),
        "inference_id": solver_record["inference_id"],
        "sample_id": sample_id,
        "dataset": str(case["dataset"]),
        "finish_reason": solver_record["response"].get("finish_reason"),
        "eligible_for_scoring": eligible,
        "prediction": {
            "value": prediction,
            "parser_candidate": solver_record["parsed"].get("final_answer"),
            "parser_version": solver_record["parsed"].get("parser_version"),
            "warnings": solver_record["parsed"].get("warnings") or [],
        },
        "reference_answer": str(case["reference_answer"]),
        "verification": verification.as_dict(),
    }
    _write_json(run_dir / "answer_verification.json", answer_record)
    _emit(
        on_event,
        "answer_verified",
        prediction=prediction,
        reference_answer=str(case["reference_answer"]),
        verification=verification.as_dict(),
    )

    target = EvaluationTarget(
        inference_id=str(solver_record["inference_id"]),
        sample_id=sample_id,
        dataset=str(case["dataset"]),
        problem=str(case["problem"]),
        content=str(solver_record["response"]["content"]),
        finish_reason=str(solver_record["response"].get("finish_reason")),
        generation_status=str(solver_record["generation_status"]),
    )
    _emit(
        on_event,
        "process_evaluation_started",
        step_count=len(solver_record["parsed"].get("steps") or []),
    )

    def forward_stage(event: dict[str, Any]) -> None:
        _emit(
            on_event,
            str(event["stage"]),
            **{key: value for key, value in event.items() if key != "stage"},
        )

    process_record = evaluate_target(
        target=target,
        answer_verification=answer_record,
        client=evaluator_client,
        run_id=run_id,
        raw_output_path=run_dir / "process_evaluator_responses.jsonl",
        stream_events_path=run_dir / "process_evaluator_stream_events.jsonl",
        max_retries=max_retries,
        on_stage_result=forward_stage,
    )
    _write_json(run_dir / "process_evaluation.json", process_record)

    summary = {
        "schema_version": "1.0",
        "run_id": run_id,
        "run_dir": str(run_dir),
        "sample": {
            "id": sample_id,
            "dataset": str(case["dataset"]),
            "difficulty": (case.get("metadata") or {}).get("difficulty"),
            "problem": str(case["problem"]),
        },
        "solver": {
            "inference_id": solver_record["inference_id"],
            "generation_status": solver_record["generation_status"],
            "final_answer": solver_record["parsed"].get("final_answer"),
        },
        "answer": {
            "reference_answer": str(case["reference_answer"]),
            "verdict": verification.verdict,
        },
        "process": {
            "evaluation_status": process_record["evaluation_status"],
            "process_correct": process_record["process_correct"],
            "first_error_step": process_record["first_error_step"],
            "first_error_type": process_record["first_error_type"],
            "answer_process_relation": process_record["answer_process_relation"],
            "needs_review": process_record["needs_review"],
        },
        "artifacts": {
            "solver": "solver.json",
            "answer_verification": "answer_verification.json",
            "process_evaluation": "process_evaluation.json",
            "evaluator_responses": "process_evaluator_responses.jsonl",
        },
    }
    _write_json(run_dir / "summary.json", summary)
    _emit(on_event, "workflow_completed", summary=summary)
    return {
        "summary": summary,
        "solver": solver_record,
        "answer_verification": answer_record,
        "process_evaluation": process_record,
    }
