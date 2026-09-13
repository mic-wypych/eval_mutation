from __future__ import annotations

import asyncio
import hashlib
import json
import tempfile
import unittest
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import patch

from pydantic_ai.models.test import TestModel
from pydantic_evals.reporting import EvaluationReport, ReportCaseFailure

from eval_mutation.agent.triage_agent import AgentConfig, build_agent
from eval_mutation.evals import TriageEvalTask, load_dataset
from eval_mutation.evals.artifacts import (
    EvalRunManifest,
    EvalRunSummary,
    build_result_rows,
    build_slice_summary,
    write_eval_artifacts,
)


class EvalArtifactTests(unittest.TestCase):
    def _successful_report(self):
        dataset = load_dataset("datasets/development.yaml")
        dataset.cases = dataset.cases[:1]
        config = AgentConfig()
        model = TestModel(
            call_tools=[],
            custom_output_args={
                "team": "product_feedback",
                "urgency": "P3_low",
                "summary": "Feature request for scheduled PDF exports.",
                "rationale": "R-FEED-1 and U-P3-1 support this filing.",
                "related_ticket_ids": [],
                "uncertainty_note": None,
            },
        )
        task = TriageEvalTask(config=config, agent=build_agent(config, model=model))
        report = asyncio.run(
            dataset.evaluate(task, progress=False, repeat=2, max_concurrency=1)
        )
        return dataset, config, report

    def test_artifacts_preserve_repeat_rows_slices_and_provenance(self) -> None:
        dataset, config, report = self._successful_report()
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "baseline.json"
            with patch(
                "eval_mutation.evals.artifacts._ollama_runtime",
                return_value=("0.30.7", "abc123"),
            ):
                paths = write_eval_artifacts(
                    report=report,
                    dataset=dataset,
                    dataset_path=Path("datasets/development.yaml"),
                    output_path=output,
                    config=config,
                    project_root=Path("."),
                    run_id="test-run",
                    repeat=2,
                    max_concurrency=1,
                    observability_enabled=False,
                    created_at=datetime(2026, 9, 13, tzinfo=UTC),
                )

            rows = [json.loads(line) for line in paths.rows.read_text().splitlines()]
            summary = EvalRunSummary.model_validate_json(paths.summary.read_text())
            manifest = EvalRunManifest.model_validate_json(paths.manifest.read_text())

            self.assertTrue(paths.report.is_file())
            self.assertEqual([row["repeat_index"] for row in rows], [1, 2])
            self.assertEqual({row["case_id"] for row in rows}, {"dev-001"})
            self.assertEqual(
                [row["scores"]["tool_calls_total"]["value"] for row in rows],
                [1, 1],
            )

            overall = next(
                item for item in summary.slices if item.dimension == "overall"
            )
            self.assertEqual(overall.total_runs, 2)
            self.assertEqual(overall.assertions["integrated_success"].passed, 2)
            self.assertEqual(overall.assertions["integrated_success"].pass_rate, 1.0)
            self.assertEqual(overall.mean_scores["filing_calls"].total, 2)
            self.assertEqual(overall.mean_scores["filing_calls"].mean, 1.0)
            self.assertTrue(
                any(
                    item.dimension == "task_family"
                    and item.value == "T1_routine_routing"
                    for item in summary.slices
                )
            )
            self.assertTrue(
                any(
                    item.dimension == "facet" and item.value == "F1_routing"
                    for item in summary.slices
                )
            )

            self.assertEqual(manifest.run_id, "test-run")
            self.assertEqual(manifest.dataset_version, "0.1.0")
            self.assertEqual(manifest.selected_case_ids, ["dev-001"])
            self.assertEqual(manifest.agent_config["model_name"], "gemma4:e4b")
            self.assertEqual(manifest.ollama_version, "0.30.7")
            self.assertEqual(manifest.model_digest, "abc123")
            self.assertEqual(manifest.repeat, 2)
            self.assertIn("TeamAssignment", manifest.evaluator_versions)
            self.assertEqual(
                manifest.fixture_sha256s, manifest.declared_fixture_sha256s
            )
            for artifact in manifest.artifacts.values():
                self.assertEqual(
                    artifact.sha256,
                    hashlib.sha256(Path(artifact.path).read_bytes()).hexdigest(),
                )

    def test_failed_case_has_exception_slice_and_no_assertion_denominator(self) -> None:
        dataset = load_dataset("datasets/development.yaml")
        case = dataset.cases[0]
        report = EvaluationReport(
            name="failed-report",
            cases=[],
            failures=[
                ReportCaseFailure(
                    name="dev-001 [2/3]",
                    source_case_name="dev-001",
                    inputs=case.inputs,
                    metadata=case.metadata,
                    expected_output=case.expected_output,
                    error_message="request timed out",
                    error_stacktrace="Traceback ...\nTimeoutError: request timed out",
                )
            ],
        )

        rows = build_result_rows(report, "failed-run")
        summary = build_slice_summary(rows, "failed-run")

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].repeat_index, 2)
        self.assertEqual(rows[0].repeat_count, 3)
        self.assertEqual(rows[0].exception_type, "TimeoutError")
        exception_slice = next(
            item
            for item in summary.slices
            if item.dimension == "exception_type" and item.value == "TimeoutError"
        )
        self.assertEqual(exception_slice.failed_runs, 1)
        self.assertEqual(exception_slice.assertions, {})


if __name__ == "__main__":
    unittest.main()
