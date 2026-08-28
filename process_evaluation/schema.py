"""Strict schemas for visible local and global Hy3 evaluator responses."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from typing import Any


LOCAL_STATUSES = frozenset({"valid", "invalid", "insufficient", "uncertain"})
IMPORTANCE_LEVELS = frozenset({"low", "medium", "high"})
ERROR_ORIGINS = frozenset({"none", "current_step", "inherited", "uncertain"})
ERROR_TYPES = frozenset(
    {
        "problem_misinterpretation",
        "concept_or_theorem_error",
        "invalid_derivation",
        "calculation_error",
        "condition_omission",
        "case_omission",
        "insufficient_justification",
        "answer_extraction_or_format_error",
        "other",
    }
)


class EvaluatorSchemaError(ValueError):
    """Raised when visible evaluator JSON does not exactly satisfy the v1 schema."""


@dataclass(frozen=True)
class LocalStepResult:
    step_id: int
    status: str
    importance: str
    purpose: str
    error_type: str | None
    error_origin: str
    evidence: str

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class GlobalEvaluationResult:
    global_status: str
    process_complete: bool
    final_answer_supported: bool
    global_error_type: str | None
    first_error_step_override: int | None
    evidence: str

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def _load_object(content: str) -> dict[str, Any]:
    try:
        value = json.loads(content)
    except json.JSONDecodeError as error:
        raise EvaluatorSchemaError(f"invalid_json: {error}") from error
    if not isinstance(value, dict):
        raise EvaluatorSchemaError("top_level_value_must_be_object")
    return value


def _require_exact_fields(value: dict[str, Any], expected: set[str]) -> None:
    actual = set(value)
    if actual != expected:
        missing = sorted(expected - actual)
        extra = sorted(actual - expected)
        raise EvaluatorSchemaError(f"schema_fields_mismatch: missing={missing}, extra={extra}")


def _require_nonempty_string(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise EvaluatorSchemaError(f"{field}_must_be_nonempty_string")
    return value


def _optional_error_type(value: Any, field: str) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str) or value not in ERROR_TYPES:
        raise EvaluatorSchemaError(f"{field}_has_invalid_value")
    return value


def parse_local_result(content: str, *, expected_step_id: int) -> LocalStepResult:
    value = _load_object(content)
    _require_exact_fields(
        value,
        {
            "step_id",
            "status",
            "importance",
            "purpose",
            "error_type",
            "error_origin",
            "evidence",
        },
    )
    if type(value["step_id"]) is not int or value["step_id"] != expected_step_id:
        raise EvaluatorSchemaError("step_id_does_not_match_requested_step")
    status = value["status"]
    if not isinstance(status, str) or status not in LOCAL_STATUSES:
        raise EvaluatorSchemaError("status_has_invalid_value")
    importance = value["importance"]
    if not isinstance(importance, str) or importance not in IMPORTANCE_LEVELS:
        raise EvaluatorSchemaError("importance_has_invalid_value")
    error_origin = value["error_origin"]
    if not isinstance(error_origin, str) or error_origin not in ERROR_ORIGINS:
        raise EvaluatorSchemaError("error_origin_has_invalid_value")
    error_type = _optional_error_type(value["error_type"], "error_type")
    if status in {"invalid", "insufficient"} and error_type is None:
        raise EvaluatorSchemaError("invalid_or_insufficient_requires_error_type")
    if status in {"invalid", "insufficient"} and error_origin == "none":
        raise EvaluatorSchemaError("invalid_or_insufficient_requires_error_origin")
    if status == "valid" and error_type is not None:
        raise EvaluatorSchemaError("valid_status_requires_null_error_type")
    if status == "valid" and error_origin not in {"none", "inherited"}:
        raise EvaluatorSchemaError("valid_status_has_inconsistent_error_origin")
    return LocalStepResult(
        step_id=value["step_id"],
        status=status,
        importance=importance,
        purpose=_require_nonempty_string(value["purpose"], "purpose"),
        error_type=error_type,
        error_origin=error_origin,
        evidence=_require_nonempty_string(value["evidence"], "evidence"),
    )


def parse_global_result(
    content: str,
    *,
    allowed_step_ids: set[int],
) -> GlobalEvaluationResult:
    value = _load_object(content)
    _require_exact_fields(
        value,
        {
            "global_status",
            "process_complete",
            "final_answer_supported",
            "global_error_type",
            "first_error_step_override",
            "evidence",
        },
    )
    status = value["global_status"]
    if not isinstance(status, str) or status not in LOCAL_STATUSES:
        raise EvaluatorSchemaError("global_status_has_invalid_value")
    if type(value["process_complete"]) is not bool:
        raise EvaluatorSchemaError("process_complete_must_be_boolean")
    if type(value["final_answer_supported"]) is not bool:
        raise EvaluatorSchemaError("final_answer_supported_must_be_boolean")
    if value["final_answer_supported"] and (
        status != "valid" or not value["process_complete"]
    ):
        raise EvaluatorSchemaError(
            "supported_final_answer_requires_valid_complete_process"
        )
    if status == "valid" and (
        not value["process_complete"] or not value["final_answer_supported"]
    ):
        raise EvaluatorSchemaError(
            "valid_global_status_requires_complete_supported_process"
        )
    error_type = _optional_error_type(value["global_error_type"], "global_error_type")
    if status in {"invalid", "insufficient"} and error_type is None:
        raise EvaluatorSchemaError("invalid_or_insufficient_global_requires_error_type")
    if status == "valid" and error_type is not None:
        raise EvaluatorSchemaError("valid_global_status_requires_null_error_type")
    override = value["first_error_step_override"]
    if override is not None and (type(override) is not int or override not in allowed_step_ids):
        raise EvaluatorSchemaError("first_error_step_override_is_not_a_known_step")
    return GlobalEvaluationResult(
        global_status=status,
        process_complete=value["process_complete"],
        final_answer_supported=value["final_answer_supported"],
        global_error_type=error_type,
        first_error_step_override=override,
        evidence=_require_nonempty_string(value["evidence"], "evidence"),
    )
