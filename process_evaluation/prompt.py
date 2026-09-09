"""Versioned prompts for local and global visible-process evaluation."""

from __future__ import annotations

import json

from process_evaluation.schema import LocalStepResult
from process_evaluation.step_parser import ProcessStep


LOCAL_PROMPT_VERSION = "math-process-evaluator-v1.1"
GLOBAL_PROMPT_VERSION = "math-global-evaluator-v1.2"

TAXONOMY = """Error taxonomy and classification rules:

General rules

First locate the earliest primary error event relevant to the evaluation target.
Classify that event, not a later consequence such as a wrong final answer,
missing solution, or inconsistent downstream calculation. Use only visible
evidence; do not infer what the solver privately understood or intended.

An inherited error is not a new primary error. If a later step is locally valid
given an earlier erroneous value or premise, do not assign the downstream
symptom a new error category. For a step-level evaluation, classify only an
error introduced by the current step. For a complete-solution evaluation,
classify the earliest primary cause that makes the solution invalid or
incomplete. Choose exactly one category.

Category definitions and exclusive boundaries

1. problem_misinterpretation
   The visible solution represents the task, given information, requested
   object, or requested operation incorrectly.
   Do not use this when the task is represented correctly but a required
   restriction is not enforced later; use condition_omission.

2. condition_omission
   The solution fails to enforce a required admissibility or applicability
   condition, such as a domain, sign, boundary, nonzero, integrality,
   distinctness, or theorem-applicability condition.
   Do not use this for an unexamined alternative branch, candidate, root, or
   solution family; use case_omission.

3. case_omission
   The solution fails to examine a necessary branch, case, candidate, root, or
   solution family before discarding it or claiming completeness.
   Examining one branch is not itself an error. The error occurs when another
   necessary branch is discarded or a complete conclusion is made without it.
   If cases are lost because of an earlier illegal operation, classify that
   earlier operation as invalid_derivation.

4. concept_or_theorem_error
   The step explicitly states or directly relies on an incorrect general
   mathematical definition, theorem, identity, concept, or rule.
   Do not use this as a generic label for an isolated transition that fails to
   follow from its premises; use invalid_derivation.

5. invalid_derivation
   A specific logical or algebraic transition does not follow from the visible
   premises, although no incorrect general rule needs to be attributed to the
   solver.
   Do not use this for an isolated arithmetic, simplification, substitution,
   sign-copying, or transcription execution error; use calculation_error.

6. calculation_error
   The mathematical operation being carried out is valid, but its concrete
   arithmetic, algebraic execution, simplification, substitution, sign, or
   transcription is incorrect.
   Do not use this when the transition itself is invalid in principle.

7. insufficient_justification
   No definite false statement, illegal transition, or identifiable omitted
   condition or case has been established, but essential visible support is
   missing.
   Use this primarily with status=insufficient. If a specific invalid step,
   omitted case, or omitted condition is identifiable, use that more specific
   category.

8. answer_extraction_or_format_error
   The preceding visible reasoning is correct, complete, and sufficient, but
   the final answer is copied, selected, extracted, or formatted incorrectly.
   Use this only when no earlier substantive mathematical error explains the
   final-answer problem.

9. other
   A clear primary process error exists but does not reasonably fit any
   category above. Use this only after the defined categories are considered.

Ambiguity-resolution rules

- Classify the earliest causal failure, not its downstream symptom.
- Missing an alternative case or candidate is case_omission; failing to apply
  an admissibility restriction is condition_omission.
- An explicitly incorrect general rule is concept_or_theorem_error; an invalid
  instance-level transition is invalid_derivation; a valid operation executed
  incorrectly is calculation_error.
- A specifically identifiable missing case or condition is not merely
  insufficient_justification.
- If an illegal transformation causes solutions to be lost, the transformation
  is the primary invalid_derivation; the later missing solutions are a
  consequence.
- A final-answer error is answer_extraction_or_format_error only when the
  preceding substantive reasoning is already valid and sufficient.

Diagnostic classification questions

After locating the earliest primary error event, use the following questions to
assign one label. They classify the already-located event; they are not an
instruction to search the solution in this order.

A. Does the event represent the task, givens, requested object, or requested
   operation incorrectly? -> problem_misinterpretation
B. Does it fail to enforce an admissibility or applicability condition?
   -> condition_omission
C. Does it discard or fail to cover a necessary branch, candidate, root, or
   solution family? -> case_omission
D. Does it state or directly rely on an incorrect general mathematical rule,
   definition, theorem, identity, or concept? -> concept_or_theorem_error
E. Is it a specific logical or algebraic transition that does not follow?
   -> invalid_derivation
F. Is the operation valid but its concrete execution incorrect?
   -> calculation_error
G. Is no definite error identifiable while essential visible support is
   missing? -> insufficient_justification
H. Is the substantive reasoning already correct and sufficient, with the only
   error in final-answer extraction, selection, copying, or required format?
   -> answer_extraction_or_format_error
I. Does a clear primary error remain outside all defined categories? -> other"""

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
