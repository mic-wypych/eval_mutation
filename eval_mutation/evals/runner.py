from __future__ import annotations

import argparse
import asyncio
import sys
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from eval_mutation.agent.triage_agent import AgentConfig
from eval_mutation.evals.artifacts import write_eval_artifacts
from eval_mutation.evals.dataset import load_dataset
from eval_mutation.evals.task import TriageEvalTask
from eval_mutation.observability import configure_observability


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run ticket-triage Pydantic Evals cases.")
    parser.add_argument("--dataset", type=Path, default=Path("datasets/development.yaml"))
    parser.add_argument("--case", action="append", dest="case_names", default=[])
    parser.add_argument("--project-root", type=Path, default=Path("."))
    parser.add_argument("--model", default=None)
    parser.add_argument("--base-url", default=None)
    parser.add_argument("--max-tokens", type=int, default=None)
    parser.add_argument("--request-limit", type=int, default=None)
    parser.add_argument("--tool-calls-limit", type=int, default=None)
    parser.add_argument("--timeout-seconds", type=float, default=None)
    parser.add_argument("--repeat", type=int, default=1)
    parser.add_argument("--max-concurrency", type=int, default=1)
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument("--run-id", default=None)
    parser.add_argument("--no-progress", action="store_true")
    return parser


def _config(args: argparse.Namespace) -> AgentConfig:
    config = AgentConfig.from_environment()
    for argument, field_name in (
        (args.model, "model_name"),
        (args.base_url, "base_url"),
        (args.max_tokens, "max_tokens"),
        (args.request_limit, "request_limit"),
        (args.tool_calls_limit, "tool_calls_limit"),
        (args.timeout_seconds, "timeout_seconds"),
    ):
        if argument is not None:
            setattr(config, field_name, argument)
    return config


async def _run(args: argparse.Namespace, *, observability_enabled: bool = False) -> int:
    if args.repeat < 1:
        raise ValueError("--repeat must be at least 1")
    if args.max_concurrency < 1:
        raise ValueError("--max-concurrency must be at least 1")

    dataset = load_dataset(args.dataset)
    if args.case_names:
        requested = set(args.case_names)
        available = {case.name for case in dataset.cases}
        missing = sorted(requested - available)
        if missing:
            raise ValueError(f"unknown case names: {missing}; available={sorted(available)}")
        dataset.cases = [case for case in dataset.cases if case.name in requested]

    config = _config(args)
    run_id = args.run_id or (
        f"eval-{datetime.now(UTC).strftime('%Y%m%dT%H%M%SZ')}-{uuid4().hex[:8]}"
    )
    print(
        "[eval-mutation] eval started "
        f"run_id={run_id} dataset={args.dataset} cases={len(dataset.cases)} model={config.model_name} "
        f"repeat={args.repeat} concurrency={args.max_concurrency} "
        f"observability={'enabled' if observability_enabled else 'disabled'}",
        file=sys.stderr,
        flush=True,
    )
    task = TriageEvalTask(config=config, project_root=args.project_root)
    report = await dataset.evaluate(
        task,
        name=f"{dataset.name}:{config.model_name}",
        max_concurrency=args.max_concurrency,
        progress=not args.no_progress,
        repeat=args.repeat,
        metadata={
            "run_id": run_id,
            "dataset_path": str(args.dataset),
            "model": config.model_dump(mode="json"),
        },
    )
    report.print(include_reasons=True)

    if args.output is not None:
        paths = write_eval_artifacts(
            report=report,
            dataset=dataset,
            dataset_path=args.dataset,
            output_path=args.output,
            config=config,
            project_root=args.project_root,
            run_id=run_id,
            repeat=args.repeat,
            max_concurrency=args.max_concurrency,
            observability_enabled=observability_enabled,
        )
        print(
            f"[eval-mutation] artifacts written manifest={paths.manifest} rows={paths.rows} ",
            f"summary={paths.summary} report={paths.report}",
            file=sys.stderr,
            flush=True,
        )

    integrated_failures = [
        case.name
        for case in report.cases
        if (result := case.assertions.get("integrated_success")) is not None and not result.value
    ]
    return 2 if report.failures or integrated_failures else 0


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    observability_enabled = configure_observability()
    return asyncio.run(_run(args, observability_enabled=observability_enabled))
