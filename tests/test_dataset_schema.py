from __future__ import annotations

import json
import unittest
from pathlib import Path

from eval_mutation.evals.dataset import TriageDataset


class DatasetSchemaTests(unittest.TestCase):
    def test_committed_schema_matches_typed_dataset_models(self) -> None:
        committed = json.loads(Path("datasets/development_schema.json").read_text(encoding="utf-8"))
        generated = TriageDataset.model_json_schema_with_evaluators()
        self.assertEqual(committed, generated)


if __name__ == "__main__":
    unittest.main()
