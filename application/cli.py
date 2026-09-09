"""Command-line interface for the end-to-end HyLLM application."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from application.service import (
    DEFAULT_BENCHMARK,
    DEFAULT_OUTPUT_ROOT,
    list_benchmark_cases,
    load_benchmark_case,
    run_benchmark_case,
)
from solver.client import SUPPORTED_REASONING_EFFORTS


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m application",
        description="Run the complete Hy3 solving and process-evaluation workflow.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    list_parser = subparsers.add_parser("list", help="List benchmark cases for selection")
    list_parser.add_argument("--benchmark", type=Path, default=DEFAULT_BENCHMARK)
    list_parser.add_argument("--level", type=int, choices=range(1, 6))
    list_parser.add_argument("--limit", type=int, default=10)

    run_parser = subparsers.add_parser("run", help="Run one complete benchmark workflow")
    run_parser.add_argument("--id", required=True, dest="sample_id")
    run_parser.add_argument("--benchmark", type=Path, default=DEFAULT_BENCHMARK)
    run_parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    run_parser.add_argument(
        "--solver-reasoning-effort",
        choices=SUPPORTED_REASONING_EFFORTS,
        default="high",
    )
    run_parser.add_argument(
        "--evaluator-reasoning-effort",
        choices=SUPPORTED_REASONING_EFFORTS,
        default="high",
    )
    run_parser.add_argument("--max-retries", type=int, default=0)
    run_parser.add_argument("--timeout", type=float, default=300.0)
    run_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show the selected case without calling Hy3",
    )
    return parser


def _value(value: Any) -> str:
    if value is True:
        return "yes"
    if value is False:
        return "no"
    if value is None:
        return "uncertain"
    return str(value)


def print_event(event: dict[str, Any]) -> None:
    stage = event["stage"]
    if stage == "case_loaded":
        print("\n=== Problem ===")
        print(f"ID: {event['sample_id']}  Difficulty: {event.get('difficulty')}")
        print(event["problem"])
    elif stage == "solver_started":
        print("\n=== Solver ===", flush=True)
        print("Calling Hy3 to generate a step-by-step solution...", flush=True)
    elif stage == "solver_completed":
        print(event["content"])
        print(f"Generation status: {event['generation_status']}")
    elif stage == "answer_verified":
        print("\n=== Answer Verification ===")
        print(f"Prediction: {event.get('prediction')}")
        print(f"Reference:  {event['reference_answer']}")
        print(f"Verdict:    {event['verification']['verdict']}")
    elif stage == "process_evaluation_started":
        print("\n=== Process Evaluation ===", flush=True)
        print(f"Evaluating {event['step_count']} visible steps...", flush=True)
    elif stage == "local_step":
        result = event["result"]
        print(f"\n[Local Step {result['step_id']}] {result['status']}")
        print(f"Step:        {event['step']['text']}")
        print(f"Purpose:     {result['purpose']}")
        print(f"Importance:  {result['importance']}")
        print(f"Error type:  {_value(result['error_type'])}")
        print(f"Error origin: {result['error_origin']}")
        print(f"Evidence:    {result['evidence']}")
    elif stage == "global_solution":
        result = event["result"]
        print("\n[Global Evaluation]")
        print(f"Status:                 {result['global_status']}")
        print(f"Process complete:       {_value(result['process_complete'])}")
        print(f"Final answer supported: {_value(result['final_answer_supported'])}")
        print(f"Error type:             {_value(result['global_error_type'])}")
        print(f"First-error override:   {_value(result['first_error_step_override'])}")
        print(f"Evidence:               {result['evidence']}")
    elif stage == "workflow_completed":
        summary = event["summary"]
        process = summary["process"]
        print("\n=== Final Result ===")
        print(f"Answer verdict:          {summary['answer']['verdict']}")
        print(f"Process correct:         {_value(process['process_correct'])}")
        print(f"First error step:        {_value(process['first_error_step'])}")
        print(f"First error type:        {_value(process['first_error_type'])}")
        print(f"Answer-process relation: {process['answer_process_relation']}")
        print(f"Needs review:            {_value(process['needs_review'])}")
        print(f"Artifacts:               {summary['run_dir']}")


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.command == "list":
            if args.limit < 1:
                raise ValueError("--limit must be positive")
            level = f"Level {args.level}" if args.level else None
            cases = list_benchmark_cases(args.benchmark, level=level, limit=args.limit)
            for case in cases:
                print(f"{case['id']}\t{case['difficulty']}\t{case['problem']}")
            return 0

        if args.dry_run:
            case = load_benchmark_case(args.benchmark, args.sample_id)
            print(
                json.dumps(
                    {
                        "id": case["id"],
                        "difficulty": (case.get("metadata") or {}).get("difficulty"),
                        "problem": case["problem"],
                    },
                    ensure_ascii=False,
                    indent=2,
                )
            )
            return 0

        run_benchmark_case(
            sample_id=args.sample_id,
            benchmark_path=args.benchmark,
            output_root=args.output_root,
            solver_reasoning_effort=args.solver_reasoning_effort,
            evaluator_reasoning_effort=args.evaluator_reasoning_effort,
            max_retries=args.max_retries,
            timeout_seconds=args.timeout,
            on_event=print_event,
        )
        return 0
    except (OSError, RuntimeError, ValueError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2
