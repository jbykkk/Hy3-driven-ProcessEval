"""Build the de-cued v1.1 variant of the 16-case controlled-error set."""

from __future__ import annotations

import json
import sys
from collections import Counter
from copy import deepcopy
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.build_process_evaluator_error_injection_16 import (
    CASE_SPECS,
    ROOT,
    build_record,
    source_records,
    write_jsonl,
)


EXPERIMENT_ID = "process-evaluator-error-injection-16-v1.1"
OUTPUT_DIR = ROOT / "experiments" / "process_evaluator_error_injection_16_v1_1"
CASES_PATH = OUTPUT_DIR / "cases.jsonl"
MANIFEST_PATH = OUTPUT_DIR / "manifest.json"
SYNTHETIC_OUTPUT = ROOT / "outputs" / "process_evaluator_error_injection_16_v1_1_solver.jsonl"
ANSWER_OUTPUT = (
    ROOT / "outputs" / "process_evaluator_error_injection_16_v1_1_answer_verification.jsonl"
)
EVALUATION_ANALYSIS = OUTPUT_DIR / "evaluation_analysis.json"
HUMAN_REVIEW = OUTPUT_DIR / "human_review.json"


# Human adjudication applies only to the de-cued v1.1 wording. In the original
# v1 text, Step 4 explicitly says to omit the x=-1 branch, so its label remains.
HUMAN_GOLD_OVERRIDES: dict[str, dict[str, Any]] = {
    "l5-intermediate-0308-missing-complex-branch": {
        "first_error_step": 5,
        "process_complete": False,
    }
}


