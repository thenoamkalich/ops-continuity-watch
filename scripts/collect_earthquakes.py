#!/usr/bin/env python3
"""Collect earthquakes from the EMSC FDSN event service for three regions.

Source: EMSC-CSEM SeismicPortal, https://www.seismicportal.eu (CC BY 4.0).
Regions and thresholds are the proposals in HANDOFF.md (not yet approved).

Output: data/earthquakes.json. Each event has domain, date, severity, title,
link, plus the raw values it was built from. severity is the EMSC magnitude
as reported; no scoring happens here.

Standard library only. Usage:
    python scripts/collect_earthquakes.py [--days 7] [--out data/earthquakes.json]
"""

import argparse
import json
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

FDSN_URL = "https://www.seismicportal.eu/fdsnws/event/1/query"
EVENT_URL = "https://www.seismicportal.eu/eventdetails.html?unid={unid}"
CREDIT = "Credit: EMSC-CSEM SeismicPortal, https://www.seismicportal.eu"
USER_AGENT = "ops-continuity-watch (+https://github.com/thenoamkalich/ops-continuity-watch)"

# Proposal from HANDOFF.md, to be calibrated against real data.
# Boxes overlap: an Israel event can also match "neighbors" and "world".
REGIONS = [
    {"id": "israel", "name": "ישראל", "minmag": 2.5,
     "box": {"minlat": 29.3, "maxlat": 33.5, "minlon": 34.2, "maxlon": 35.9}},
    {"id": "neighbors", "name": "שכנות והשבר הסורי-אפריקאי", "minmag": 3.5,
     "box": {"minlat": 27.0, "maxlat": 37.5, "minlon": 31.0, "maxlon": 42.0}},
    {"id": "world", "name": "עולם", "minmag": 6.0, "box": None},
]


def fdsn_time(dt):
    return dt.strftime("%Y-%m-%dT%H:%M:%S")


def query_region(region, start, end, timeout=60):
    params = {
        "format": "json",
        "starttime": fdsn_time(start),
        "endtime": fdsn_time(end),
        "minmag": region["minmag"],
        "orderby": "time",
        "limit": 20000,
    }
    if region["box"]:
        params.update(region["box"])
    url = FDSN_URL + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        # FDSN returns 204 No Content when nothing matches.
        if resp.status == 204:
            return url, []
        body = resp.read()
    if not body.strip():
        return url, []
    return url, json.loads(body).get("features", [])


def to_event(feature, region):
    p = feature["properties"]
    unid = p["unid"]
    mag = p["mag"]
    place = p.get("flynn_region") or ""
    return {
        "domain": "earthquake",
        "date": p["time"],
        "severity": mag,
        "title": f"M{mag} {place}".strip(),
        "link": EVENT_URL.format(unid=unid),
        "region": region["id"],
        "magnitude": mag,
        "magtype": p.get("magtype"),
        "lat": p.get("lat"),
        "lon": p.get("lon"),
        "depth_km": p.get("depth"),
        "emsc_unid": unid,
        "source": "EMSC",
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--days", type=int, default=7, help="look-back window in days (default 7)")
    ap.add_argument("--out", default="data/earthquakes.json")
    args = ap.parse_args()

    end = datetime.now(timezone.utc).replace(microsecond=0)
    start = end - timedelta(days=args.days)

    events, queries = [], []
    for region in REGIONS:
        try:
            url, features = query_region(region, start, end)
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as e:
            print(f"ERROR {region['id']}: {e}", file=sys.stderr)
            return 1
        region_events = [to_event(f, region) for f in features]
        events.extend(region_events)
        queries.append({"region": region["id"], "name": region["name"],
                        "minmag": region["minmag"], "box": region["box"],
                        "count": len(region_events), "query_url": url})
        print(f"{region['id']}: {len(region_events)} events")

    events.sort(key=lambda e: e["date"], reverse=True)
    out = {
        "generated_at": end.isoformat().replace("+00:00", "Z"),
        "window": {"start": start.isoformat().replace("+00:00", "Z"),
                   "end": end.isoformat().replace("+00:00", "Z")},
        "source": FDSN_URL,
        "license": "CC BY 4.0",
        "credit": CREDIT,
        "queries": queries,
        "events": events,
    }
    path = Path(args.out)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {len(events)} events to {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
