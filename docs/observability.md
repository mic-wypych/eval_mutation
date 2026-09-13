# Logfire observability

Both command-line entry points can configure Logfire before building the Pydantic AI
agent. Pydantic AI instrumentation records the agent run, model requests, tool calls,
retries, durations, and token usage. A project-level `triage request` span groups those
events and adds the request ID, run ID, model, route, urgency, and aggregate usage.

Both entry points immediately print a flushed `started` status line to stderr. This
keeps the final JSON/report on stdout machine-readable while making slow local model
runs visibly active and showing whether observability was configured.

Observability and remote export are both disabled by default. Enable them explicitly
after reviewing the data policy for the tickets being processed:

```bash
LOGFIRE_ENABLED=true \
LOGFIRE_SEND_TO_LOGFIRE=true \
uv run python -m eval_mutation triage ...
```

The default content policy remains conservative even when tracing is enabled:

- request, response, and tool content is not attached to telemetry;
- customer IDs, ticket titles, and ticket bodies are not project-span attributes;
- console telemetry and system metrics are disabled.

Set `LOGFIRE_INCLUDE_CONTENT=true` only for synthetic or otherwise approved data when
you need the full Pydantic AI conversation and tool payloads.

## Environment controls

| Variable | Default | Purpose |
|---|---|---|
| `LOGFIRE_ENABLED` | `false` | Enable project-managed Logfire setup. |
| `LOGFIRE_SEND_TO_LOGFIRE` | `false` | Accepts `true`, `false`, or `if-token-present`. |
| `LOGFIRE_SERVICE_NAME` | `eval-mutation` | Service name attached to telemetry. |
| `LOGFIRE_ENVIRONMENT` | unset | Optional environment label such as `development`. |
| `LOGFIRE_INCLUDE_CONTENT` | `false` | Include Pydantic AI prompt, response, and tool content. |
| `LOGFIRE_CONSOLE` | `false` | Enable Logfire console output. |
| `LOGFIRE_SYSTEM_METRICS` | `false` | Enable host system metrics. |

To inspect spans locally without remote export, set `LOGFIRE_ENABLED=true`,
`LOGFIRE_CONSOLE=true`, and leave `LOGFIRE_SEND_TO_LOGFIRE=false`.
