"""Unit tests for scripts/validate.py. Fixtures are DUMMY data, not real events."""

import copy
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import validate  # noqa: E402

FIXTURE = ROOT / "tests" / "fixtures" / "DUMMY_events.json"


class ValidateTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.events = json.loads(FIXTURE.read_text(encoding="utf-8"))["events"]

    def test_split_valid_and_gaps(self):
        valid, gaps = validate.validate_events(self.events)
        self.assertEqual([e["id"][-1] for e in valid], ["1", "2"])
        self.assertEqual([g["index"] for g in gaps], [2, 3])

    def test_invalid_item_reasons(self):
        errs = validate.event_errors(self.events[2])
        for expected in ("id: not a UUID", "severity: not an integer 1-5", "url: not http(s)",
                         "lat/lon: both or neither", "collected_at: not ISO-8601 date-time"):
            self.assertIn(expected, errs)

    def test_missing_field_and_unknown_domain(self):
        errs = validate.event_errors(self.events[3])
        self.assertIn("missing field: url", errs)
        self.assertIn("domain: unknown value 'earthquake'", errs)
        self.assertIn("title: empty", errs)

    def test_bool_severity_rejected(self):
        ev = copy.deepcopy(self.events[0])
        ev["severity"] = True
        self.assertIn("severity: not an integer 1-5", validate.event_errors(ev))

    def test_schema_domains_match_config(self):
        cfg = json.loads((ROOT / "config" / "scoring.json").read_text(encoding="utf-8"))
        schema = validate.load_schema()
        self.assertEqual(sorted(d["id"] for d in cfg["domains"]),
                         sorted(schema["properties"]["domain"]["enum"]))


if __name__ == "__main__":
    unittest.main()
