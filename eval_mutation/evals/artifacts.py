from __future__ import annotations

import hashlib
import importlib.metadata
import json
import os
import platform
import re
import subprocess
import sys
from collections import defaultdict
from collections.abc import Iterable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit
from urllib.request import urlopen

from pydantic import Field
from pydantic_evals.reporting import EvaluationReportAdapter

from eval_mutation.agent.instructions import BASE_INSTRUCTIONS
from eval_mutation.agent.triage_agent import AgentConfig
from eval_mutation.domain.models import StrictModel
from eval_mutation.evals.dataset import TriageDataset
from eval_mutation.evals.evaluators import DEFAULT_EVALUATORS
from eval_mutation.evals.models import TriageCaseMetadata, TriageEvalOutput

ARTIFACT_SCHEMA_VERSION = "1.0"


class EvaluatorValue(StrictModel):
    value: bool | int | float | str
    reason: str | None = None
    evaluator: str | None = None
    evaluator_version: str | None = None


class EvaluatorFailureRecord(StrictModel):
    name: str
    error_type: str | None = None
    error_message: str
    evaluator: str | None = None
    evaluator_version: str | None = None


class EvalRunRow(StrictModel):
    schema_version: str = ARTIFACT_SCHEMA_VERSION
    run_id: str
    case_id: str
    report_case_name: str
    repeat_index: int = Field(ge=1)
    repeat_count: int = Field(ge=1)
    split: str | None = None
    task_family: str | None = None
    target_facets: list[str] = Field(default_factory=list)
    metamorphic_group_id: str | None = None
    fixture_sha256: str | None = None
    expected_teams: list[str] = Field(default_factory=list)
    actual_team: str | None = None
    expected_urgency: str | None = None
    actual_urgency: str | None = None
    expected_related_ticket_ids: list[int] = Field(default_factory=list)
    actual_related_ticket_ids: list[int] = Field(default_factory=list)
    expected_manual_triage: bool | None = None
    actual_manual_triage: bool | None = None
    outcome: str
    exception_type: str | None = None
    error_message: str | None = None
    error_stacktrace: str | None = None
    assertions: dict[str, EvaluatorValue] = Field(default_factory=dict)
    scores: dict[str, EvaluatorValue] = Field(default_factory=dict)
    labels: dict[str, EvaluatorValue] = Field(default_factory=dict)
    metrics: dict[str, int | float] = Field(default_factory=dict)
    evaluator_failures: list[EvaluatorFailureRecord] = Field(default_factory=list)
    task_duration_seconds: float | None = Field(default=None, ge=0)
    total_duration_seconds: float | None = Field(default=None, ge=0)
    trace_id: str | None = None
    span_id: str | None = None


class AssertionAggregate(StrictModel):
    passed: int = Field(ge=0)
    total: int = Field(ge=0)
    pass_rate: float | None = Field(default=None, ge=0, le=1)


class ScoreAggregate(StrictModel):
    total: int = Field(ge=0)
    mean: float


class SliceSummary(StrictModel):
    dimension: str
    value: str
    total_runs: int = Field(ge=0)
    completed_runs: int = Field(ge=0)
    failed_runs: int = Field(ge=0)
    assertions: dict[str, AssertionAggregate] = Field(default_factory=dict)
    mean_scores: dict[str, ScoreAggregate] = Field(default_factory=dict)


class EvalRunSummary(StrictModel):
    schema_version: str = ARTIFACT_SCHEMA_VERSION
    run_id: str
    slices: list[SliceSummary]


class ArtifactFile(StrictModel):
    path: str
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")


class EvalRunManifest(StrictModel):
    schema_version: str = ARTIFACT_SCHEMA_VERSION
    run_id: str
    created_at: datetime
    configuration: str = "baseline"
    mutation_id: str | None = None
    report_name: str
    dataset_name: str
    dataset_version: str | None = None
    dataset_path: str
    dataset_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    selected_case_ids: list[str]
    fixture_sha256s: dict[str, str]
    declared_fixture_sha256s: dict[str, str]
    runbook_sha256s: dict[str, str]
    base_instructions_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    source_sha256s: dict[str, str]
    evaluator_versions: dict[str, str]
    agent_config: dict[str, Any]
    model_digest: str | None = None
    ollama_version: str | None = None
    package_versions: dict[str, str]
    python_version: str
    platform: str
    cpu_count: int | None = Field(default=None, ge=1)
    git_commit: str | None = None
    git_dirty: bool | None = None
    repeat: int = Field(ge=1)
    max_concurrency: int = Field(ge=1)
    observability_enabled: bool
    report_failures: int = Field(ge=0)
    report_evaluator_failures: int = Field(ge=0)
    artifacts: dict[str, ArtifactFile]


