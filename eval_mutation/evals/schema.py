from __future__ import annotations

import argparse
from pathlib import Path

from eval_mutation.evals.dataset import TriageDataset


def regenerate_schema(dataset_path: Path, schema_path: Path) -> None:
    dataset = TriageDataset.from_file(dataset_path)
    dataset.to_file(dataset_path, schema_path=schema_path)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Canonicalize an eval dataset and regenerate its schema.")
    parser.add_argument("dataset", type=Path)
    parser.add_argument("--schema", type=Path, required=True)
    args = parser.parse_args(argv)
    regenerate_schema(args.dataset, args.schema)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
