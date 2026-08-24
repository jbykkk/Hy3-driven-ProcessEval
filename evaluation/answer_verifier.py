"""Verify predicted final answers without modifying inference evidence."""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from typing import Any

from math_verify import parse, verify


VERIFIER_VERSION = "answer-verifier-v1"


@dataclass(frozen=True)
class VerificationResult:
    verdict: str
    exact_match: bool
    math_equivalent: bool | None
    format_mismatch_but_equivalent: bool
    manual_review_recommended: bool
    gold_extracted: list[str]
    prediction_extracted: list[str]
    error: str | None

    def as_dict(self) -> dict[str, Any]:
        return {"verifier_version": VERIFIER_VERSION, **asdict(self)}


def _strip_math_delimiters(value: str) -> str:
    value = value.strip()
    if value.startswith("$") and value.endswith("$") and len(value) >= 2:
        return value[1:-1].strip()
    return value


def _math_text(value: str) -> str:
    return f"${_strip_math_delimiters(value)}$"


def _serialized(expressions: list[object]) -> list[str]:
    return [str(expression) for expression in expressions]


def _needs_manual_review(reference: str, prediction: str) -> bool:
    """Flag answer shapes whose ordering or semantics need dataset-aware handling."""

    combined = f"{reference}\n{prediction}"
    structural_text = combined.replace(r"{,}", "").replace(r",\!", "")
    has_collection_syntax = any(
        marker in structural_text
        for marker in (r"\{", r"\}", r"\begin{", r"\text{or}", r"\text{and}")
    )
    comma_outside_thousands = bool(
        re.search(r",(?!\d{3}(?:\D|$))", structural_text)
    )
    return has_collection_syntax or comma_outside_thousands


def verify_answer(reference: str, prediction: str | None) -> VerificationResult:
    """Compare one extracted prediction with a benchmark reference answer."""

    if prediction is None or not prediction.strip():
        return VerificationResult(
            verdict="unverified",
            exact_match=False,
            math_equivalent=None,
            format_mismatch_but_equivalent=False,
            manual_review_recommended=True,
            gold_extracted=[],
            prediction_extracted=[],
            error="missing_prediction",
        )

    normalized_reference = _strip_math_delimiters(reference)
    normalized_prediction = _strip_math_delimiters(prediction)
    exact_match = normalized_reference == normalized_prediction
    manual_review = _needs_manual_review(reference, prediction)

    try:
        gold = parse(_math_text(reference))
        target = parse(_math_text(prediction))
        if not gold or not target:
            return VerificationResult(
                verdict="unverified",
                exact_match=exact_match,
                math_equivalent=None,
                format_mismatch_but_equivalent=False,
                manual_review_recommended=True,
                gold_extracted=_serialized(gold),
                prediction_extracted=_serialized(target),
                error="math_expression_not_extracted",
            )
        equivalent = bool(verify(gold, target))
    except Exception as error:  # verifier failures must become auditable records
        return VerificationResult(
            verdict="unverified",
            exact_match=exact_match,
            math_equivalent=None,
            format_mismatch_but_equivalent=False,
            manual_review_recommended=True,
            gold_extracted=[],
            prediction_extracted=[],
            error=f"{type(error).__name__}: {error}",
        )

    return VerificationResult(
        verdict="correct" if equivalent else "incorrect",
        exact_match=exact_match,
        math_equivalent=equivalent,
        format_mismatch_but_equivalent=equivalent and not exact_match,
        manual_review_recommended=manual_review,
        gold_extracted=_serialized(gold),
        prediction_extracted=_serialized(target),
        error=None,
    )