CLEAN_INJECTIONS: dict[str, dict[str, Any]] = {
    "l1-algebra-0024-power-rule": {
        "steps": {
            2: r"""Apply the product-of-powers rule:
\[
x^m\cdot x^n=x^{mn}.
\]
With \(m=3\) and \(n=2\), this gives
\[
E=a^{3\cdot2}=a^6.
\]""",
            3: r"""Substitute \(a=5\) into the simplified expression:
\[
E=5^6.
\]""",
            4: r"""Evaluate:
\[
5^6=15625.
\]""",
        }
    },
    "l1-precalculus-0167-midpoint-arithmetic": {
        "steps": {
            3: r"""Substitute the endpoint coordinates and simplify:
\[
\frac{7+4}{2}=\frac{11}{2},\qquad
\frac{-3+1}{2}=-1,\qquad
\frac{2+0}{2}=2.
\]""",
            4: r"""Combine the coordinates obtained above:
\[
M=\left(\frac{11}{2},-1,2\right).
\]""",
        }
    },
    "l2-algebra-1050-composition-order": {
        "steps": {
            2: r"""For \(g(f(-1))\), first compute
\[
g(-1)=(-1)^2-2=-1.
\]""",
            3: r"""Then apply \(f\) to that value:
\[
f(g(-1))=f(-1)=5(-1)+3=-2.
\]""",
        }
    },
    "l3-counting-0280-nonempty-condition": {
        "steps": {
            3: r"""Each of the \(16\) subsets counted in Step 2 is a possible selection, so the number of selections is
\[
16.
\]"""
        }
    },
    "l3-algebra-0422-unsupported-maximum": {
        "span": {
            "start": 3,
            "end": 6,
            "text": r"""Step 3: The maximum occurs when \(x=y=50\).

Step 4: The resulting area is
\[
A=50\cdot50=2500.
\]
Therefore the maximum area is \(2500\) square feet.

""",
        }
    },
    "l4-counting-0187-binomial-coefficient": {
        "steps": {
            3: r"""Compute the number of ways to choose the 4 treasure islands:
\[
\binom{7}{4}=28.
\]""",
            5: r"""Multiply the number of arrangements by the probability of one arrangement:
\[
P(X=4)=28\cdot\frac{64}{78125}=\frac{1792}{78125}.
\]""",
        }
    },
    "l4-geometry-0261-inradius-formula": {
        "steps": {
            5: r"""The area and inradius satisfy \(K=r(AB+AC+BC)\). Since the perimeter is \(42\),
\[
r=\frac{K}{42}=\frac{21\sqrt{15}}{42}=\frac{\sqrt{15}}{2}.
\]"""
        }
    },
    "l4-intermediate-0298-negative-roots": {
        "steps": {
            2: r"""Use the divisors of the constant and leading coefficients:
\[
p\in\{1,2,7,14\},\qquad q\in\{1,7\}.
\]""",
            3: r"""The distinct candidates are
\[
1,2,7,14,\frac17,\frac27.
\]
There are six candidates.""",
            5: r"""Thus the requested number of possible rational zeros is \(6\).""",
        }
    },
    "l4-precalculus-0028-excluded-vertex": {
        "steps": {
            4: r"""Choose the root \(t=-1\), giving
\[
E=(-1,-1,-1)=D.
\]
This point satisfies the equal-distance equations, so take \(E=(-1,-1,-1)\)."""
        }
    },
    "l4-algebra-0442-correct-answer-invalid-bound": {
        "steps": {
            5: r"""For every real \(x\), \((x+4)^2\ge0\). Multiplying by \(-1\) gives
\[
-(x+4)^2\ge0.
\]
Hence \(f(x)=-(x+4)^2+28\ge28\).""",
            6: r"""Therefore the maximum is \(28\), attained at \(x=-4\).""",
        }
    },
    "l5-counting-0273-de-morgan": {
        "steps": {
            2: r"""Let \(W\) be Jean's winning event. By De Morgan's law,
\[
W^c=\{\text{product is even}\}\cup\{\text{product is not a multiple of }3\}.
\]""",
            3: r"""There are \(36-3\cdot3=27\) outcomes with even product.""",
            4: r"""There are \(4\cdot4=16\) outcomes whose product is not a multiple of \(3\), and \(12\) outcomes in the intersection of these two events.""",
            5: r"""Applying inclusion-exclusion gives
\[
|W^c|=27+16-12=31,
\]
so Jean has \(36-31=5\) winning outcomes.""",
            6: r"""The resulting probability is
\[
\frac{5}{36}.
\]""",
        }
    },
    "l5-intermediate-0308-missing-complex-branch": {
        "steps": {
            4: r"""From \(2y(x+1)=0\), take \(y=0\). Then \(x^2+2=0\), which has no real solution.""",
            5: r"""Therefore the only solution is \(z=0\), and the sum is \(0\).""",
        }
    },
    "l5-intermediate-0082-power-sum-identity": {
        "steps": {
            5: r"""Use the identity
\[
\sum_{i=1}^4z_i^2=\left(\sum_{i=1}^4z_i\right)^2+2\sum_{i<j}z_iz_j.
\]
Substitution gives
\[
\sum_{i=1}^4z_i^2=1^2+2(-1)=-1.
\]""",
            6: r"""Substitute this value into Step 3:
\[
\sum_{i=1}^4P(z_i)=-1-1+4=2.
\]""",
        }
    },
    "l5-precalculus-0488-negative-radius": {
        "steps": {
            9: r"""Of the two values, \(-6<6/23\), so the smaller radius is \(r=-6\)."""
        }
    },
    "l5-number-0456-correct-answer-invalid-exponents": {
        "steps": {
            3: r"""Because the exponent of \(3\) in \(1200\) is odd, \(n\) cannot contain a factor of \(3\), so \(b=0\). For the other primes,
\[
2a\le4\Rightarrow a\in\{0,1,2\},\qquad
2c\le2\Rightarrow c\in\{0,1\}.
\]""",
            4: r"""Thus all possible values are generated by choosing a power of \(2\) from \(1,2,4\), no factor of \(3\), and a power of \(5\) from \(1,5\). Their sum is
\[
(1+2+4)(1)(1+5)=7\cdot6=42.
\]""",
            5: r"""Therefore the requested sum is \(42\).""",
        }
    },
}