class EvalArtifactPaths(StrictModel):
    report: Path
    rows: Path
    summary: Path
    manifest: Path


_REPEAT_SUFFIX = re.compile(r"\s+\[(?P<index>\d+)/(?P<count>\d+)]$")
_EXCEPTION_LINE = re.compile(r"^(?P<type>[A-Za-z_][\w.]*(?:Error|Exception))(?::|$)")


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _sha256_file(path: Path) -> str:
    return _sha256_bytes(path.read_bytes())


def _repeat_identity(name: str) -> tuple[int, int]:
    match = _REPEAT_SUFFIX.search(name)
    if match is None:
        return 1, 1
    return int(match.group("index")), int(match.group("count"))


def _result_values(values: dict[str, Any]) -> dict[str, EvaluatorValue]:
    result: dict[str, EvaluatorValue] = {}
    for name, value in values.items():
        source = getattr(value, "source", None)
        result[name] = EvaluatorValue(
            value=value.value,
            reason=value.reason,
            evaluator=getattr(source, "name", None),
            evaluator_version=value.evaluator_version,
        )
    return result


def _evaluator_failures(values: Iterable[Any]) -> list[EvaluatorFailureRecord]:
    failures: list[EvaluatorFailureRecord] = []
    for value in values:
        source = getattr(value, "source", None)
        failures.append(
            EvaluatorFailureRecord(
                name=value.name,
                error_type=value.error_type,
                error_message=value.error_message,
                evaluator=getattr(source, "name", None),
                evaluator_version=value.evaluator_version,
            )
        )
    return failures


def _metadata_fields(metadata: TriageCaseMetadata | None) -> dict[str, Any]:
    if metadata is None:
        return {
            "split": None,
            "task_family": None,
            "target_facets": [],
            "metamorphic_group_id": None,
            "fixture_sha256": None,
        }
    return {
        "split": metadata.split.value,
        "task_family": metadata.task_family.value,
        "target_facets": [facet.value for facet in metadata.target_facets],
        "metamorphic_group_id": metadata.metamorphic_group_id,
        "fixture_sha256": metadata.fixture_sha256,
    }


def _expected_fields(expected: TriageEvalOutput | None) -> dict[str, Any]:
    if expected is None:
        return {
            "expected_teams": [],
            "expected_urgency": None,
            "expected_related_ticket_ids": [],
            "expected_manual_triage": None,
        }
    teams = list(expected.permitted_teams)
    if expected.team is not None:
        teams.append(expected.team)
    return {
        "expected_teams": [team.value for team in teams],
        "expected_urgency": expected.urgency.value
        if expected.urgency is not None
        else None,
        "expected_related_ticket_ids": expected.related_ticket_ids,
        "expected_manual_triage": expected.manual_triage,
    }


def _exception_type(message: str, stacktrace: str) -> str:
    for line in reversed([*stacktrace.splitlines(), message]):
        match = _EXCEPTION_LINE.match(line.strip())
        if match is not None:
            return match.group("type").rsplit(".", 1)[-1]
    return "TaskFailure"


def build_result_rows(report: Any, run_id: str) -> list[EvalRunRow]:
    rows: list[EvalRunRow] = []
    for case in report.cases:
        metadata = case.metadata
        expected = case.expected_output
        output = case.output
        repeat_index, repeat_count = _repeat_identity(case.name)
        metadata_fields = _metadata_fields(metadata)
        observed_fixture_hash = case.attributes.get("fixture_sha256")
        if isinstance(observed_fixture_hash, str):
            metadata_fields["fixture_sha256"] = observed_fixture_hash
        rows.append(
            EvalRunRow(
                run_id=run_id,
                case_id=metadata.case_id
                if metadata is not None
                else (case.source_case_name or case.name),
                report_case_name=case.name,
                repeat_index=repeat_index,
                repeat_count=repeat_count,
                **metadata_fields,
                **_expected_fields(expected),
                actual_team=output.team.value if output.team is not None else None,
                actual_urgency=output.urgency.value
                if output.urgency is not None
                else None,
                actual_related_ticket_ids=output.related_ticket_ids,
                actual_manual_triage=output.manual_triage,
                outcome="completed",
                assertions=_result_values(case.assertions),
                scores=_result_values(case.scores),
                labels=_result_values(case.labels),
                metrics=case.metrics,
                evaluator_failures=_evaluator_failures(case.evaluator_failures),
                task_duration_seconds=case.task_duration,
                total_duration_seconds=case.total_duration,
                trace_id=case.trace_id,
                span_id=case.span_id,
            )
        )

    for case in report.failures:
        metadata = case.metadata
        repeat_index, repeat_count = _repeat_identity(case.name)
        rows.append(
            EvalRunRow(
                run_id=run_id,
                case_id=metadata.case_id
                if metadata is not None
                else (case.source_case_name or case.name),
                report_case_name=case.name,
                repeat_index=repeat_index,
                repeat_count=repeat_count,
                **_metadata_fields(metadata),
                **_expected_fields(case.expected_output),
                outcome="task_failure",
                exception_type=_exception_type(
                    case.error_message, case.error_stacktrace
                ),
                error_message=case.error_message,
                error_stacktrace=case.error_stacktrace,
                trace_id=case.trace_id,
                span_id=case.span_id,
            )
        )
    return rows


