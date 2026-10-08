#!/usr/bin/env python3
"""Validate collected events against schema/event.schema.json.

Spec: docs/DASHBOARD_SPEC.md section 7. An invalid item is rejected and
recorded as an information gap ("פערי מידע"); valid items pass through.

Standard library only: the rules below mirror schema/event.schema.json.
Usage:
    python scripts/validate.py data/events.json
"""

import json
import sys
import uuid
from datetime import date, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCHEMA_PATH = ROOT / "schema" / "event.schema.json"


def load_schema(path=SCHEMA_PATH):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _is_number(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def _check_uuid(v):
    try:
        uuid.UUID(v)
        return True
    except (ValueError, AttributeError, TypeError):
        return False


def _check_date(v):
    try:
        date.fromisoformat(v)
        return len(v) == 10
    except (ValueError, TypeError):
        return False


def _check_datetime(v):
    if not isinstance(v, str) or "T" not in v:
        return False
    try:
        datetime.fromisoformat(v.replace("Z", "+00:00"))
        return True
    except ValueError:
        return False


def event_errors(event, schema=None):
    """Return a list of human-readable errors; empty means valid."""
    schema = schema or load_schema()
    if not isinstance(event, dict):
        return ["not an object"]
    errors = [f"missing field: {k}" for k in schema["required"] if k not in event]
    props = schema["properties"]
    get = event.get

    if "id" in event and not (isinstance(get("id"), str) and _check_uuid(get("id"))):
        errors.append("id: not a UUID")
    if "domain" in event and get("domain") not in props["domain"]["enum"]:
        errors.append(f"domain: unknown value {get('domain')!r}")
    if "date" in event and not _check_date(get("date")):
        errors.append("date: not YYYY-MM-DD")
    if "severity" in event:
        s = get("severity")
        if not (isinstance(s, int) and not isinstance(s, bool)
                and props["severity"]["minimum"] <= s <= props["severity"]["maximum"]):
            errors.append("severity: not an integer 1-5")
    for k in ("title", "source"):
        if k in event and not (isinstance(get(k), str) and get(k).strip()):
            errors.append(f"{k}: empty")
    if "url" in event and not (isinstance(get("url"), str)
                               and get("url").startswith(("http://", "https://"))):
        errors.append("url: not http(s)")
    for k in ("lat", "lon"):
        if k in event and get(k) is not None:
            v = get(k)
            if not (_is_number(v) and props[k]["minimum"] <= v <= props[k]["maximum"]):
                errors.append(f"{k}: out of range")
    if "lat" in event and "lon" in event and (get("lat") is None) != (get("lon") is None):
        errors.append("lat/lon: both or neither")
    if "collected_at" in event and not _check_datetime(get("collected_at")):
        errors.append("collected_at: not ISO-8601 date-time")
    return errors


def validate_events(events, schema=None):
    """Split events into (valid, gaps). Each gap: {index, id, errors}."""
    schema = schema or load_schema()
    valid, gaps = [], []
    for i, ev in enumerate(events):
        errs = event_errors(ev, schema)
        if errs:
            gaps.append({"index": i,
                         "id": ev.get("id") if isinstance(ev, dict) else None,
                         "errors": errs})
        else:
            valid.append(ev)
    return valid, gaps


def main(argv):
    if len(argv) != 2:
        print(__doc__, file=sys.stderr)
        return 2
    data = json.loads(Path(argv[1]).read_text(encoding="utf-8"))
    events = data["events"] if isinstance(data, dict) else data
    valid, gaps = validate_events(events)
    print(json.dumps({"valid": len(valid), "rejected": gaps}, ensure_ascii=False, indent=2))
    return 0 if not gaps else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
