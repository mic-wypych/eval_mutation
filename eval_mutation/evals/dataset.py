from __future__ import annotations

from pathlib import Path

from pydantic_evals import Dataset

from eval_mutation.evals.evaluators import DEFAULT_EVALUATORS
from eval_mutation.evals.models import TriageCaseInput, TriageCaseMetadata, TriageEvalOutput


class TriageDataset(Dataset[TriageCaseInput, TriageEvalOutput, TriageCaseMetadata]):
    """Concrete dataset type required for typed YAML deserialization and schema generation."""


def load_dataset(path: str | Path) -> TriageDataset:
    dataset = TriageDataset.from_file(path)
    dataset.evaluators = list(DEFAULT_EVALUATORS)
    return dataset