def _slice_memberships(row: EvalRunRow) -> Iterable[tuple[str, str]]:
    yield "overall", "all"
    if row.task_family is not None:
        yield "task_family", row.task_family
    for facet in row.target_facets:
        yield "facet", facet
    for team in row.expected_teams:
        yield "expected_team", team
    if row.expected_urgency is not None:
        yield "expected_urgency", row.expected_urgency
    if row.fixture_sha256 is not None:
        yield "fixture", row.fixture_sha256
    yield "exception_type", row.exception_type or "none"


def build_slice_summary(rows: list[EvalRunRow], run_id: str) -> EvalRunSummary:
    grouped: dict[tuple[str, str], list[EvalRunRow]] = defaultdict(list)
    for row in rows:
        for membership in _slice_memberships(row):
            grouped[membership].append(row)

    slices: list[SliceSummary] = []
    for (dimension, value), members in sorted(grouped.items()):
        assertion_names = sorted({name for row in members for name in row.assertions})
        assertions: dict[str, AssertionAggregate] = {}
        for name in assertion_names:
            applicable = [
                row.assertions[name].value for row in members if name in row.assertions
            ]
            passed = sum(result is True for result in applicable)
            assertions[name] = AssertionAggregate(
                passed=passed,
                total=len(applicable),
                pass_rate=passed / len(applicable) if applicable else None,
            )

        score_names = sorted({name for row in members for name in row.scores})
        means: dict[str, ScoreAggregate] = {}
        for name in score_names:
            values = [
                float(row.scores[name].value) for row in members if name in row.scores
            ]
            means[name] = ScoreAggregate(
                total=len(values), mean=sum(values) / len(values)
            )
        completed = sum(row.outcome == "completed" for row in members)
        slices.append(
            SliceSummary(
                dimension=dimension,
                value=value,
                total_runs=len(members),
                completed_runs=completed,
                failed_runs=len(members) - completed,
                assertions=assertions,
                mean_scores=means,
            )
        )
    return EvalRunSummary(run_id=run_id, slices=slices)


def _git_value(project_root: Path, *arguments: str) -> str | None:
    try:
        result = subprocess.run(
            ("git", *arguments),
            cwd=project_root,
            check=False,
            capture_output=True,
            text=True,
            timeout=2,
        )
    except OSError, subprocess.TimeoutExpired:
        return None
    return result.stdout.strip() if result.returncode == 0 else None


def _package_versions() -> dict[str, str]:
    versions: dict[str, str] = {}
    for package in ("pydantic-ai", "pydantic-evals", "pydantic", "logfire"):
        try:
            versions[package] = importlib.metadata.version(package)
        except importlib.metadata.PackageNotFoundError:
            versions[package] = "not-installed"
    return versions


def _ollama_runtime(config: AgentConfig) -> tuple[str | None, str | None]:
    parsed = urlsplit(config.base_url)
    api_root = f"{parsed.scheme}://{parsed.netloc}"

    def load(path: str) -> dict[str, Any]:
        with urlopen(f"{api_root}{path}", timeout=1) as response:
            return json.load(response)

    try:
        version = load("/api/version").get("version")
        models = load("/api/tags").get("models", [])
    except OSError, TimeoutError, ValueError, json.JSONDecodeError:
        return None, None

    exact = [model for model in models if model.get("name") == config.model_name]
    if not exact and ":" not in config.model_name:
        exact = [
            model
            for model in models
            if str(model.get("name", "")).startswith(f"{config.model_name}:")
        ]
    digest = exact[0].get("digest") if len(exact) == 1 else None
    return str(version) if version is not None else None, str(
        digest
    ) if digest is not None else None


