# RAPP Commons — bundled spec pointer

This file exists per the **specs-travel-with-planting** rule (CONSTITUTION Article XLVI / bundle 2.0.0 / `tools/front_door_specs.py`): every planted repo MUST contain enough governance to stay in-contract without reaching back to the parent tree.

For the commons, the load-bearing extensions of the parent RAPP spec are:

- `rapp-neighborhood/1.0` — the manifest format used by this neighborhood's `neighborhood.json`. Carries: rappid, urls{}, coordinates{physical, virtual}, quirks{}, join_flow{}, soul_summary.
- `brainstem-egg/2.3-neighborhood` — the invite egg cartridge format. JSON-only (no ZIP), small enough to fit in a QR code. Carries: rappid + neighborhood_url + neighborhood_json + tether_url + soul_summary. The `egg_hatcher_agent.py` (RAR `@rapp/egg_hatcher` v1.1.0+) routes these by writing `{rappid, added_at, via: "egg"}` to the joining operator's two-tier estate.
- `rapp-commons-event/1.0` — the append-only signed event format. See `events/SCHEMA.md` in this repo.
- `rapp-virtual-space/1.0` — the virtual coordinate space format. Carries: bounds, spawn, movement, occupancy_cap, render_hint. The commons uses `type: town-square`.

The canonical parent spec lives at `https://github.com/kody-w/RAPP/blob/main/pages/docs/SPEC.md` and is mirrored at `pages/docs/SPEC.md` in any clone of that repo. **If the parent is unreachable**, the rules above are sufficient to operate this neighborhood in-contract.

## Constitutional anchors

- **Article XLVI** — rappid IS the global address; estate entries store ONLY `{rappid, added_at, via}`; no per-consumer parsers.
- **Article XLVII + .5/.5.1/.5.2/.5.3** — substrate-agnostic federation; this neighborhood is reachable over github raw, GitHub Pages, LAN HTTP, AirDrop'd egg, and sneakernet file://.
- **Article XLVIII** — two-tier estate; the operator joining keeps their public + private estates separate; private path is opaque.
- **Article L** — `.egg` is the universal portable unit; one extension, one hatcher, refuses on unknown kinds.
- **Article LI** — every neighborhood front gate (`index.html` at repo root) MUST display a tether QR on first paint. The commons conforms — `index.html` includes the canonical `rapp-front-gate-qr/1.0` snippet (QRious-rendered, encodes `.well-known/neighborhood.egg`, gracefully degrades to plain-URL text when the CDN is unreachable). See `pages/docs/QR_FRONT_GATE.md` in the parent RAPP repo for the spec.

## Antipatterns inherited from upstream

- ❌ Don't generalize per-pattern primitives across all neighborhoods. The commons quirk is `event-stream-only`. Other neighborhoods have their own.
- ❌ Don't reinvent rappid parsing. Single parser, single source of truth.
- ❌ Don't introduce shared mutable state into the commons. If you need it, plant a new neighborhood.

## Why this file is short

Because the canonical god spec is large and we don't want every planted repo to drift on its copy. The bundle 2.0.0 rule says the planting carries `specs/SPEC.md` + `specs/skill.md` + `specs/<KIND>_PROTOCOL.md`. For the commons, this short pointer is the SPEC.md — the load-bearing rules (above) are the only ones the commons specifically extends. Everything else is read from the parent spec when reachable, and from the upstream RAPP repo's `pages/docs/SPEC.md` (cached in any local clone) when not.
