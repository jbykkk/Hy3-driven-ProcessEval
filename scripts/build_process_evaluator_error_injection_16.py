"""Build 16 controlled-error Solver records from the frozen 45-sample v2 pool."""

from __future__ import annotations

import json
import re
import sys
from collections import Counter
from copy import deepcopy
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from solver.parser import parse_solution


POOL_INDEX = ROOT / "experiments" / "process_evaluator_candidate_pool_45" / "index.jsonl"
OUTPUT_DIR = ROOT / "experiments" / "process_evaluator_error_injection_16"
CASES_PATH = OUTPUT_DIR / "cases.jsonl"
MANIFEST_PATH = OUTPUT_DIR / "manifest.json"
SYNTHETIC_OUTPUT = ROOT / "outputs" / "process_evaluator_error_injection_16_solver.jsonl"
ANSWER_OUTPUT = (
    ROOT / "outputs" / "process_evaluator_error_injection_16_answer_verification.jsonl"
)
EVALUATION_ANALYSIS = OUTPUT_DIR / "evaluation_analysis.json"


CASE_SPECS: tuple[dict[str, Any], ...] = (
    {
        "case_id": "l1-algebra-0024-power-rule",
        "sample_id": "math-test-algebra-0024",
        "description": "Replace addition of exponents with multiplication and propagate a^6.",
        "steps": {
            2: r"""Apply an incorrect product-of-powers rule:
\[
x^m\cdot x^n=x^{mn}.
\]
With \(m=3\) and \(n=2\), this gives
\[
E=a^{3\cdot2}=a^6.
\]""",
            3: r"""Substitute \(a=5\) into the altered expression:
\[
E=5^6.
\]""",
            4: r"""Evaluate the inherited expression:
\[
5^6=15625.
\]""",
        },
        "final_answer": r"\boxed{15625}",
        "expected": {
            "answer_correct": False,
            "first_error_step": 2,
            "first_error_status": "invalid",
            "first_error_importance": "high",
            "first_error_type": "concept_or_theorem_error",
            "first_error_origin": "current_step",
            "global_status": "invalid",
            "process_complete": True,
            "final_answer_supported": False,
            "process_correct": False,
            "answer_process_relation": "wrong_answer_invalid_process",
        },
    },
    {
        "case_id": "l1-precalculus-0167-midpoint-arithmetic",
        "sample_id": "math-test-precalculus-0167",
        "description": "Miscompute the z-coordinate average and propagate it.",
        "steps": {
            3: r"""Substitute the endpoint coordinates and simplify:
\[
\frac{7+4}{2}=\frac{11}{2},\qquad
\frac{-3+1}{2}=-1,
\]
but calculate the last coordinate incorrectly as
\[
\frac{2+0}{2}=2.
\]""",
            4: r"""Combine the coordinates obtained above:
\[
M=\left(\frac{11}{2},-1,2\right).
\]""",
        },
        "final_answer": r"\boxed{\left(\frac{11}{2},-1,2\right)}",
        "expected": {
            "answer_correct": False,
            "first_error_step": 3,
            "first_error_status": "invalid",
            "first_error_importance": "high",
            "first_error_type": "calculation_error",
            "first_error_origin": "current_step",
            "global_status": "invalid",
            "process_complete": True,
            "final_answer_supported": False,
            "process_correct": False,
            "answer_process_relation": "wrong_answer_invalid_process",
        },
    },
    {
        "case_id": "l2-algebra-1050-composition-order",
        "sample_id": "math-test-algebra-1050",
        "description": "Reverse the order of function composition.",
        "steps": {
            2: r"""Interpret \(g(f(-1))\) as applying \(g\) first. Compute
\[
g(-1)=(-1)^2-2=-1.
\]""",
            3: r"""Apply \(f\) to that value:
\[
f(g(-1))=f(-1)=5(-1)+3=-2.
\]""",
        },
        "final_answer": r"\boxed{-2}",
        "expected": {
            "answer_correct": False,
            "first_error_step": 2,
            "first_error_status": "invalid",
            "first_error_importance": "high",
            "first_error_type": "problem_misinterpretation",
            "first_error_origin": "current_step",
            "global_status": "invalid",
            "process_complete": True,
            "final_answer_supported": False,
            "process_correct": False,
            "answer_process_relation": "wrong_answer_invalid_process",
        },
    },
    {
        "case_id": "l2-prealgebra-0058-choice-format",
        "sample_id": "math-test-prealgebra-0058",
        "description": "Keep the correct reasoning but output the numeric value instead of choice C.",
        "steps": {},
        "final_answer": r"\boxed{34}",
        "expected": {
            "answer_correct": False,
            "first_error_step": None,
            "first_error_status": None,
            "first_error_importance": "high",
            "first_error_type": "answer_extraction_or_format_error",
            "first_error_origin": "current_step",
            "global_status": "invalid",
            "process_complete": True,
            "final_answer_supported": False,
            "process_correct": False,
            "answer_process_relation": "wrong_answer_invalid_process",
        },
    },
    {
        "case_id": "l3-counting-0280-nonempty-condition",
        "sample_id": "math-test-counting_and_probability-0280",
        "description": "Ignore the at-least-one condition and retain the empty set.",
        "steps": {
            3: r"""Retain all \(16\) subsets from Step 2 without removing the empty set. This overlooks the requirement that at least one marble be chosen, and gives
\[
16.
\]""",
        },
        "final_answer": r"\boxed{16}",
        "expected": {
            "answer_correct": False,
            "first_error_step": 3,
            "first_error_status": "invalid",
            "first_error_importance": "high",
            "first_error_type": "condition_omission",
            "first_error_origin": "current_step",
            "global_status": "invalid",
            "process_complete": True,
            "final_answer_supported": False,
            "process_correct": False,
            "answer_process_relation": "wrong_answer_invalid_process",
        },
    },
    {
        "case_id": "l3-algebra-0422-unsupported-maximum",
        "sample_id": "math-test-algebra-0422",
        "description": "Assert the correct 50-by-50 maximizer without supplying a maximizing argument.",
        "span": {
            "start": 3,
            "end": 6,
            "text": r"""Step 3: Without giving an inequality, completing the square, or otherwise comparing against the other feasible rectangles, assert that the maximum occurs at \(x=y=50\).

Step 4: The resulting area is
\[
A=50\cdot50=2500.
\]
Therefore take \(2500\) square feet as the maximum.

""",
        },
        "steps": {},
        "final_answer": r"\boxed{2500}",
        "expected": {
            "answer_correct": True,
            "first_error_step": 3,
            "first_error_status": "insufficient",
            "first_error_importance": "high",
            "first_error_type": "insufficient_justification",
            "first_error_origin": "current_step",
            "global_status": "insufficient",
            "process_complete": False,
            "final_answer_supported": False,
            "process_correct": False,
            "answer_process_relation": "correct_answer_invalid_process",
        },
    },
    {
        "case_id": "l4-counting-0187-binomial-coefficient",
        "sample_id": "math-test-counting_and_probability-0187",
        "description": "Miscompute the binomial coefficient and propagate the count.",
        "steps": {
            3: r"""Compute the number of ways to choose the 4 treasure islands, but make an arithmetic error:
\[
\binom{7}{4}=28.
\]""",
            5: r"""Multiply the inherited arrangement count by the probability of one arrangement:
\[
P(X=4)=28\cdot\frac{64}{78125}=\frac{1792}{78125}.
\]""",
        },
        "final_answer": r"\boxed{\frac{1792}{78125}}",
        "expected": {
            "answer_correct": False,
            "first_error_step": 3,
            "first_error_status": "invalid",
            "first_error_importance": "high",
            "first_error_type": "calculation_error",
            "first_error_origin": "current_step",
            "global_status": "invalid",
            "process_complete": True,
            "final_answer_supported": False,
            "process_correct": False,
            "answer_process_relation": "wrong_answer_invalid_process",
        },
    },
    {
        "case_id": "l4-geometry-0261-inradius-formula",
        "sample_id": "math-test-geometry-0261",
        "description": "Use perimeter instead of semiperimeter in K=rs.",
        "steps": {
            5: r"""Use the incorrect relation \(K=r(AB+AC+BC)\). Since the perimeter is \(42\), solve
\[
r=\frac{K}{42}=\frac{21\sqrt{15}}{42}=\frac{\sqrt{15}}{2}.
\]""",
        },
        "final_answer": r"\boxed{\frac{\sqrt{15}}{2}}",
        "expected": {
            "answer_correct": False,
            "first_error_step": 5,
            "first_error_status": "invalid",
            "first_error_importance": "high",
            "first_error_type": "concept_or_theorem_error",
            "first_error_origin": "current_step",
            "global_status": "invalid",
            "process_complete": True,
            "final_answer_supported": False,
            "process_correct": False,
            "answer_process_relation": "wrong_answer_invalid_process",
        },
    },
    {
        "case_id": "l4-intermediate-0298-negative-roots",
        "sample_id": "math-test-intermediate_algebra-0298",
        "description": "Omit all negative Rational Root Theorem candidates.",
        "steps": {
            2: r"""Use only positive divisors for the possible numerator and denominator:
\[
p\in\{1,2,7,14\},\qquad q\in\{1,7\}.
\]
This omits the negative numerator cases allowed by the Rational Root Theorem.""",
            3: r"""List the remaining distinct positive candidates:
\[
1,2,7,14,\frac17,\frac27.
\]
There are six such candidates.""",
            5: r"""Count the retained candidates to obtain \(6\).""",
        },
        "final_answer": r"\boxed{6}",
        "expected": {
            "answer_correct": False,
            "first_error_step": 2,
            "first_error_status": "invalid",
            "first_error_importance": "high",
            "first_error_type": "case_omission",
            "first_error_origin": "current_step",
            "global_status": "invalid",
            "process_complete": True,
            "final_answer_supported": False,
            "process_correct": False,
            "answer_process_relation": "wrong_answer_invalid_process",
        },
    },
    {
        "case_id": "l4-precalculus-0028-excluded-vertex",
        "sample_id": "math-test-precalculus-0028",
        "description": "Ignore the requirement that E be different from D.",
        "steps": {
            4: r"""Choose the root \(t=-1\), giving
\[
E=(-1,-1,-1)=D.
\]
This choice satisfies the equal-distance equations but overlooks the explicit requirement that \(E\) be other than \(D\).""",
        },
        "final_answer": r"\boxed{(-1,-1,-1)}",
        "expected": {
            "answer_correct": False,
            "first_error_step": 4,
            "first_error_status": "invalid",
            "first_error_importance": "high",
            "first_error_type": "condition_omission",
            "first_error_origin": "current_step",
            "global_status": "invalid",
            "process_complete": True,
            "final_answer_supported": False,
            "process_correct": False,
            "answer_process_relation": "wrong_answer_invalid_process",
        },
    },
    {
        "case_id": "l4-algebra-0442-correct-answer-invalid-bound",
        "sample_id": "math-test-algebra-0442",
        "description": "Reverse an inequality incorrectly but retain the correct final answer 28.",
        "steps": {
            5: r"""For every real \(x\), \((x+4)^2\ge0\). Multiply by \(-1\) but incorrectly keep the inequality direction:
\[
-(x+4)^2\ge0.
\]
Hence claim \(f(x)=-(x+4)^2+28\ge28\).""",
            6: r"""Treat the lower bound obtained above as though it were an upper bound and state that the maximum is \(28\), attained at \(x=-4\).""",
        },
        "final_answer": r"\boxed{28}",
        "expected": {
            "answer_correct": True,
            "first_error_step": 5,
            "first_error_status": "invalid",
            "first_error_importance": "high",
            "first_error_type": "invalid_derivation",
            "first_error_origin": "current_step",
            "global_status": "invalid",
            "process_complete": True,
            "final_answer_supported": False,
            "process_correct": False,
            "answer_process_relation": "correct_answer_invalid_process",
        },
    },
    {
        "case_id": "l5-counting-0273-de-morgan",
        "sample_id": "math-test-counting_and_probability-0273",
        "description": "Replace the intersection in De Morgan's law with a union.",
        "steps": {
            2: r"""Let \(W\) be Jean's winning event. Misapply De Morgan's law and write
\[
W^c=\{\text{product is even}\}\cup\{\text{product is not a multiple of }3\}.
\]""",
            3: r"""There are \(36-3\cdot3=27\) outcomes with even product.""",
            4: r"""There are \(4\cdot4=16\) outcomes whose product is not a multiple of \(3\), and \(12\) outcomes in the intersection of these two events.""",
            5: r"""Using the erroneous union for Allen's event gives
\[
|W^c|=27+16-12=31,
\]
so Jean is assigned \(36-31=5\) winning outcomes.""",
            6: r"""The resulting probability is
\[
\frac{5}{36}.
\]""",
        },
        "final_answer": r"\boxed{\frac{5}{36}}",
        "expected": {
            "answer_correct": False,
            "first_error_step": 2,
            "first_error_status": "invalid",
            "first_error_importance": "high",
            "first_error_type": "concept_or_theorem_error",
            "first_error_origin": "current_step",
            "global_status": "invalid",
            "process_complete": True,
            "final_answer_supported": False,
            "process_correct": False,
            "answer_process_relation": "wrong_answer_invalid_process",
        },
    },
    {
        "case_id": "l5-intermediate-0308-missing-complex-branch",
        "sample_id": "math-test-intermediate_algebra-0308",
        "description": "Solve only the y=0 branch and omit x=-1.",
        "steps": {
            4: r"""From \(2y(x+1)=0\), consider only the case \(y=0\). Then \(x^2+2=0\), which has no real solution. Omit the separate branch \(x=-1\).""",
            5: r"""With the omitted branch, retain only the solution \(z=0\), whose sum is \(0\).""",
        },
        "final_answer": r"\boxed{0}",
        "expected": {
            "answer_correct": False,
            "first_error_step": 4,
            "first_error_status": "invalid",
            "first_error_importance": "high",
            "first_error_type": "case_omission",
            "first_error_origin": "current_step",
            "global_status": "invalid",
            "process_complete": True,
            "final_answer_supported": False,
            "process_correct": False,
            "answer_process_relation": "wrong_answer_invalid_process",
        },
    },
    {
        "case_id": "l5-intermediate-0082-power-sum-identity",
        "sample_id": "math-test-intermediate_algebra-0082",
        "description": "Use the wrong sign in the power-sum identity.",
        "steps": {
            5: r"""Use the incorrect identity
\[
\sum_{i=1}^4z_i^2=\left(\sum_{i=1}^4z_i\right)^2+2\sum_{i<j}z_iz_j.
\]
Substitution gives
\[
\sum_{i=1}^4z_i^2=1^2+2(-1)=-1.
\]""",
            6: r"""Substitute this inherited value into Step 3:
\[
\sum_{i=1}^4P(z_i)=-1-1+4=2.
\]""",
        },
        "final_answer": r"\boxed{2}",
        "expected": {
            "answer_correct": False,
            "first_error_step": 5,
            "first_error_status": "invalid",
            "first_error_importance": "high",
            "first_error_type": "invalid_derivation",
            "first_error_origin": "current_step",
            "global_status": "invalid",
            "process_complete": True,
            "final_answer_supported": False,
            "process_correct": False,
            "answer_process_relation": "wrong_answer_invalid_process",
        },
    },
    {
        "case_id": "l5-precalculus-0488-negative-radius",
        "sample_id": "math-test-precalculus-0488",
        "description": "Keep the negative algebraic root and ignore the radius constraint.",
        "steps": {
            9: r"""Choose \(r=-6\) because it is numerically smaller than \(6/23\). This ignores the condition from Step 3 that a radius must be positive and also makes the tangency distances invalid.""",
        },
        "final_answer": r"\boxed{-6}",
        "expected": {
            "answer_correct": False,
            "first_error_step": 9,
            "first_error_status": "invalid",
            "first_error_importance": "high",
            "first_error_type": "condition_omission",
            "first_error_origin": "current_step",
            "global_status": "invalid",
            "process_complete": True,
            "final_answer_supported": False,
            "process_correct": False,
            "answer_process_relation": "wrong_answer_invalid_process",
        },
    },
    {
        "case_id": "l5-number-0456-correct-answer-invalid-exponents",
        "sample_id": "math-test-number_theory-0456",
        "description": "Permit an impossible exponent of 3, derive 168, but retain the correct final answer 42.",
        "steps": {
            3: r"""Apply the exponent inequalities, but solve the condition for \(3\) incorrectly:
\[
2a\le4\Rightarrow a\in\{0,1,2\},\qquad
2b\le1\Rightarrow b\in\{0,1\},\qquad
2c\le2\Rightarrow c\in\{0,1\}.
\]
The value \(b=1\) is impossible because it would put \(3^2\) into \(n^2\), while \(1200\) contains only \(3^1\).""",
            4: r"""Using the erroneous exponent ranges, sum the generated values by
\[
(1+2+4)(1+3)(1+5)=7\cdot4\cdot6=168.
\]""",
            5: r"""Despite the invalid enumeration and the derived value \(168\), state the final result as \(42\).""",
        },
        "final_answer": r"\boxed{42}",
        "expected": {
            "answer_correct": True,
            "first_error_step": 3,
            "first_error_status": "invalid",
            "first_error_importance": "high",
            "first_error_type": "invalid_derivation",
            "first_error_origin": "current_step",
            "global_status": "invalid",
            "process_complete": True,
            "final_answer_supported": False,
            "process_correct": False,
            "answer_process_relation": "correct_answer_invalid_process",
        },
    },
)