def _source_hashes(project_root: Path) -> tuple[dict[str, str], dict[str, str]]:
    runbook_paths = sorted((project_root / "eval_mutation/agent/runbooks").glob("*.md"))
    runbooks = {
        str(path.relative_to(project_root)): _sha256_file(path)
        for path in runbook_paths
    }
    source_paths = (
        project_root / "eval_mutation/agent/instructions.py",
        project_root / "eval_mutation/evals/evaluators.py",
        project_root / "eval_mutation/evals/task.py",
    )
    sources = {
        str(path.relative_to(project_root)): _sha256_file(path)
        for path in source_paths
        if path.is_file()
    }
    return runbooks, sources


def write_eval_artifacts(
    *,
    report: Any,
    dataset: TriageDataset,
    dataset_path: Path,
    output_path: Path,
    config: AgentConfig,
    project_root: Path,
    run_id: str,
    repeat: int,
    max_concurrency: int,
    observability_enabled: bool,
    created_at: datetime | None = None,
) -> EvalArtifactPaths:
    root = project_root.resolve()
    resolved_dataset_path = dataset_path.resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    rows_path = output_path.with_name(f"{output_path.stem}.rows.jsonl")
    summary_path = output_path.with_name(f"{output_path.stem}.summary.json")
    manifest_path = output_path.with_name(f"{output_path.stem}.manifest.json")

    rows = build_result_rows(report, run_id)
    summary = build_slice_summary(rows, run_id)
    output_path.write_bytes(EvaluationReportAdapter.dump_json(report, indent=2))
    rows_path.write_text(
        "".join(row.model_dump_json() + "\n" for row in rows),
        encoding="utf-8",
    )
    summary_path.write_text(summary.model_dump_json(indent=2) + "\n", encoding="utf-8")

    dataset_versions = {
        case.metadata.dataset_version
        for case in dataset.cases
        if case.metadata is not None
    }
    declared_fixture_hashes = {
        case.inputs.fixture_path: case.metadata.fixture_sha256
        for case in dataset.cases
        if case.metadata is not None
    }
    fixture_hashes: dict[str, str] = {}
    for case in dataset.cases:
        fixture_path = (root / case.inputs.fixture_path).resolve()
        if fixture_path.is_relative_to(root) and fixture_path.is_file():
            fixture_hashes[case.inputs.fixture_path] = _sha256_file(fixture_path)
    runbooks, source_hashes = _source_hashes(root)
    ollama_version, model_digest = _ollama_runtime(config)
    git_commit = _git_value(root, "rev-parse", "HEAD")
    git_status = _git_value(root, "status", "--porcelain")
    artifact_files = {
        "report": ArtifactFile(path=str(output_path), sha256=_sha256_file(output_path)),
        "rows": ArtifactFile(path=str(rows_path), sha256=_sha256_file(rows_path)),
        "summary": ArtifactFile(
            path=str(summary_path), sha256=_sha256_file(summary_path)
        ),
    }
    manifest = EvalRunManifest(
        run_id=run_id,
        created_at=created_at or datetime.now(UTC),
        report_name=report.name,
        dataset_name=dataset.name,
        dataset_version=next(iter(dataset_versions))
        if len(dataset_versions) == 1
        else None,
        dataset_path=str(dataset_path),
        dataset_sha256=_sha256_file(resolved_dataset_path),
        selected_case_ids=[case.name for case in dataset.cases],
        fixture_sha256s=dict(sorted(fixture_hashes.items())),
        declared_fixture_sha256s=dict(sorted(declared_fixture_hashes.items())),
        runbook_sha256s=runbooks,
        base_instructions_sha256=_sha256_bytes(BASE_INSTRUCTIONS.encode()),
        source_sha256s=source_hashes,
        evaluator_versions={
            type(evaluator).__name__: evaluator.get_evaluator_version()
            for evaluator in DEFAULT_EVALUATORS
        },
        agent_config=config.model_dump(mode="json"),
        model_digest=model_digest,
        ollama_version=ollama_version,
        package_versions=_package_versions(),
        python_version=sys.version.split()[0],
        platform=platform.platform(),
        cpu_count=os.cpu_count(),
        git_commit=git_commit,
        git_dirty=bool(git_status) if git_status is not None else None,
        repeat=repeat,
        max_concurrency=max_concurrency,
        observability_enabled=observability_enabled,
        report_failures=len(report.failures),
        report_evaluator_failures=len(report.report_evaluator_failures),
        artifacts=artifact_files,
    )
    manifest_path.write_text(
        manifest.model_dump_json(indent=2) + "\n", encoding="utf-8"
    )
    return EvalArtifactPaths(
        report=output_path,
        rows=rows_path,
        summary=summary_path,
        manifest=manifest_path,
    )
