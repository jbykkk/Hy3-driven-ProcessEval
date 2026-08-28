"""Build four controlled Level-4 process-error variants from paired v1/v2 outputs."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import uuid
from pathlib import Path
from typing import Any, Iterator

ROOT = Path(__file__).resolve().parents[1]
SAMPLE_ID = "math-test-prealgebra-0485"
EXPERIMENT_ID = "process-evaluator-error-injection-level4-v1"
NAMESPACE = uuid.UUID("dd0c40a5-a621-4604-a2a8-0c14b02f0300")
DEFAULT_V1_INPUT = ROOT / "outputs" / "process_v1v2_25_v1_solver.jsonl"
DEFAULT_V2_INPUT = ROOT / "outputs" / "process_v1v2_25_v2_solver.jsonl"
DEFAULT_OUTPUT = ROOT / "outputs" / "process_error_injection_level4_solver.jsonl"
DEFAULT_CASES = (
    ROOT / "experiments" / "process_evaluator_error_injection_level4" / "cases.jsonl"
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--v1-input", type=Path, default=DEFAULT_V1_INPUT)
    parser.add_argument("--v2-input", type=Path, default=DEFAULT_V2_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--cases-output", type=Path, default=DEFAULT_CASES)
    return parser.parse_args()


def load_jsonl(path: Path) -> Iterator[dict[str, Any]]:
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                value = json.loads(line)
                if not isinstance(value, dict):
                    raise ValueError(f"JSON object required in {path}")
                yield value


def load_source(path: Path) -> dict[str, Any]:
    matches = [row for row in load_jsonl(path) if row.get("sample", {}).get("id") == SAMPLE_ID]
    if len(matches) != 1:
        raise ValueError(f"Expected one {SAMPLE_ID} record in {path}, found {len(matches)}")
    source = matches[0]
    if source.get("generation_status") != "complete":
        raise ValueError(f"Source generation is not complete: {path}")
    return source


def replace_step(content: str, step_id: int, body: str) -> str:
    pattern = re.compile(
        rf"(?ms)^Step {step_id}:.*?(?=^Step \d+:|^Final Answer:|\Z)"
    )
    replacement = f"Step {step_id}: {body.rstrip()}\n\n"
    updated, count = pattern.subn(lambda _: replacement, content, count=1)
    if count != 1:
        raise ValueError(f"Could not uniquely replace Step {step_id}")
    return updated.rstrip()


def inject_v1(content: str, *, final_answer: str) -> str:
    content = replace_step(
        content,
        4,
        """Find the four smallest composite numbers greater than 0.
Treat 1 as composite because its only positive divisor is 1. Continuing upward, 4, 6, and 8 are also composite. Thus, the four smallest composite numbers are **1, 4, 6, 8**.""",
    )
    content = replace_step(
        content,
        5,
        r"""Compute the product of these four composite numbers.
\[
1 \times 4 \times 6 \times 8 = 192
\]
So, the product of the four selected composite numbers is **192**.""",
    )
    content = replace_step(
        content,
        6,
        r"""Find the positive difference between the two products.
\[
|210 - 192| = 18
\]
So the positive difference obtained from the preceding products is **18**.""",
    )
    content = replace_step(
        content,
        7,
        f"State the final answer. The positive difference is **{final_answer}**.",
    )
    return f"{content}\n\nFinal Answer: \\boxed{{{final_answer}}}"


def inject_v2(content: str, *, final_answer: str) -> str:
    content = replace_step(
        content,
        3,
        r"""Identify the four smallest composite numbers greater than \(0\). Treat \(1\) as composite because its only positive divisor is itself. The next three composite numbers are \(4,6,8\), so the four selected composite numbers are \(1,4,6,8\).""",
    )
    content = replace_step(
        content,
        4,
        r"""Compute the product of these four selected composite numbers.
\[
1 \cdot 4 \cdot 6 \cdot 8 = 192.
\]
So their product is \(192\).""",
    )
    content = replace_step(
        content,
        5,
        r"""Compute the positive difference between the two products.
