from __future__ import annotations

import io
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from eval_mutation import cli


class CliStatusTests(unittest.IsolatedAsyncioTestCase):
    async def test_triage_announces_start_on_stderr_before_result_json(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            database = Path(directory) / "tickets.db"
            args = cli._parser().parse_args(
                [
                    "triage",
                    "--db",
                    str(database),
                    "--request-id",
                    "request-1",
                    "--title",
                    "Test request",
                    "--body",
                    "Test body",
                    "--customer-id",
                    "customer-1",
                    "--model",
                    "gemma4:e4b",
                ]
            )
            result = MagicMock(consistent=True)
            result.model_dump_json.return_value = "{}"
            stdout = io.StringIO()
            stderr = io.StringIO()

            with (
                patch.object(cli, "run_triage", new=AsyncMock(return_value=result)),
                redirect_stdout(stdout),
                redirect_stderr(stderr),
            ):
                exit_code = await cli._triage(args, observability_enabled=True)

        self.assertEqual(exit_code, 0)
        self.assertEqual(stdout.getvalue(), "{}\n")
        status = stderr.getvalue()
        self.assertIn("[eval-mutation] triage started", status)
        self.assertIn("request_id=request-1", status)
        self.assertIn("model=gemma4:e4b", status)
        self.assertIn("request_timeout=120s", status)
        self.assertIn("observability=enabled", status)


if __name__ == "__main__":
    unittest.main()
