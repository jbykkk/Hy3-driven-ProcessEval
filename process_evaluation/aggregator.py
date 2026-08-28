"""Deterministically combine process evidence without calling an LLM."""

from __future__ import annotations

from typing import Any

from process_evaluation.schema import GlobalEvaluationResult, LocalStepResult
from process_evaluation.step_parser import StepParseResult


AGGREGATOR_VERSION = "process-evaluation-aggregator-v1"


def locate_local_first_error(
    results: list[LocalStepResult],
) -> tuple[int | None, str | None]:
    """Conservatively locate the first newly introduced fatal error or critical gap."""

    for result in results:
        introduced_here = result.error_origin in {"current_step", "uncertain"}
        if result.status == "invalid" and introduced_here:
            return result.step_id, result.error_type
        if (
            result.status == "insufficient"
            and result.importance == "high"
            and introduced_here
        ):
            return result.step_id, result.error_type
    return None, None


def _answer_process_relation(
    answer_correct: bool | None,
    process_correct: bool | None,
) -> str:
    if answer_correct is None or process_correct is None:
        return "uncertain"
    if answer_correct and process_correct:
        return "correct_answer_valid_process"
    if answer_correct and not process_correct:
        return "correct_answer_invalid_process"
    if not answer_correct and process_correct:
        return "wrong_answer_valid_or_supported_process"
    return "wrong_answer_invalid_process"


def aggregate_process_evaluation(
    *,
    step_parse: StepParseResult,
    local_results: list[LocalStepResult],
    global_result: GlobalEvaluationResult | None,
    answer_correct: bool | None,
    evaluation_errors: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Apply explicit conservative rules and preserve local/global disagreement."""

    errors = evaluation_errors or []
    local_step, local_type = locate_local_first_error(local_results)
    override = global_result.first_error_step_override if global_result else None
    override_type = global_result.global_error_type if global_result else None
    needs_review = bool(errors) or step_parse.parse_status != "success"

    if local_step is not None and override is not None and local_step != override:
        first_error_step = None
        first_error_type = None
        needs_review = True
    elif local_step is not None:
        first_error_step = local_step
        first_error_type = local_type
    else:
        first_error_step = override
        first_error_type = override_type if override is not None else None

    uncertain_local = any(result.status == "uncertain" for result in local_results)
    inherited_without_origin = any(
        result.error_origin == "inherited" for result in local_results
    ) and not any(
        result.status == "invalid" and result.error_origin == "current_step"
        for result in local_results
    )
    local_invalid = any(
        result.status == "invalid" and result.error_origin != "inherited"
        for result in local_results
    )
    critical_insufficient = any(
        result.status == "insufficient" and result.importance == "high"
        for result in local_results
    )
    material_insufficient = any(
        result.status == "insufficient" and result.importance in {"medium", "high"}
        for result in local_results
    )

    process_correct: bool | None
    if errors or step_parse.parse_status == "failed" or global_result is None:
        process_correct = None
        needs_review = True
    elif uncertain_local or global_result.global_status == "uncertain" or inherited_without_origin:
        process_correct = None
        needs_review = True
    elif local_invalid:
        process_correct = False
        needs_review = needs_review or global_result.global_status == "valid"
    elif (
        global_result.global_status == "invalid"
        or not global_result.process_complete
        or not global_result.final_answer_supported
    ):
        process_correct = False
    elif global_result.global_status == "insufficient":
        process_correct = False
    elif critical_insufficient or material_insufficient:
        process_correct = None
        needs_review = True
    elif global_result.global_status == "valid":
        process_correct = True
    else:
        process_correct = None
        needs_review = True

    if global_result is not None and global_result.global_status in {"invalid", "insufficient"}:
        if first_error_step is None:
            needs_review = True

    return {
        "aggregator_version": AGGREGATOR_VERSION,
        "local_first_error_step": local_step,
        "local_first_error_type": local_type,
        "global_first_error_step_override": override,
        "first_error_step": first_error_step,
        "first_error_type": first_error_type,
        "process_correct": process_correct,
        "answer_process_relation": _answer_process_relation(answer_correct, process_correct),
        "needs_review": needs_review,
    }