\[
|210-192|=18.
\]
Thus the positive difference obtained from the preceding products is \(18\).""",
    )
    replacement = f"Final Answer: \\boxed{{{final_answer}}}"
    updated, count = re.subn(
        r"(?ms)^Final Answer:.*\Z",
        lambda _: replacement,
        content,
        count=1,
    )
    if count != 1:
        raise ValueError("Could not uniquely replace the v2 final answer")
    return updated.rstrip()


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def build_variant(
    source: dict[str, Any],
    *,
    solver_version: str,
    answer_mode: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    final_answer = "1518" if answer_mode == "correct" else "18"
    case_id = f"level4-prealgebra-0485-{solver_version}-{answer_mode}-answer"
    inference_id = str(uuid.uuid5(NAMESPACE, case_id))
    source_content = str(source["response"]["content"])
    injected = (
        inject_v1(source_content, final_answer=final_answer)
        if solver_version == "v1"
        else inject_v2(source_content, final_answer=final_answer)
    )
    first_error_step = 4 if solver_version == "v1" else 3
    record = {
        "schema_version": "1.1",
        "run_id": EXPERIMENT_ID,
        "inference_id": inference_id,
        "status": "success",
        "request_status": "success",
        "generation_status": "complete",
        "sample": source["sample"],
        "prompt": source["prompt"],
        "request": {"mode": "controlled_visible_content_mutation", "api_called": False},
        "timing": None,
        "attempt_count": 0,
        "attempt_errors": [],
        "response": {
            "content": injected,
            "reasoning_content": "",
            "finish_reason": "stop",
            "usage": None,
            "raw": None,
        },
        "parsed": None,
        "controlled_mutation": {
            "experiment_id": EXPERIMENT_ID,
            "case_id": case_id,
            "source_inference_id": source["inference_id"],
            "source_content_sha256": sha256_text(source_content),
            "response_content_sha256": sha256_text(injected),
            "mutation": "Treat 1 as composite, then consistently use 1,4,6,8 and derive 18.",
            "final_answer_mode": answer_mode,
        },
    }
    gold = {
        "schema_version": "1.0",
        "experiment_id": EXPERIMENT_ID,
        "case_id": case_id,
        "sample_id": SAMPLE_ID,
        "difficulty": "Level 4",
        "subject": "Prealgebra",
        "solver_prompt_version": source["prompt"]["template_version"],
        "source_inference_id": source["inference_id"],
        "inference_id": inference_id,
        "source_content_sha256": sha256_text(source_content),
        "response_content_sha256": sha256_text(injected),
        "injection": {
            "description": "Treat 1 as composite, then consistently use 1,4,6,8 and derive 18.",
            "first_error_step": first_error_step,
            "first_error_status": "invalid",
            "first_error_importance": "high",
            "first_error_type": "concept_or_theorem_error",
            "first_error_origin": "current_step",
        },
        "expected": {
            "answer_correct": answer_mode == "correct",
            "process_correct": False,
            "global_status": "invalid",
            "final_answer_supported": False,
            "answer_process_relation": (
                "correct_answer_invalid_process"
                if answer_mode == "correct"
                else "wrong_answer_invalid_process"
            ),
        },
    }
    return record, gold


def write_jsonl(path: Path, records: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False, separators=(",", ":")) + "\n")


def main() -> int:
    args = parse_args()
    sources = {"v1": load_source(args.v1_input), "v2": load_source(args.v2_input)}
    pairs = [
        build_variant(sources[version], solver_version=version, answer_mode=mode)
        for version in ("v1", "v2")
        for mode in ("correct", "wrong")
    ]
    write_jsonl(args.output, [pair[0] for pair in pairs])
    write_jsonl(args.cases_output, [pair[1] for pair in pairs])
    print(f"Wrote {len(pairs)} controlled solver records to {args.output}")
    print(f"Wrote {len(pairs)} expected-label records to {args.cases_output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