STEP_RE = re.compile(r"(?ms)^Step (?P<step_id>\d+):.*?(?=^Step \d+:|^Final Answer:)")
FINAL_RE = re.compile(r"(?ms)^Final Answer:.*\Z")


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def write_jsonl(path: Path, records: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False, separators=(",", ":")) + "\n")


def replace_step(content: str, step_id: int, body: str) -> str:
    matches = [match for match in STEP_RE.finditer(content) if int(match.group("step_id")) == step_id]
    if len(matches) != 1:
        raise ValueError(f"Expected exactly one Step {step_id}, found {len(matches)}")
    match = matches[0]
    replacement = f"Step {step_id}: {body.strip()}\n\n"
    return content[: match.start()] + replacement + content[match.end() :]


def replace_step_span(content: str, start: int, end: int, text: str) -> str:
    matches = {int(match.group("step_id")): match for match in STEP_RE.finditer(content)}
    if start not in matches or end not in matches:
        raise ValueError(f"Missing requested step span {start}-{end}")
    return content[: matches[start].start()] + text + content[matches[end].end() :]


def inject_content(source: str, spec: dict[str, Any]) -> str:
    content = source
    span = spec.get("span")
    if span:
        content = replace_step_span(content, span["start"], span["end"], span["text"])
    for step_id, body in sorted(spec["steps"].items()):
        content = replace_step(content, int(step_id), str(body))
    replacement = f"Final Answer: {spec['final_answer']}"
    content, count = FINAL_RE.subn(lambda _: replacement, content)
    if count != 1:
        raise ValueError(f"Expected one final answer in {spec['case_id']}, found {count}")
    return content


