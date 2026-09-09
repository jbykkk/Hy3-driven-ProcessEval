"""Build the mathematics-solving prompt."""

from __future__ import annotations

from solver.dataset import SolverSample


PROMPT_VERSION = "math-solver-v2"

INSTRUCTION_V2 = (
    "Solve the following mathematics problem and provide a clear step-by-step solution. "
    "Number the steps explicitly as Step 1, Step 2, Step 3, ... "
    "Each step should represent one coherent stage of the solution, with a clear "
    "mathematical purpose and a clear intermediate result or decision whenever applicable. "
    "Show enough mathematical reasoning or calculation to justify every key intermediate "
    "result that is used later in the solution. Avoid unsupported jumps such as "
    "'clearly' or 'after some algebra' when the omitted reasoning is important. "
    "Keep each step reasonably concise. A step may contain a short sequence of closely "
    "related calculations, but start a new step when the solution moves to a different "
    "mathematical objective, assumption, case, or major inference. "
    "When using a nontrivial theorem, identity, or problem condition that is essential "
    "to the argument, state it at the point where it is used. "
    "When an operation requires a condition or may introduce, remove, or invalidate "
    "solutions, explicitly state and check the relevant condition when necessary. "
    "If case analysis is required, make the relevant cases explicit and show how they "
    "are combined or eliminated. "
    "Use one primary solution approach. Avoid abandoned attempts, alternative solutions, "
    "unnecessary repetition, and meta-commentary. "
    "Prefer exact mathematical forms over unnecessary decimal approximations. "
    "Make sure the visible reasoning supports the final conclusion. "
    "End with 'Final Answer: \\boxed{...}'."
)

INSTRUCTIONS = {PROMPT_VERSION: INSTRUCTION_V2}


def build_messages(
    sample: SolverSample,
    *,
    prompt_version: str = PROMPT_VERSION,
) -> list[dict[str, str]]:
    """Return a single-turn prompt containing no benchmark reference information."""

    try:
        instruction = INSTRUCTIONS[prompt_version]
    except KeyError as error:
        raise ValueError(f"Unknown solver prompt version: {prompt_version}") from error
    content = f"{instruction}\n\nProblem:\n{sample.problem}"
    return [{"role": "user", "content": content}]
