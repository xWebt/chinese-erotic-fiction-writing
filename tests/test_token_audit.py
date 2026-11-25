import json
import tempfile
import unittest
from pathlib import Path

from harness.token_audit import audit_session


class TokenAuditTests(unittest.TestCase):
    def test_audits_latest_thread_usage(self):
        usage = {
            "input_tokens": 1000,
            "cached_input_tokens": 90_000,
            "output_tokens": 500,
            "reasoning_output_tokens": 100,
            "total_tokens": 91_500,
        }
        records = [
            {
                "type": "token_usage_record",
                "payload": {
                    "turn_id": "turn-1",
                    "usage": usage,
                    "thread_token_usage": usage,
                },
            }
        ]
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "session.jsonl"
            path.write_text(
                "\n".join(json.dumps(item) for item in records),
                encoding="utf-8",
            )
            report = audit_session(path, budget=50_000)
        self.assertEqual(report["thread"]["total_tokens"], 91_500)
        self.assertEqual(report["responses"], 1)
        self.assertTrue(report["warnings"])

    def test_missing_records(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "empty.jsonl"
            path.write_text("", encoding="utf-8")
            report = audit_session(path)
        self.assertIn("error", report)


if __name__ == "__main__":
    unittest.main()
