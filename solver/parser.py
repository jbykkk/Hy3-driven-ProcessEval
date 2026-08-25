"""Parse useful fields without modifying the raw Hy3 response."""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from typing import Any


STEP_PATTERN = re.compile(
    r"(?im)^\s*(?:\*\*)?Step\s+(\d+)\s*:?\s*(?:\*\*)?\s*"
)
PARSER_VERSION = "solution-parser-v1.3"


@dataclass(frozen=True)
class ParsedStep:
    number: int
    text: str


@dataclass(frozen=True)
class ParsedSolution:
    steps: list[ParsedStep]
    final_answer: str | None
    warnings: list[str]

    def as_dict(self) -> dict[str, Any]:
        return {
            "parser_version": PARSER_VERSION,
            "steps": [asdict(step) for step in self.steps],
            "final_answer": self.final_answer,
            "warnings": self.warnings,
        }


def _extract_last_boxed(text: str) -> str | None:
    answers: list[str] = []
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
                    answers.append(text[brace + 1 : end].strip())
                    cursor = end + 1
                    break
        else:
            break
    return answers[-1] if answers else None


def _extract_final_answer(text: str) -> str | None:
    boxed = _extract_last_boxed(text)
    if boxed:
        return boxed
    matches = re.findall(
        r"(?im)^\s*(?:\*\*)?(?:Final\s+Answer|Answer)\s*(?::\*\*|\*\*:|:)\s*(.+?)\s*$",
        text,
    )
    if not matches:
        concluding_lines = re.findall(
            r"(?im)^\s*(?:Therefore|Thus|Hence),?\s+(.+?)\s*$",
            text,
        )
        if not concluding_lines:
            return None
        matches = [concluding_lines[-1]]

    candidate = matches[-1].strip()
    inline_math = re.findall(
        r"\$([^$]+)\$|\\\((.+?)\\\)|\\\[(.+?)\\\]",
        candidate,
    )
    if inline_math:
        candidate = next(part for part in inline_math[-1] if part).strip()
    else:
        bold_spans = re.findall(r"\*\*(.+?)\*\*", candidate)
        if bold_spans:
            candidate = bold_spans[0].strip()

    numeric_tokens = re.findall(r"(?<![\w.])-?\d[\d,]*(?:\.\d+)?(?![\w.])", candidate)
    if len(numeric_tokens) == 1:
        return numeric_tokens[0].replace(",", "")
    return candidate.strip("$* ")


def _extract_stated_answer_from_last_step(step: ParsedStep) -> str | None:
    """Prefer a clearly marked answer inside the final numbered step."""

    explicit_statement = re.search(
        r"(?i)\bstate\s+(?:the\s+)?final\s+answer\b", step.text
    )
    answer_context = re.search(
        r"(?i)\b(?:answer|final|total|maximum|minimum)\b", step.text
    )
    if not explicit_statement and not answer_context:
        return None
    boxed = _extract_last_boxed(step.text)
    if boxed:
        return boxed

    body = step.text
    if explicit_statement:
        body = re.sub(
            r"(?is)^.*?\bstate\s+(?:the\s+)?final\s+answer(?:\s+with\s+units)?\s*\.?\s*",
            "",
            body,
            count=1,
        ).strip()
    bold_spans = re.findall(r"\*\*(.+?)\*\*", body)
    if not bold_spans and not explicit_statement:
        return None
    candidate = bold_spans[-1].strip() if bold_spans else body
    numeric_tokens = re.findall(r"(?<![\w.])-?\d[\d,]*(?:\.\d+)?(?![\w.])", candidate)
    if len(numeric_tokens) == 1:
        return numeric_tokens[0].replace(",", "")
    return candidate.strip("$* ") or None


def parse_solution(content: str) -> ParsedSolution:
    """Extract explicitly numbered visible steps and a best-effort final answer."""

    matches = list(STEP_PATTERN.finditer(content))
    steps = []
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(content)
        steps.append(
            ParsedStep(
                number=int(match.group(1)),
                text=content[match.end() : end].strip(),
            )
        )

    warnings = []
    if not steps:
        warnings.append("no_numbered_steps")
    elif [step.number for step in steps] != list(range(1, len(steps) + 1)):
        warnings.append("non_sequential_step_numbers")

    has_answer_label = bool(
        re.search(r"(?im)^\s*(?:\*\*)?(?:Final\s+Answer|Answer)\s*:", content)
    )
    if has_answer_label:
        final_answer = _extract_final_answer(content)
    else:
        final_answer = (
            _extract_stated_answer_from_last_step(steps[-1]) if steps else None
        ) or _extract_final_answer(content)
    if final_answer is None:
        warnings.append("final_answer_not_detected")
    return ParsedSolution(steps=steps, final_answer=final_answer, warnings=warnings)
