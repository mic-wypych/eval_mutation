from __future__ import annotations

import argparse
import asyncio
from pathlib import Path

from pydantic_evals.reporting import EvaluationReportAdapter

from eval_mutation.agent.triage_agent import AgentConfig
from eval_mutation.evals.dataset import load_dataset
from eval_mutation.evals.task import TriageEvalTask


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


async def _run(args: argparse.Namespace) -> int:
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
    task = TriageEvalTask(config=config, project_root=args.project_root)
    report = await dataset.evaluate(
        task,
        name=f"{dataset.name}:{config.model_name}",
        max_concurrency=args.max_concurrency,
        progress=not args.no_progress,
        repeat=args.repeat,
        metadata={
            "dataset_path": str(args.dataset),
            "model": config.model_dump(mode="json"),
        },
    )
    report.print(include_reasons=True)

    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_bytes(EvaluationReportAdapter.dump_json(report, indent=2))

    integrated_failures = [
        case.name
        for case in report.cases
        if (result := case.assertions.get("integrated_success")) is not None and not result.value
    ]
    return 2 if report.failures or integrated_failures else 0


def main(argv: list[str] | None = None) -> int:
    return asyncio.run(_run(_parser().parse_args(argv)))