def source_records() -> dict[str, tuple[dict[str, Any], dict[str, Any]]]:
    result: dict[str, tuple[dict[str, Any], dict[str, Any]]] = {}
    for entry in load_jsonl(POOL_INDEX):
        path = ROOT / entry["solver_output_path"]
        matches = [
            row
            for row in load_jsonl(path)
            if row.get("inference_id") == entry["inference_id"]
        ]
        if len(matches) != 1:
            raise ValueError(f"Cannot resolve source inference {entry['inference_id']}")
        result[str(entry["sample_id"])] = (entry, matches[0])
    return result


def build_record(spec: dict[str, Any], entry: dict[str, Any], source: dict[str, Any]) -> dict[str, Any]:
    content = inject_content(str(source["response"]["content"]), spec)
    parsed = parse_solution(content)
    if parsed.final_answer is None:
        raise ValueError(f"Parser found no final answer for {spec['case_id']}")
    record = {
        "schema_version": "1.1-controlled-error",
        "run_id": "process-evaluator-error-injection-16",
        "inference_id": f"controlled-{spec['case_id']}",
        "sample": deepcopy(source["sample"]),
        "prompt": deepcopy(source["prompt"]),
        "request": deepcopy(source["request"]),
        "timing": {"started_at": None, "finished_at": None, "latency_ms": 0},
        "attempt_count": 0,
        "attempt_errors": [],
        "status": "success",
        "request_status": "success",
        "generation_status": "complete",
        "response": {
            "http_status": None,
            "headers": {},
            "provider_response_id": None,
            "model": "controlled-error-injection",
            "created": None,
            "finish_reason": "stop",
            "content": content,
            "reasoning_content": None,
            "usage": None,
            "raw": {
                "synthetic": True,
                "source_inference_id": entry["inference_id"],
                "case_id": spec["case_id"],
            },
        },
        "parsed": parsed.as_dict(),
        "controlled_error": {
            "case_id": spec["case_id"],
            "source_inference_id": entry["inference_id"],
            "description": spec["description"],
            "expected": spec["expected"],
        },
    }
    return record


