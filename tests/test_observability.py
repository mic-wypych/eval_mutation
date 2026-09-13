from __future__ import annotations

import os
import unittest
from unittest.mock import MagicMock, patch

import eval_mutation.observability as observability
from eval_mutation.observability import ObservabilityConfig


class ObservabilityTests(unittest.TestCase):
    def setUp(self) -> None:
        observability._configured = False

    def tearDown(self) -> None:
        observability._configured = False

    def test_environment_defaults_are_disabled_and_do_not_capture_content(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            config = ObservabilityConfig.from_environment()
        self.assertFalse(config.enabled)
        self.assertFalse(config.send_to_logfire)
        self.assertFalse(config.include_content)
        self.assertFalse(config.console)
        self.assertFalse(config.system_metrics)

    def test_disabled_configuration_does_not_touch_logfire(self) -> None:
        with (
            patch.object(observability.logfire, "configure") as configure,
            patch.object(observability.logfire, "instrument_pydantic_ai") as instrument,
        ):
            self.assertFalse(
                observability.configure_observability(ObservabilityConfig(enabled=False))
            )
        configure.assert_not_called()
        instrument.assert_not_called()

    def test_configuration_is_idempotent_and_content_is_explicit(self) -> None:
        config = ObservabilityConfig(
            enabled=True,
            send_to_logfire=False,
            include_content=True,
            system_metrics=True,
        )
        with (
            patch.object(observability.logfire, "configure") as configure,
            patch.object(observability.logfire, "instrument_pydantic_ai") as instrument,
            patch.object(observability.logfire, "instrument_system_metrics") as system_metrics,
        ):
            self.assertTrue(observability.configure_observability(config))
            self.assertTrue(observability.configure_observability(config))

        configure.assert_called_once()
        instrument.assert_called_once_with(include_content=True)
        system_metrics.assert_called_once_with()

    def test_invalid_boolean_is_rejected(self) -> None:
        with patch.dict(os.environ, {"LOGFIRE_ENABLED": "sometimes"}, clear=True):
            with self.assertRaisesRegex(ValueError, "LOGFIRE_ENABLED"):
                ObservabilityConfig.from_environment()

    def test_triage_span_is_a_noop_before_configuration(self) -> None:
        with patch.object(observability.logfire, "span") as logfire_span:
            with observability.triage_span(
                request_id="request-1",
                run_id="run-1",
                model_name="test:model",
                channel="email",
                account_tier="standard",
            ) as span:
                self.assertIsNone(span)
        logfire_span.assert_not_called()

    def test_triage_span_carries_only_operational_input_metadata(self) -> None:
        observability._configured = True
        emitted_span = MagicMock()
        span_context = MagicMock()
        span_context.__enter__.return_value = emitted_span
        with patch.object(
            observability.logfire, "span", return_value=span_context
        ) as logfire_span:
            with observability.triage_span(
                request_id="request-1",
                run_id="run-1",
                model_name="test:model",
                channel="email",
                account_tier="standard",
            ) as span:
                self.assertIs(span, emitted_span)

        logfire_span.assert_called_once_with(
            "triage request {request_id}",
            request_id="request-1",
            run_id="run-1",
            model_name="test:model",
            channel="email",
            account_tier="standard",
            _tags=("ticket-triage",),
        )


if __name__ == "__main__":
    unittest.main()
