"""Deterministically segment visible solver responses for process evaluation."""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from typing import Any


STEP_PARSER_VERSION = "process-step-parser-v1"
STEP_HEADER_PATTERN = re.compile(
    r"(?im)^[ \t]*(?:\*\*)?Step[ \t]+(?P<number>\d+)"
    r"(?:[ \t]*\[[^\]\n]*\])?[ \t]*(?:\*\*)?[ \t]*:?"
    r"[ \t]*(?:\*\*)?[ \t]*"
)
FINAL_ANSWER_PATTERN = re.compile(
    r"(?im)^[ \t]*(?:\*\*)?(?:Final[ \t]+Answer|Answer)"
    r"[ \t]*(?:\*\*)?[ \t]*:[ \t]*(?:\*\*)?[ \t]*"
)


@dataclass(frozen=True)
class ProcessStep:
    step_id: int
    text: str


@dataclass(frozen=True)
class StructureIssue:
    code: str
    message: str
    step_id: int | None = None


@dataclass(frozen=True)
class StepParseResult:
    parse_status: str
    original_content: str
    steps: list[ProcessStep]
    final_answer_text: str | None
    final_answer_source: str | None
    structure_issues: list[StructureIssue]

    def as_dict(self) -> dict[str, Any]:
        return {
            "parser_version": STEP_PARSER_VERSION,
            "parse_status": self.parse_status,
            "original_content": self.original_content,
            "steps": [asdict(step) for step in self.steps],
            "final_answer_text": self.final_answer_text,
            "final_answer_source": self.final_answer_source,
            "structure_issues": [asdict(issue) for issue in self.structure_issues],
        }


def _last_boxed_span(text: str) -> str | None:
    """Return the last complete raw ``\\boxed{...}`` span without rewriting it."""

    spans: list[str] = []
    cursor = 0
    while (marker := text.find(r"\boxed", cursor)) >= 0:
        brace = text.find("{", marker + len(r"\boxed"))
        if brace < 0:
            break
        depth = 0
        for end in range(brace, len(text)):
            if text[end] == "{":
                depth += 1
            elif text[end] == "}":
                depth -= 1
                if depth == 0:
                    spans.append(text[marker : end + 1])
                    cursor = end + 1
                    break
        else:
            break
    return spans[-1] if spans else None


def parse_process_steps(content: str) -> StepParseResult:
    """Split numbered steps while preserving their exact body text and all issues."""

    step_matches = list(STEP_HEADER_PATTERN.finditer(content))
    answer_matches = list(FINAL_ANSWER_PATTERN.finditer(content))
    explicit_answer = answer_matches[-1] if answer_matches else None
    steps: list[ProcessStep] = []
    issues: list[StructureIssue] = []

    for index, match in enumerate(step_matches):
        end = step_matches[index + 1].start() if index + 1 < len(step_matches) else len(content)
        answer_after_header = next(
            (
                answer
                for answer in answer_matches
                if match.end() <= answer.start() < end
            ),
            None,
        )
        if answer_after_header is not None:
            end = answer_after_header.start()
        step_id = int(match.group("number"))
        text = content[match.end() : end].strip()
        steps.append(ProcessStep(step_id=step_id, text=text))
        if not text:
            issues.append(
                StructureIssue(
                    code="empty_step_content",
                    message=f"Step {step_id} has no content.",
                    step_id=step_id,
                )
            )

    if not steps:
        issues.append(
            StructureIssue(
                code="no_numbered_steps",
                message="No explicitly numbered Step entries were detected.",
            )
        )
    else:
        numbers = [step.step_id for step in steps]
        duplicates = sorted({number for number in numbers if numbers.count(number) > 1})
        for number in duplicates:
            issues.append(
                StructureIssue(
                    code="duplicate_step_number",
                    message=f"Step number {number} occurs more than once.",
                    step_id=number,
                )
            )
        if numbers != list(range(1, len(numbers) + 1)):
            issues.append(
                StructureIssue(
                    code="non_contiguous_step_numbers",
                    message=(
                        "Step numbers are not the contiguous sequence 1..N: "
                        f"{numbers}."
                    ),
                )
            )

    if explicit_answer is not None:
        final_answer_text = content[explicit_answer.end() :].strip()
        final_answer_source = "explicit_label"
        if not final_answer_text:
            issues.append(
                StructureIssue(
                    code="empty_final_answer",
                    message="A final-answer label is present but has no content.",
                )
            )
    else:
        final_answer_text = _last_boxed_span(content)
        final_answer_source = "boxed_expression" if final_answer_text else None
        if final_answer_text is None:
            issues.append(
                StructureIssue(
                    code="final_answer_missing",
                    message="No explicit final answer or complete boxed expression was detected.",
                )
            )

    parse_status = "failed" if not steps else ("issues" if issues else "success")
    return StepParseResult(
        parse_status=parse_status,
        original_content=content,
        steps=steps,
        final_answer_text=final_answer_text,
        final_answer_source=final_answer_source,
        structure_issues=issues,
    )