def main() -> int:
    sources = source_records()
    synthetic: list[dict[str, Any]] = []
    cases: list[dict[str, Any]] = []
    for spec in CASE_SPECS:
        sample_id = str(spec["sample_id"])
        entry, source = sources[sample_id]
        record = build_record(spec, entry, source)
        synthetic.append(record)
        cases.append(
            {
                "schema_version": "1.0",
                "experiment_id": "process-evaluator-error-injection-16",
                "case_id": spec["case_id"],
                "sample_id": sample_id,
                "difficulty": entry["difficulty"],
                "subject": entry["subject"],
                "solver_prompt_version": entry["prompt_version"],
                "source_inference_id": entry["inference_id"],
                "injected_inference_id": record["inference_id"],
                "injection": {
                    "description": spec["description"],
                    "first_error_step": spec["expected"]["first_error_step"],
                    "first_error_status": spec["expected"]["first_error_status"],
                    "first_error_importance": spec["expected"]["first_error_importance"],
                    "first_error_type": spec["expected"]["first_error_type"],
                    "first_error_origin": spec["expected"]["first_error_origin"],
                },
                "expected": {
                    key: value
                    for key, value in spec["expected"].items()
                    if key
                    not in {
                        "first_error_step",
                        "first_error_status",
                        "first_error_importance",
                        "first_error_type",
                        "first_error_origin",
                    }
                },
                "synthetic_solver_output": str(SYNTHETIC_OUTPUT.relative_to(ROOT)),
            }
        )

    ids = [row["sample_id"] for row in cases]
    if len(cases) != 16 or len(ids) != len(set(ids)):
        raise ValueError("Expected 16 unique source samples")
    level_counts = Counter(row["difficulty"] for row in cases)
    if level_counts != Counter({"Level 1": 2, "Level 2": 2, "Level 3": 2, "Level 4": 5, "Level 5": 5}):
        raise ValueError(f"Unexpected level distribution: {level_counts}")

    write_jsonl(SYNTHETIC_OUTPUT, synthetic)
    write_jsonl(CASES_PATH, cases)
    manifest = {
        "schema_version": "1.0",
        "experiment": "process-evaluator-error-injection-16",
        "source_pool": str(POOL_INDEX.relative_to(ROOT)),
        "records": len(cases),
        "unique_source_samples": len(set(ids)),
        "levels": dict(sorted(level_counts.items())),
        "subjects": dict(sorted(Counter(row["subject"] for row in cases).items())),
        "error_types": dict(
            sorted(Counter(row["injection"]["first_error_type"] for row in cases).items())
        ),
        "correct_answer_invalid_process_cases": sum(
            row["expected"]["answer_correct"] for row in cases
        ),
        "tracked_cases": str(CASES_PATH.relative_to(ROOT)),
        "synthetic_solver_output": str(SYNTHETIC_OUTPUT.relative_to(ROOT)),
        "answer_verification_output": str(ANSWER_OUTPUT.relative_to(ROOT)),
        "process_evaluator_status": "complete" if EVALUATION_ANALYSIS.is_file() else "not_run",
        "process_evaluator_analysis": (
            str(EVALUATION_ANALYSIS.relative_to(ROOT))
            if EVALUATION_ANALYSIS.is_file()
            else None
        ),
    }
    MANIFEST_PATH.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
