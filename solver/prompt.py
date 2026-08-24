"""Build the initial minimal mathematics-solving prompt."""

from __future__ import annotations

from solver.dataset import SolverSample


PROMPT_VERSION = "math-solver-v1"
INSTRUCTION = (
    "Solve the following mathematics problem. Provide a clear step-by-step solution. "
    "Number the steps explicitly as Step 1, Step 2, Step 3, ... "
    "Do not skip important reasoning or calculations."
)


def build_messages(sample: SolverSample) -> list[dict[str, str]]:
    """Return a single-turn prompt containing no benchmark reference information."""

    content = f"{INSTRUCTION}\n\nProblem:\n{sample.problem}"
    return [{"role": "user", "content": content}]
