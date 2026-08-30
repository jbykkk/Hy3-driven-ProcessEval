"""Build v1.2 human labels from the frozen v1.1 visible-solution cases."""

from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
SOURCE_CASES = (
    ROOT / "experiments" / "process_evaluator_error_injection_16_v1_1" / "cases.jsonl"
)
OUTPUT_DIR = ROOT / "experiments" / "process_evaluator_error_injection_16_v1_2"
OUTPUT_CASES = OUTPUT_DIR / "cases.jsonl"
EXPERIMENT_ID = "process-evaluator-error-injection-16-v1.2"
ANNOTATION_VERSION = "error-taxonomy-v1.2-human-reviewed"


TYPE_REVISIONS: dict[str, tuple[str, str]] = {
    "l5-counting-0273-de-morgan": (
        "concept_or_theorem_error",
        "invalid_derivation",
    ),
    "l5-intermediate-0082-power-sum-identity": (
        "invalid_derivation",
        "concept_or_theorem_error",
    ),
    "l5-number-0456-correct-answer-invalid-exponents": (
        "invalid_derivation",
        "concept_or_theorem_error",
    ),
}


DESCRIPTION_REVISIONS = {
    "l5-number-0456-correct-answer-invalid-exponents": (
        "Use the incorrect general rule that an odd exponent in the factorization "
        "prevents that prime from appearing in n; the conclusion b=0 happens to "
        "be correct for exponent 1."
    )
}


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def build_cases(source_cases: list[dict[str, Any]]) -> list[dict[str, Any]]:
    cases = deepcopy(source_cases)
    for case in cases:
        case_id = str(case["case_id"])
        case["schema_version"] = "1.2"
        case["experiment_id"] = EXPERIMENT_ID
        case["controlled_set_version"] = "v1.1-visible-v1.2-taxonomy"
        case["annotation_version"] = ANNOTATION_VERSION
        case["taxonomy_review"] = (
            "experiments/process_evaluator_error_injection_16_v1_2/"
            "taxonomy_review.json"
        )
        revision = TYPE_REVISIONS.get(case_id)
        if revision is not None:
            old_type, new_type = revision
            actual_type = str(case["injection"]["first_error_type"])
            if actual_type != old_type:
                raise ValueError(
                    f"Unexpected source type for {case_id}: {actual_type} != {old_type}"
                )
            case["injection"]["first_error_type"] = new_type
        if case_id in DESCRIPTION_REVISIONS:
            case["injection"]["description"] = DESCRIPTION_REVISIONS[case_id]
    return cases


def main() -> int:
    cases = build_cases(load_jsonl(SOURCE_CASES))
    if len(cases) != 16:
        raise ValueError(f"Expected 16 cases, found {len(cases)}")
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    with OUTPUT_CASES.open("w", encoding="utf-8") as handle:
        for case in cases:
            handle.write(json.dumps(case, ensure_ascii=False, separators=(",", ":")) + "\n")
    print(
        json.dumps(
            {
                "experiment": EXPERIMENT_ID,
                "annotation_version": ANNOTATION_VERSION,
                "records": len(cases),
                "type_revisions": len(TYPE_REVISIONS),
                "output": str(OUTPUT_CASES.relative_to(ROOT)),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
