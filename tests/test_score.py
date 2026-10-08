"""Unit tests for scripts/score.py. All inputs are DUMMY numbers, not real data."""

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import score  # noqa: E402

DUMMY_HISTORY = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]  # DUMMY


class MathTest(unittest.TestCase):
    def test_percentile_rank(self):
        self.assertEqual(score.percentile_rank(0, DUMMY_HISTORY), 0.0)
        self.assertEqual(score.percentile_rank(11, DUMMY_HISTORY), 1.0)
        # 4 below, 1 equal -> (4 + 0.5) / 10
        self.assertAlmostEqual(score.percentile_rank(5, DUMMY_HISTORY), 0.45)

    def test_to_score_range(self):
        self.assertEqual(score.to_score(0.0), 1.0)
        self.assertEqual(score.to_score(1.0), 10.0)
        self.assertAlmostEqual(score.to_score(0.5), 5.5)

    def test_weighted_sum(self):
        # 8*0.5 + 4*0.5 = 6.0
        self.assertAlmostEqual(score.weighted_sum({"a": 8, "b": 4}, {"a": 0.5, "b": 0.5}), 6.0)

    def test_config_weights_sum_to_one(self):
        cfg = score.load_config()
        self.assertAlmostEqual(sum(d["weight"] for d in cfg["domains"]), 1.0)


class LabelTrendTest(unittest.TestCase):
    def setUp(self):
        self.labels = score.load_config()["labels"]

    def test_label_boundaries(self):
        cases = {8.0: "גבוה מאוד", 7.96: "גבוה מאוד", 7.9: "גבוה", 7.0: "גבוה",
                 6.94: "בינוני-גבוה", 6.0: "בינוני-גבוה", 5.9: "בינוני-נמוך",
                 4.0: "בינוני-נמוך", 3.9: "נמוך", 1.0: "נמוך"}
        for s, expected in cases.items():
            self.assertEqual(score.label_for(s, self.labels)["label"], expected, s)

    def test_trend(self):
        self.assertIsNone(score.trend(5.0, None, 0.3))
        self.assertEqual(score.trend(5.3, 5.0, 0.3)["direction"], "flat")
        self.assertEqual(score.trend(5.31, 5.0, 0.3)["direction"], "up")
        self.assertEqual(score.trend(4.6, 5.0, 0.3)["direction"], "down")


class ComputeTest(unittest.TestCase):
    def setUp(self):
        self.cfg = score.load_config()

    def dummy_input(self, value):
        return {"domains": {d["id"]: {"value": value, "history": DUMMY_HISTORY}
                            for d in self.cfg["domains"]}}

    def test_no_baseline(self):
        out = score.compute({"domains": {"cyber": {"value": 3, "history": [1]}}}, self.cfg)
        self.assertIsNone(out["overall"])
        self.assertFalse(out["domains"]["cyber"]["baseline"])
        self.assertEqual(out["domains"]["cyber"]["status"], score.NO_BASELINE)
        self.assertEqual(out["domains"]["kinetic"]["status"], score.NO_DATA)
        self.assertEqual(len(out["gaps"]), len(self.cfg["domains"]))

    def test_overall_is_weighted_sum_of_domains(self):
        out = score.compute(self.dummy_input(5), self.cfg)
        # every domain: p = 0.45 -> 1 + 9*0.45 = 5.05; weights sum to 1 -> overall 5.05
        for d in out["domains"].values():
            self.assertAlmostEqual(d["score"], 5.05)
        self.assertAlmostEqual(out["overall"]["score"], 5.05)
        self.assertEqual(out["overall"]["label"], "בינוני-נמוך")
        self.assertEqual(out["gaps"], [])

    def test_overall_matches_displayed_domains(self):
        raw = self.dummy_input(5)
        raw["domains"]["cyber"]["value"] = 11  # DUMMY: p = 1.0 -> 10.0
        out = score.compute(raw, self.cfg)
        expected = sum(d["score"] * d["weight"] for d in out["domains"].values())
        self.assertAlmostEqual(out["overall"]["score"], round(expected, 2))

    def test_trend_against_previous(self):
        prev = score.compute(self.dummy_input(5), self.cfg)
        cur = score.compute(self.dummy_input(11), self.cfg, previous=prev)
        self.assertEqual(cur["overall"]["trend"]["direction"], "up")
        self.assertEqual(cur["domains"]["cyber"]["trend"]["diff"], 4.95)


if __name__ == "__main__":
    unittest.main()
