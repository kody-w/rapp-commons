#!/usr/bin/env python3
"""commons warehouse/build.py — the git-scraper SHAPER (Simon-Willison-style).

Every published frozen FRAME under live/<episode>/frameNN.state.json is a snapshot of the
commons' append-only SIGNED log at that instant. This script flattens all of them into a flat,
Datasette-ready warehouse and is re-run on each commit, so the GIT HISTORY of the warehouse files
becomes a queryable TIME-SERIES of the whole branching multiverse — who signed what, when, in
which episode/dimension, tracked commit over commit.

Emits (all additive, never touches the sacred commons app):
  warehouse/events.jsonl   — one row per UNIQUE signed event (deduped by sig+ts+from)
  warehouse/frames.jsonl   — one row per published frame (episode, idx, label, records, state path)
  warehouse/metadata.json  — Datasette metadata (so `datasette warehouse/ -m metadata.json` works)
  warehouse/stats.json     — rollups (counts by schema/kind/signer) — small + diff-friendly per commit

Usage:  python warehouse/build.py [repo_root]
Idempotent: re-running on the same data yields the same files (stable sort), so commits are clean.
"""
import os, sys, json, glob


def _root():
    return os.path.abspath(sys.argv[1]) if len(sys.argv) > 1 else os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _kind(r):
    return r.get("kind") or r.get("op") or r.get("act") or r.get("type") or "?"


def _detail(r):
    for k in ("body", "text", "title", "word", "block"):
        if r.get(k):
            return str(r[k])[:160]
    if r.get("x") is not None:
        return "@%s,%s" % (r.get("x"), r.get("z") if r.get("z") is not None else r.get("y"))
    if r.get("with"):
        return "with %s" % str(r["with"])[:40]
    return ""


def main():
    root = _root()
    live = os.path.join(root, "live")
    wh = os.path.join(root, "warehouse")
    os.makedirs(wh, exist_ok=True)

    events = {}   # key (sig|ts|from) -> row  (dedup across every published frame, all episodes)
    frames = []
    for state_path in sorted(glob.glob(os.path.join(live, "**", "*.state.json"), recursive=True)):
        rel = os.path.relpath(state_path, root)
        parts = rel.split(os.sep)
        # live/<episode>/frameNN.state.json
        episode = parts[1] if len(parts) >= 3 else "unknown"
        fname = os.path.basename(state_path)
        idx = "".join(c for c in fname if c.isdigit()) or "0"
        try:
            log = json.loads(open(state_path).read())
        except Exception:
            continue
        meta_path = os.path.join(os.path.dirname(state_path), "frames.json")
        label = ""
        if os.path.exists(meta_path):
            try:
                fm = {str(x.get("i")): x.get("label", "") for x in json.loads(open(meta_path).read())}
                label = fm.get(str(int(idx)), "")
            except Exception:
                pass
        frames.append({"episode": episode, "frame": int(idx), "label": label,
                       "records": len(log), "state": rel})
        for r in log:
            if not isinstance(r, dict):
                continue
            sig = str(r.get("sig") or "")
            key = "%s|%s|%s" % (sig[:24], r.get("ts"), str(r.get("from"))[:30])
            if key in events:
                # remember the EARLIEST episode/frame this signed event first appeared in
                continue
            events[key] = {
                "ts": r.get("ts"),
                "schema": r.get("schema"),
                "kind": _kind(r),
                "from": r.get("from"),
                "sig8": sig[:8],
                "detail": _detail(r),
                "first_episode": episode,
                "first_frame": int(idx),
            }

    rows = sorted(events.values(), key=lambda x: (x.get("ts") or 0, x.get("sig8") or ""))
    with open(os.path.join(wh, "events.jsonl"), "w") as f:
        for r in rows:
            f.write(json.dumps(r, sort_keys=True) + "\n")
    frames.sort(key=lambda x: (x["episode"], x["frame"]))
    with open(os.path.join(wh, "frames.jsonl"), "w") as f:
        for r in frames:
            f.write(json.dumps(r, sort_keys=True) + "\n")

    # rollups (small, diff-friendly — the part that visibly evolves commit-over-commit)
    by_schema, by_kind, by_signer, by_episode = {}, {}, {}, {}
    for r in rows:
        by_schema[r["schema"]] = by_schema.get(r["schema"], 0) + 1
        by_kind[r["kind"]] = by_kind.get(r["kind"], 0) + 1
        by_signer[r["from"]] = by_signer.get(r["from"], 0) + 1
        by_episode[r["first_episode"]] = by_episode.get(r["first_episode"], 0) + 1
    stats = {"total_events": len(rows), "total_frames": len(frames),
             "episodes": sorted(set(f["episode"] for f in frames)),
             "by_schema": dict(sorted(by_schema.items())),
             "by_kind": dict(sorted(by_kind.items())),
             "distinct_signers": len(by_signer),
             "by_episode": dict(sorted(by_episode.items()))}
    open(os.path.join(wh, "stats.json"), "w").write(json.dumps(stats, indent=2, sort_keys=True))

    # Datasette metadata so `datasette warehouse -m warehouse/metadata.json` just works
    metadata = {
        "title": "RAPP Commons — signed-event warehouse",
        "description": "A git-scraped time-series of every signed event in the Commons multiverse. "
                       "Each commit is a snapshot; git history is the time axis.",
        "license": "MIT",
        "source": "kody-w/rapp-commons",
        "databases": {"events": {"tables": {"events": {"sort_desc": "ts"}}}},
    }
    open(os.path.join(wh, "metadata.json"), "w").write(json.dumps(metadata, indent=2, sort_keys=True))
    # single-line summary on stdout so callers (the GitWarehouse agent) parse it cleanly.
    print(json.dumps({"status": "ok", "events": len(rows), "frames": len(frames),
                      "episodes": stats["episodes"], "signers": stats["distinct_signers"]}, sort_keys=True))


if __name__ == "__main__":
    main()
