from __future__ import annotations

import unittest
from collections import Counter

from scripts.build_process_evaluator_error_injection_16 import CASE_SPECS, inject_content
from scripts.build_process_evaluator_error_injection_16_v1_1 import (
    CLEAN_INJECTIONS,
    HUMAN_GOLD_OVERRIDES,
    cleaned_specs,
)
from scripts.build_process_evaluator_error_injection_16_v1_2_labels import (
    ANNOTATION_VERSION,
    SOURCE_CASES,
    TYPE_REVISIONS,
    build_cases,
    load_jsonl,
)
from scripts.analyze_process_evaluator_error_injection_16_v1_1 import (
    SELF_REVEAL_PATTERNS,
)


class ControlledError16Tests(unittest.TestCase):
    def test_case_plan_has_required_levels_types_and_answer_relations(self) -> None:
        levels = Counter(spec["case_id"].split("-")[0] for spec in CASE_SPECS)
        self.assertEqual(len(CASE_SPECS), 16)
        self.assertEqual(len({spec["sample_id"] for spec in CASE_SPECS}), 16)
        self.assertEqual(
            {spec["expected"]["first_error_type"] for spec in CASE_SPECS},
            {
                "problem_misinterpretation",
                "concept_or_theorem_error",
                "invalid_derivation",
                "calculation_error",
                "condition_omission",
                "case_omission",
                "insufficient_justification",
                "answer_extraction_or_format_error",
            },
        )
        self.assertEqual(
            sum(spec["expected"]["answer_correct"] for spec in CASE_SPECS), 3
        )
        self.assertEqual(levels, Counter({"l1": 2, "l2": 2, "l3": 2, "l4": 5, "l5": 5}))

    def test_inject_content_replaces_step_and_final_answer(self) -> None:
        source = "Step 1: valid\n\nStep 2: valid\n\nFinal Answer: \\(\\boxed{1}\\)"
        spec = {"case_id": "test", "steps": {2: "invalid"}, "final_answer": r"\boxed{2}"}
        injected = inject_content(source, spec)
        self.assertIn("Step 1: valid", injected)
        self.assertIn("Step 2: invalid", injected)
        self.assertTrue(injected.endswith(r"Final Answer: \boxed{2}"))

    def test_v1_1_covers_changed_cases_and_has_no_self_revealing_phrases(self) -> None:
        self.assertEqual(len(CLEAN_INJECTIONS), 15)
        for spec in cleaned_specs():
            visible_injection = "\n".join(
                [str(spec.get("span", {}).get("text", ""))]
                + [str(body) for body in spec["steps"].values()]
            )
            hits = [
                match.group(0)
                for _, pattern in SELF_REVEAL_PATTERNS
                for match in pattern.finditer(visible_injection)
            ]
            self.assertEqual(hits, [], spec["case_id"])

    def test_v1_1_human_gold_revision_does_not_modify_v1(self) -> None:
        case_id = "l5-intermediate-0308-missing-complex-branch"
        v1 = next(spec for spec in CASE_SPECS if spec["case_id"] == case_id)
        v1_1 = next(spec for spec in cleaned_specs() if spec["case_id"] == case_id)

        self.assertEqual(HUMAN_GOLD_OVERRIDES[case_id]["first_error_step"], 5)
        self.assertEqual(v1["expected"]["first_error_step"], 4)
        self.assertTrue(v1["expected"]["process_complete"])
        self.assertEqual(v1_1["expected"]["first_error_step"], 5)
        self.assertFalse(v1_1["expected"]["process_complete"])

    def test_v1_2_taxonomy_review_relabels_only_three_types(self) -> None:
        v1_1_cases = load_jsonl(SOURCE_CASES)
        v1_2_cases = build_cases(v1_1_cases)
        old_by_id = {case["case_id"]: case for case in v1_1_cases}
        new_by_id = {case["case_id"]: case for case in v1_2_cases}

        self.assertEqual(len(v1_2_cases), 16)
        self.assertEqual(len(TYPE_REVISIONS), 3)
        self.assertTrue(
            all(
                case["annotation_version"] == ANNOTATION_VERSION
                for case in v1_2_cases
            )
        )
        changed = {
            case_id
            for case_id in new_by_id
            if old_by_id[case_id]["injection"]["first_error_type"]
            != new_by_id[case_id]["injection"]["first_error_type"]
        }
        self.assertEqual(changed, set(TYPE_REVISIONS))
        for case_id, (old_type, new_type) in TYPE_REVISIONS.items():
            self.assertEqual(
                old_by_id[case_id]["injection"]["first_error_type"], old_type
            )
            self.assertEqual(
                new_by_id[case_id]["injection"]["first_error_type"], new_type
            )

        self.assertEqual(
            new_by_id["l4-algebra-0442-correct-answer-invalid-bound"]["injection"][
                "first_error_type"
            ],
            "invalid_derivation",
        )
        self.assertEqual(
            new_by_id["l5-precalculus-0488-negative-radius"]["injection"][
                "first_error_type"
            ],
            "condition_omission",
        )


if __name__ == "__main__":
    unittest.main()
