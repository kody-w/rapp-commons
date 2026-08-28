#!/usr/bin/env python3
"""harvest_commons_events.py — Static Data Covenant harvester for the
commons_almanac rapp (rapps/commons_almanac/index.html).

That page used to list events/ and fetch each event file from the visitor's
browser via the GitHub contents API (`${api}/contents/events`, then a
download_url fetch per file). It now reads one committed rollup snapshot
(rapps/commons_almanac/data/events.json) instead.

This is a *local* harvest, not an API harvest: CI already has the full repo
checked out, so this script reads events/*.json straight off disk — no
network call, no rate limit, no api.github.com dependency at all. Any
neighborhood that drops commons_almanac into its own rapps/ should copy this
script (or an equivalent) into its own CI so its own events/ gets harvested
into its own rapps/commons_almanac/data/events.json.
"""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EVENTS_DIR = ROOT / "events"
OUT = ROOT / "rapps" / "commons_almanac" / "data" / "events.json"
MAX_EVENTS = 500  # keep the snapshot bounded; the page itself only ever showed 50


def main():
    events = []
    if EVENTS_DIR.is_dir():
        for f in sorted(EVENTS_DIR.glob("*.json")):
            if f.name == "SCHEMA.md":
                continue
            try:
                events.append(json.loads(f.read_text()))
            except Exception as e:
                print(f"! skipping unparseable event file {f.name}: {e}")

    events.sort(key=lambda e: e.get("ts", ""), reverse=True)
    events = events[:MAX_EVENTS]

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(events, indent=1) + "\n")
    print(f"✓ {OUT.relative_to(ROOT)} — {len(events)} events harvested from {EVENTS_DIR.relative_to(ROOT)}/")
    return 0


if __name__ == "__main__":
    sys.exit(main())
