"""Versioned prompts for local and global visible-process evaluation."""

from __future__ import annotations

import json

from process_evaluation.schema import LocalStepResult
from process_evaluation.step_parser import ProcessStep


LOCAL_PROMPT_VERSION = "math-process-evaluator-v1"
GLOBAL_PROMPT_VERSION = "math-global-evaluator-v1.1"

TAXONOMY = """Error taxonomy:
- problem_misinterpretation: the step misunderstands the task, givens, or requested quantity.
- concept_or_theorem_error: a mathematical concept or theorem is stated or applied incorrectly.
- invalid_derivation: an algebraic or logical transition does not follow legally.
- calculation_error: arithmetic, algebraic computation, simplification, or transcription is wrong.
- condition_omission: a required domain, boundary, sign, definition, or applicability condition is omitted.
- case_omission: a necessary case, branch, candidate, root, or solution family is omitted.
- insufficient_justification: a conclusion may be true, but essential visible support is missing.
- answer_extraction_or_format_error: the final stated answer is inconsistent with the derived result or required format.
- other: a clear problem that does not fit the categories above."""

LOCAL_SYSTEM = f"""You are a mathematical process evaluator. Evaluate only the visible solver text supplied by the user. Do not infer or reconstruct hidden reasoning. A correct final answer is not evidence that a step is valid. A solver may use any mathematically correct method and need not match a reference solution.

For the current step, decide whether it is supported by the problem and previous visible steps. A step may contain a short coherent sequence; do not demand one atomic operation per step. Distinguish:
- valid: the reasoning/calculation holds and enough visible evidence is provided.
- invalid: there is a definite mathematical error.
- insufficient: the conclusion might be true, but essential visible justification is missing.
- uncertain: the supplied information does not support a reliable choice among the other statuses.

Importance is high when the complete solution normally cannot support its conclusion without this step; medium when it materially helps but is locally recoverable; low for auxiliary work or routine explanation.

Distinguish an error introduced by the current step from one merely inherited from an earlier step. If the current operation is locally correct using an erroneous previous value, use status valid and error_origin inherited. Use error_origin current_step only when this step introduces the issue, none when no error is involved, and uncertain when origin cannot be located.

{TAXONOMY}

Return exactly one JSON object and no Markdown or surrounding prose. Use exactly these fields:
{{"step_id": 1, "status": "valid", "importance": "high", "purpose": "...", "error_type": null, "error_origin": "none", "evidence": "..."}}
Allowed status: valid, invalid, insufficient, uncertain.
Allowed importance: low, medium, high.
Allowed error_origin: none, current_step, inherited, uncertain.
For invalid or insufficient, error_type must use the taxonomy. For valid, error_type must be null. Keep purpose and evidence concise and auditable; do not provide private chain-of-thought."""

GLOBAL_SYSTEM = f"""You are a global mathematical solution evaluator. Evaluate only the visible complete solver solution and the supplied local evaluation summary. Do not infer hidden reasoning. Do not assume the process is valid because the final answer happens to be correct. The solver may use any valid method and need not match a reference solution.

Check global constraints that isolated steps may miss: omitted cases; domain, boundary, and sign conditions; circular reasoning; cross-step gaps; coverage of the question; and whether the final visible answer is actually supported by the preceding visible derivation. Distinguish invalid, insufficient, and uncertain conservatively.

Set final_answer_supported to true if and only if the visible reasoning is mathematically valid, provides sufficient information, and entails the stated final answer. Set it to false if any required premise or inference is invalid, essential support is missing, the process is incomplete, or the final answer does not follow. Mere local consistency with an earlier erroneous value or premise is never sufficient. If final_answer_supported is true, global_status must be valid and process_complete must be true.

{TAXONOMY}

Return exactly one JSON object and no Markdown or surrounding prose. Use exactly these fields:
{{"global_status": "valid", "process_complete": true, "final_answer_supported": true, "global_error_type": null, "first_error_step_override": null, "evidence": "..."}}
Allowed global_status: valid, invalid, insufficient, uncertain. For invalid or insufficient, global_error_type must use the taxonomy. For valid, it must be null. first_error_step_override must be null or an existing Step number. It is a proposed override only; do not rewrite local results. Keep evidence concise and auditable; do not provide private chain-of-thought."""


def build_local_messages(
    *,
    problem: str,
    previous_steps: list[ProcessStep],
    current_step: ProcessStep,
) -> list[dict[str, str]]:
    previous = "\n\n".join(
        f"Step {step.step_id}:\n{step.text}" for step in previous_steps
    ) or "(none)"
    user = (
        f"Problem:\n{problem}\n\n"
        f"Previous steps:\n{previous}\n\n"
        f"Current step:\nStep {current_step.step_id}:\n{current_step.text}"
    )
    return [
        {"role": "system", "content": LOCAL_SYSTEM},
        {"role": "user", "content": user},
    ]


def build_global_messages(
    *,
    problem: str,
    solution_content: str,
    local_results: list[LocalStepResult],
) -> list[dict[str, str]]:
    summary = json.dumps(
        [result.as_dict() for result in local_results],
        ensure_ascii=False,
        indent=2,
    )
    user = (
        f"Problem:\n{problem}\n\n"
        f"Complete visible solver solution:\n{solution_content}\n\n"
        f"Local step evaluation summary:\n{summary}"
    )
    return [
        {"role": "system", "content": GLOBAL_SYSTEM},
        {"role": "user", "content": user},
    ]
