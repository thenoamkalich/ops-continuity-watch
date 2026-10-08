#!/usr/bin/env python3
"""Compute domain scores (1-10), the overall index, labels and trend.

Method: docs/DASHBOARD_SPEC.md section 4. Weights, labels and thresholds
live in config/scoring.json (proposal, not yet approved).

1. Domain score = percentile rank of this period's raw value against the
   domain's reference history, mapped linearly: score = 1 + 9 * p.
   p = (count below + 0.5 * count equal) / n.
2. History shorter than min_history_points: baseline false, no score,
   shown as "אין בסיס להשוואה".
3. Overall = sum(score * weight). Computed only when every domain has a
   score; otherwise null, and the missing domains are listed as gaps.
4. Label from the score rounded to one decimal.
5. Trend = current - previous; an arrow only when |diff| > trend_threshold.

Input JSON:  {"domains": {"<id>": {"value": <number>, "history": [<number>, ...]}}}
Usage:
    python scripts/score.py --input raw.json [--previous data/summary.json] [--out data/summary.json]
"""

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = ROOT / "config" / "scoring.json"
NO_BASELINE = "אין בסיס להשוואה"
NO_DATA = "אין נתונים"


def load_config(path=CONFIG_PATH):
    cfg = json.loads(Path(path).read_text(encoding="utf-8"))
    total = sum(d["weight"] for d in cfg["domains"])
    if abs(total - 1.0) > 1e-9:
        raise ValueError(f"domain weights sum to {total}, expected 1.0")
    return cfg


def percentile_rank(value, history):
    """Fraction in [0, 1] of history at or below value (ties count half)."""
    if not history:
        raise ValueError("empty history")
    below = sum(1 for h in history if h < value)
    equal = sum(1 for h in history if h == value)
    return (below + 0.5 * equal) / len(history)


def to_score(p):
    """Map a percentile in [0, 1] linearly to 1-10."""
    return 1.0 + 9.0 * p


def label_for(score, labels):
    """Return the label entry for a score, using its one-decimal rounding."""
    s = round(score, 1)
    for entry in sorted(labels, key=lambda e: e["min"], reverse=True):
        if s >= entry["min"]:
            return entry
    return sorted(labels, key=lambda e: e["min"])[0]


def trend(current, previous, threshold):
    if current is None or previous is None:
        return None
    diff = round(current - previous, 6)
    direction = "up" if diff > threshold else "down" if diff < -threshold else "flat"
    return {"diff": round(diff, 2), "direction": direction}


def weighted_sum(scores, weights):
    """sum(score * weight) over the keys of weights; scores must cover them all."""
    return sum(scores[k] * w for k, w in weights.items())


def score_domain(raw, cfg):
    """raw: {"value", "history"} or None. Returns the domain result dict."""
    if raw is None or raw.get("value") is None:
        return {"baseline": False, "score": None, "status": NO_DATA}
    history = raw.get("history") or []
    if len(history) < cfg["min_history_points"]:
        return {"baseline": False, "score": None, "value": raw["value"],
                "history_points": len(history), "status": NO_BASELINE}
    p = percentile_rank(raw["value"], history)
    score = to_score(p)
    lab = label_for(score, cfg["labels"])
    return {"baseline": True, "value": raw["value"], "history_points": len(history),
            "percentile": round(p, 4), "score": round(score, 2),
            "label": lab["label"], "color": lab["color"]}


def compute(raw_input, cfg, previous=None):
    raw_domains = raw_input.get("domains", {})
    prev_domains = (previous or {}).get("domains", {})
    domains, gaps = {}, []
    for d in cfg["domains"]:
        res = score_domain(raw_domains.get(d["id"]), cfg)
        res.update({"name": d["name"], "weight": d["weight"]})
        prev_score = prev_domains.get(d["id"], {}).get("score")
        res["trend"] = trend(res["score"], prev_score, cfg["trend_threshold"])
        if res["score"] is None:
            gaps.append({"domain": d["id"], "reason": res["status"]})
        domains[d["id"]] = res

    overall = None
    if not gaps:
        value = weighted_sum({k: v["score"] for k, v in domains.items()},
                             {d["id"]: d["weight"] for d in cfg["domains"]})
        lab = label_for(value, cfg["labels"])
        prev_overall = ((previous or {}).get("overall") or {}).get("score")
        overall = {"score": round(value, 2), "label": lab["label"], "color": lab["color"],
                   "trend": trend(value, prev_overall, cfg["trend_threshold"])}
    return {
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0)
                        .isoformat().replace("+00:00", "Z"),
        "method": "docs/DASHBOARD_SPEC.md section 4; config/scoring.json",
        "overall": overall,
        "domains": domains,
        "gaps": gaps,
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--input", required=True)
    ap.add_argument("--previous")
    ap.add_argument("--out")
    args = ap.parse_args()
    cfg = load_config()
    raw = json.loads(Path(args.input).read_text(encoding="utf-8"))
    prev = None
    if args.previous and Path(args.previous).exists():
        prev = json.loads(Path(args.previous).read_text(encoding="utf-8"))
    text = json.dumps(compute(raw, cfg, prev), ensure_ascii=False, indent=2) + "\n"
    if args.out:
        Path(args.out).write_text(text, encoding="utf-8")
    else:
        sys.stdout.write(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
