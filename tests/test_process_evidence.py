from __future__ import annotations

import unittest

from eval_mutation.evals.task import _loaded_capability_ids


class ProcessEvidenceTests(unittest.TestCase):
    def test_capability_loads_are_extracted_from_dict_and_json_arguments(self) -> None:
        messages = [
            {
                "parts": [
                    {
                        "part_kind": "tool-call",
                        "tool_name": "load_capability",
                        "args": {"id": "routing-policy"},
                    },
                    {
                        "part_kind": "tool-call",
                        "tool_name": "search_tickets",
                        "args": {"query": "INC-42"},
                    },
                ]
            },
            {
                "parts": [
                    {
                        "part_kind": "tool-call",
                        "tool_name": "load_capability",
                        "args": '{"id":"urgency-policy"}',
                    },
                    {
                        "part_kind": "tool-call",
                        "tool_name": "load_capability",
                        "args": {"id": "routing-policy"},
                    },
                ]
            },
        ]

        self.assertEqual(
            _loaded_capability_ids(messages),
            ["routing-policy", "urgency-policy"],
        )


if __name__ == "__main__":
    unittest.main()
