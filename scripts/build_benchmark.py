"""Build the deterministic 400-problem benchmark from downloaded raw data."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable

import pyarrow.parquet as pq


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RAW_DIR = ROOT / "data" / "raw"
DEFAULT_OUTPUT_DIR = ROOT / "data" / "benchmark"
DEFAULT_SEED = 20260824

SOURCES = {
    "gsm8k": {
        "repo": "openai/gsm8k",
        "revision": "740312add88f781978c0658806c59bc2815b9866",
    },
    "math": {
        "repo": "EleutherAI/hendrycks_math",
        "revision": "21a5633873b6a120296cce3e2df9d5550074f4a3",
    },
    "aime24": {
        "repo": "math-ai/aime24",
        "revision": "83a7f387baaa524a8bda0022eac0541582297103",
    },
    "aime25": {
        "repo": "math-ai/aime25",
        "revision": "563bb8404243c5f09de6ec262f2db674fe5bce9b",
    },
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw-dir", type=Path, default=DEFAULT_RAW_DIR)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    return parser.parse_args()


def stable_rank(seed: int, source_id: str) -> str:
    payload = f"{seed}:{source_id}".encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def select_by_hash(records: list[dict[str, Any]], count: int, seed: int) -> list[dict[str, Any]]:
    if len(records) < count:
        raise ValueError(f"Cannot select {count} records from a group of {len(records)}")
    return sorted(records, key=lambda row: stable_rank(seed, row["id"]))[:count]


def read_parquet(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        raise FileNotFoundError(f"Missing raw data file: {path}")
    return pq.read_table(path).to_pylist()


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        raise FileNotFoundError(f"Missing raw data file: {path}")
    with path.open("r", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def extract_boxed_answer(solution: str) -> str:
    marker = r"\boxed"
    answers: list[str] = []
    start = 0
    while True:
        marker_index = solution.find(marker, start)
        if marker_index < 0:
            break
        cursor = marker_index + len(marker)
        while cursor < len(solution) and solution[cursor].isspace():
            cursor += 1
        if cursor < len(solution) and solution[cursor] == "{":
            depth = 0
            for end in range(cursor, len(solution)):
                if solution[end] == "{":
                    depth += 1
                elif solution[end] == "}":
                    depth -= 1
                    if depth == 0:
                        answers.append(solution[cursor + 1 : end].strip())
                        start = end + 1
                        break
            else:
                start = cursor + 1
        else:
            match = re.match(r"([^\s$.,;]+)", solution[cursor:])
            if match:
                answers.append(match.group(1).strip())
            start = cursor + 1
    if not answers:
        raise ValueError("Reference solution has no parseable boxed answer")
    return answers[-1]


def extract_gsm8k_answer(solution: str) -> str:
    if "####" not in solution:
        raise ValueError("GSM8K reference solution is missing the final-answer marker")
    return solution.rsplit("####", maxsplit=1)[1].strip().replace(",", "")


def build_gsm8k(raw_dir: Path, seed: int) -> list[dict[str, Any]]:
    path = raw_dir / "gsm8k" / "main" / "test-00000-of-00001.parquet"
    rows = read_parquet(path)
    if len(rows) != 1319:
        raise ValueError(f"Expected 1,319 GSM8K test rows, found {len(rows)}")

    records = []
    for index, row in enumerate(rows):
        source_id = f"gsm8k:test:{index:04d}"
        records.append(
            {
                "schema_version": "1.0",
                "id": source_id.replace(":", "-"),
                "dataset": "gsm8k",
                "problem": row["question"],
                "reference_answer": extract_gsm8k_answer(row["answer"]),
                "reference_solution": row["answer"],
                "metadata": {
                    "source_repo": SOURCES["gsm8k"]["repo"],
                    "source_revision": SOURCES["gsm8k"]["revision"],
                    "source_config": "main",
                    "source_split": "test",
                    "source_index": index,
                    "difficulty": None,
                },
            }
        )
    return sorted(select_by_hash(records, 100, seed), key=lambda row: row["id"])


def build_math(raw_dir: Path, seed: int) -> list[dict[str, Any]]:
    root = raw_dir / "math_eleutherai"
    paths = sorted(root.glob("*/test-*.parquet"))
    if len(paths) != 7:
        raise ValueError(f"Expected 7 MATH subject test files, found {len(paths)}")

    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    total = 0
    for path in paths:
        subject_config = path.parent.name
        for index, row in enumerate(read_parquet(path)):
            total += 1
            level = row["level"]
            source_id = f"math:test:{subject_config}:{index:04d}"
            grouped[level].append(
                {
                    "schema_version": "1.0",
                    "id": source_id.replace(":", "-"),
                    "dataset": "math",
                    "problem": row["problem"],
                    "reference_answer": extract_boxed_answer(row["solution"]),
                    "reference_solution": row["solution"],
                    "metadata": {
                        "source_repo": SOURCES["math"]["repo"],
                        "source_revision": SOURCES["math"]["revision"],
                        "source_config": subject_config,
                        "source_split": "test",
                        "source_index": index,
                        "difficulty": level,
                        "subject": row["type"],
                    },
                }
            )
    if total != 5000:
        raise ValueError(f"Expected 5,000 MATH test rows, found {total}")

    expected_levels = [f"Level {level}" for level in range(1, 6)]
    if sorted(grouped) != expected_levels:
        raise ValueError(f"Unexpected MATH difficulty levels: {sorted(grouped)}")

    selected = []
    for level in expected_levels:
        selected.extend(select_by_hash(grouped[level], 50, seed))
    return sorted(selected, key=lambda row: (row["metadata"]["difficulty"], row["id"]))


def build_aime(raw_dir: Path, seed: int) -> list[dict[str, Any]]:
    rows_2024 = read_parquet(raw_dir / "aime24" / "test-00000-of-00001.parquet")
    rows_2025 = read_jsonl(raw_dir / "aime25" / "test.jsonl")
    if len(rows_2024) != 30 or len(rows_2025) != 30:
        raise ValueError(
            f"Expected 30 problems per AIME year, found {len(rows_2024)} and {len(rows_2025)}"
        )

    yearly_records: dict[int, list[dict[str, Any]]] = {2024: [], 2025: []}
    for index, row in enumerate(rows_2024):
        original_id = str(row["id"])
        yearly_records[2024].append(
            {
                "schema_version": "1.0",
                "id": f"aime-2024-{original_id}",
                "dataset": "aime",
                "problem": row["problem"],
                "reference_answer": extract_boxed_answer(row["solution"]),
                "reference_solution": row["solution"],
                "metadata": {
                    "source_repo": SOURCES["aime24"]["repo"],
                    "source_revision": SOURCES["aime24"]["revision"],
                    "source_split": "test",
                    "source_index": index,
                    "source_id": original_id,
                    "year": 2024,
                    "url": row["url"],
                    "difficulty": "competition",
                },
            }
        )

    for index, row in enumerate(rows_2025):
        original_id = str(row["id"])
        yearly_records[2025].append(
            {
                "schema_version": "1.0",
                "id": f"aime-2025-{original_id}",
                "dataset": "aime",
                "problem": row["problem"],
                "reference_answer": str(row["answer"]),
                "reference_solution": None,
                "metadata": {
                    "source_repo": SOURCES["aime25"]["repo"],
                    "source_revision": SOURCES["aime25"]["revision"],
                    "source_split": "test",
                    "source_index": index,
                    "source_id": original_id,
                    "year": 2025,
                    "difficulty": "competition",
                },
            }
        )

    selected = []
    for year in (2024, 2025):
        selected.extend(select_by_hash(yearly_records[year], 25, seed))
    return sorted(selected, key=lambda row: (row["metadata"]["year"], row["id"]))


def write_jsonl(path: Path, records: Iterable[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False, separators=(",", ":")) + "\n")


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def validate(records: list[dict[str, Any]]) -> None:
    ids = [row["id"] for row in records]
    if len(ids) != len(set(ids)):
        raise ValueError("Benchmark IDs are not unique")
    for row in records:
        if not row["problem"].strip() or not str(row["reference_answer"]).strip():
            raise ValueError(f"Incomplete benchmark record: {row['id']}")


def main() -> None:
    args = parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)

    datasets = {
        "gsm8k": build_gsm8k(args.raw_dir, args.seed),
        "math": build_math(args.raw_dir, args.seed),
        "aime": build_aime(args.raw_dir, args.seed),
    }
    expected_counts = {"gsm8k": 100, "math": 250, "aime": 50}
    if {name: len(rows) for name, rows in datasets.items()} != expected_counts:
        raise ValueError("Unexpected selected dataset counts")

    combined = [row for name in ("gsm8k", "math", "aime") for row in datasets[name]]
    validate(combined)

    output_paths: dict[str, Path] = {}
    for name, rows in datasets.items():
        output_paths[name] = args.output_dir / f"{name}.jsonl"
        write_jsonl(output_paths[name], rows)
    output_paths["benchmark"] = args.output_dir / "benchmark.jsonl"
    write_jsonl(output_paths["benchmark"], combined)

    math_levels = Counter(row["metadata"]["difficulty"] for row in datasets["math"])
    aime_years = Counter(str(row["metadata"]["year"]) for row in datasets["aime"])
    manifest = {
        "schema_version": "1.0",
        "seed": args.seed,
        "selection_method": "ascending SHA-256 rank of '<seed>:<stable-id>' within each stratum",
        "counts": {**expected_counts, "total": len(combined)},
        "strata": {
            "math_levels": dict(sorted(math_levels.items())),
            "aime_years": dict(sorted(aime_years.items())),
        },
        "sources": SOURCES,
        "files": {
            path.name: {"records": sum(1 for _ in path.open(encoding="utf-8")), "sha256": file_sha256(path)}
            for path in output_paths.values()
        },
    }
    manifest_path = args.output_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(json.dumps(manifest["counts"], ensure_ascii=False))
    print(json.dumps(manifest["strata"], ensure_ascii=False))


if __name__ == "__main__":
    main()
