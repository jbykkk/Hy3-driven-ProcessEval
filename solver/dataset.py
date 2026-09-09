"""Load only model-visible fields from the benchmark JSONL."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator


@dataclass(frozen=True)
class SolverSample:
    """The complete set of benchmark fields allowed to enter the solver."""

    id: str
    dataset: str
    problem: str

    def as_dict(self) -> dict[str, str]:
        return {"id": self.id, "dataset": self.dataset, "problem": self.problem}


def load_samples(path: Path) -> Iterator[SolverSample]:
    """Yield solver-safe samples without answers, solutions, or reference metadata."""

    seen_ids: set[str] = set()
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            try:
                row = json.loads(line)
                sample = SolverSample(
                    id=str(row["id"]),
                    dataset=str(row["dataset"]),
                    problem=str(row["problem"]),
                )
            except (json.JSONDecodeError, KeyError, TypeError, ValueError) as error:
                raise ValueError(f"Invalid benchmark row at {path}:{line_number}") from error

            if not sample.id or not sample.dataset or not sample.problem.strip():
                raise ValueError(f"Empty solver field at {path}:{line_number}")
            if sample.id in seen_ids:
                raise ValueError(f"Duplicate sample ID {sample.id!r} at {path}:{line_number}")
            seen_ids.add(sample.id)
            yield sample