def cleaned_specs() -> tuple[dict[str, Any], ...]:
    specs = deepcopy(CASE_SPECS)
    for spec in specs:
        override = CLEAN_INJECTIONS.get(str(spec["case_id"]))
        if override is not None:
            if "steps" in override:
                spec["steps"] = override["steps"]
            if "span" in override:
                spec["span"] = override["span"]
        gold_override = HUMAN_GOLD_OVERRIDES.get(str(spec["case_id"]))
        if gold_override is not None:
            spec["expected"].update(gold_override)
    return specs


def main() -> int:
    sources = source_records()
    synthetic: list[dict[str, Any]] = []
    cases: list[dict[str, Any]] = []
    for spec in cleaned_specs():
        entry, source = sources[str(spec["sample_id"])]
        record = build_record(spec, entry, source)
        record["schema_version"] = "1.2-controlled-error"
        record["run_id"] = EXPERIMENT_ID
        record["inference_id"] = f"controlled-v1-1-{spec['case_id']}"
        record["response"]["raw"]["controlled_set_version"] = "v1.1"
        synthetic.append(record)
        cases.append(
            {
                "schema_version": "1.1",
                "experiment_id": EXPERIMENT_ID,
                "controlled_set_version": "v1.1",
                "case_id": spec["case_id"],
                "sample_id": spec["sample_id"],
                "difficulty": entry["difficulty"],
                "subject": entry["subject"],
                "solver_prompt_version": entry["prompt_version"],
                "source_inference_id": entry["inference_id"],
                "injected_inference_id": record["inference_id"],
                "injection": {
                    "description": spec["description"],
                    **{
                        key: spec["expected"][key]
                        for key in (
                            "first_error_step",
                            "first_error_status",
                            "first_error_importance",
                            "first_error_type",
                            "first_error_origin",
                        )
                    },
                },
                "expected": {
                    key: value
                    for key, value in spec["expected"].items()
                    if not key.startswith("first_error_")
                },
                "synthetic_solver_output": str(SYNTHETIC_OUTPUT.relative_to(ROOT)),
                "process_evaluator_status": "complete" if EVALUATION_ANALYSIS.is_file() else "not_run",
            }
        )

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    write_jsonl(SYNTHETIC_OUTPUT, synthetic)
    write_jsonl(CASES_PATH, cases)
    level_counts = Counter(row["difficulty"] for row in cases)
    manifest = {
        "schema_version": "1.1",
        "experiment": EXPERIMENT_ID,
        "controlled_set_version": "v1.1",
        "supersedes_for_future_evaluation": "process-evaluator-error-injection-16-v1",
        "records": len(cases),
        "unique_source_samples": len({row["sample_id"] for row in cases}),
        "levels": dict(sorted(level_counts.items())),
        "error_types": dict(sorted(Counter(row["injection"]["first_error_type"] for row in cases).items())),
        "correct_answer_invalid_process_cases": sum(row["expected"]["answer_correct"] for row in cases),
        "tracked_cases": str(CASES_PATH.relative_to(ROOT)),
        "synthetic_solver_output": str(SYNTHETIC_OUTPUT.relative_to(ROOT)),
        "answer_verification_output": str(ANSWER_OUTPUT.relative_to(ROOT)),
        "evaluation_output": str((ROOT / "outputs" / "process_evaluator_error_injection_16_v1_1_evaluations.jsonl").relative_to(ROOT)),
        "raw_evaluator_output": str((ROOT / "outputs" / "process_evaluator_error_injection_16_v1_1_responses.jsonl").relative_to(ROOT)),
        "stream_events_output": str((ROOT / "outputs" / "process_evaluator_error_injection_16_v1_1_stream_events.jsonl").relative_to(ROOT)),
        "process_evaluator_status": "complete" if EVALUATION_ANALYSIS.is_file() else "not_run",
        "process_evaluator_analysis": (
            str(EVALUATION_ANALYSIS.relative_to(ROOT))
            if EVALUATION_ANALYSIS.is_file()
            else None
        ),
        "human_review": (
            str(HUMAN_REVIEW.relative_to(ROOT)) if HUMAN_REVIEW.is_file() else None
        ),
    }
    MANIFEST_PATH.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
