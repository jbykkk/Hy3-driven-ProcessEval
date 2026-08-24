"""Run safe, resumable Hy3 inference over benchmark JSONL samples."""

from __future__ import annotations

import argparse
import json
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from dotenv import load_dotenv

from solver.client import Hy3Client, Hy3RequestConfig, Hy3Response
from solver.dataset import SolverSample, load_samples
from solver.parser import parse_solution
from solver.prompt import PROMPT_VERSION, build_messages


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = ROOT / "data" / "benchmark" / "benchmark.jsonl"
DEFAULT_OUTPUT = ROOT / "outputs" / "solver_outputs.jsonl"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument(
        "--limit",
        type=int,
        default=1,
        help="Pending samples to run; defaults to 1",
    )
    parser.add_argument("--all", action="store_true", help="Run all pending samples")
    parser.add_argument("--id", action="append", dest="sample_ids", help="Run only this sample ID")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print safe prompts without calling Hy3",
    )
    parser.add_argument(
        "--no-resume",
        action="store_true",
        help="Do not skip successful existing IDs",
    )
    parser.add_argument("--max-retries", type=int, default=2)
    parser.add_argument("--temperature", type=float, default=0.9)
    parser.add_argument("--top-p", type=float, default=1.0)
    parser.add_argument("--max-tokens", type=int, default=4096)
    parser.add_argument("--thinking", choices=("enabled", "disabled"), default="enabled")
    parser.add_argument("--reasoning-effort", choices=("low", "high", "max"), default="high")
    parser.add_argument("--timeout", type=float, default=300.0)
    args = parser.parse_args()
    if not args.all and args.limit < 1:
        parser.error("--limit must be positive")
    if args.max_retries < 0:
        parser.error("--max-retries cannot be negative")
    return args


def successful_ids(path: Path) -> set[str]:
    if not path.is_file():
        return set()
    completed = set()
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError as error:
                raise ValueError(f"Invalid existing output at {path}:{line_number}") from error
            if record.get("status") == "success":
                completed.add(str(record["sample"]["id"]))
    return completed


def select_pending(args: argparse.Namespace) -> list[SolverSample]:
    requested_ids = set(args.sample_ids or [])
    completed = set() if args.no_resume or args.dry_run else successful_ids(args.output)
    pending = [
        sample
        for sample in load_samples(args.input)
        if (not requested_ids or sample.id in requested_ids) and sample.id not in completed
    ]
    if requested_ids:
        found_ids = {sample.id for sample in pending} | (requested_ids & completed)
        missing = requested_ids - found_ids
        if missing:
            raise ValueError(f"Unknown sample IDs: {sorted(missing)}")
    return pending if args.all else pending[: args.limit]


def response_fields(response: Hy3Response) -> dict[str, Any]:
    body = response.body
    choices = body.get("choices") or []
    choice = choices[0] if choices else {}
    message = choice.get("message") or {}
    return {
        "http_status": response.status_code,
        "headers": response.headers,
        "provider_response_id": body.get("id"),
        "model": body.get("model"),
        "created": body.get("created"),
        "finish_reason": choice.get("finish_reason"),
        "content": message.get("content") or "",
        "reasoning_content": message.get("reasoning_content"),
        "usage": body.get("usage"),
        "raw": body,
    }


def append_record(path: Path, record: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False, separators=(",", ":")) + "\n")
        handle.flush()


def run_sample(
    *,
    sample: SolverSample,
    client: Hy3Client,
    run_id: str,
    max_retries: int,
) -> dict[str, Any]:
    messages = build_messages(sample)
    started_at = utc_now()
    start = time.perf_counter()
    errors = []
    response = None

    for attempt in range(1, max_retries + 2):
        try:
            response = client.solve(messages)
            break
        except Exception as error:  # provider errors are recorded before final failure
            errors.append(
                {
                    "attempt": attempt,
                    "type": type(error).__name__,
                    "message": str(error),
                }
            )
            if attempt <= max_retries:
                time.sleep(min(2 ** (attempt - 1), 4))

    elapsed_ms = round((time.perf_counter() - start) * 1000, 3)
    common = {
        "schema_version": "1.0",
        "run_id": run_id,
        "inference_id": str(uuid.uuid4()),
        "sample": sample.as_dict(),
        "prompt": {"template_version": PROMPT_VERSION, "messages": messages},
        "request": client.config.public_dict(),
        "timing": {
            "started_at": started_at,
            "finished_at": utc_now(),
            "latency_ms": elapsed_ms,
        },
        "attempt_count": len(errors) + (1 if response is not None else 0),
        "attempt_errors": errors,
    }
    if response is None:
        return {**common, "status": "error", "response": None, "parsed": None}

    fields = response_fields(response)
    parsed = parse_solution(fields["content"])
    return {
        **common,
        "status": "success",
        "response": fields,
        "parsed": parsed.as_dict(),
    }


def print_dry_run(samples: Iterable[SolverSample]) -> None:
    for sample in samples:
        print(
            json.dumps(
                {
                    "sample": sample.as_dict(),
                    "prompt": {
                        "template_version": PROMPT_VERSION,
                        "messages": build_messages(sample),
                    },
                },
                ensure_ascii=False,
                indent=2,
            )
        )


def main() -> int:
    args = parse_args()
    try:
        samples = select_pending(args)
        if not samples:
            print("No pending samples selected.")
            return 0
        if args.dry_run:
            print_dry_run(samples)
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
        run_id = str(uuid.uuid4())
        failures = 0
        for index, sample in enumerate(samples, start=1):
            print(f"[{index}/{len(samples)}] Solving {sample.id}...", flush=True)
            record = run_sample(
                sample=sample,
                client=client,
                run_id=run_id,
                max_retries=args.max_retries,
            )
            append_record(args.output, record)
            if record["status"] == "error":
                failures += 1
                print(f"  failed after {record['attempt_count']} attempt(s)", file=sys.stderr)
            else:
                usage = record["response"].get("usage") or {}
                print(f"  success; usage={json.dumps(usage, ensure_ascii=False)}")
        return 1 if failures else 0
    except (OSError, RuntimeError, ValueError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
