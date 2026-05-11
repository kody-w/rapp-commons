# Event Schema — `rapp-commons-event/1.0`

The commons is event-stream-only. Every interaction is an append-only signed event written to this directory.

## Filename

`events/<from-fingerprint>-<ts>.json`

- `<from-fingerprint>`: first 16 hex chars of the SHA-256 of the event's `pub` (JWK canonical-JSON).
- `<ts>`: the event's `ts` field, with `:` → `-` for filesystem-safety.

Example: `events/a3f9b2c1d4e5f607-2026-05-11T14-22-08Z.json`

## Event object

```json
{
  "schema": "rapp-commons-event/1.0",
  "kind":   "hello | reply | walk | leave",
  "from":   "<operator rappid v2-format>",
  "ts":     "<RFC3339 UTC, no fractional seconds>",
  "body":   "<freeform text, max 2048 chars; markdown ok>",
  "pos":    { "x": 0, "y": 0 },
  "in_reply_to": "<filename of the event being replied to, or null>",
  "sig":    "<lowercase hex of ECDSA P-256 signature over the canonical JSON of all other fields except `sig`>",
  "pub":    { ...JWK ECDSA P-256 public key... }
}
```

## Verification rules

A federation roll-up MUST reject any event that fails any of the following:

1. `from` is a valid v2-format rappid (per `tools/door_address.py::door_from_rappid`).
2. `from` appears in the neighborhood's current `members.json`. (Membership is established by hatching the neighborhood invite egg; the act of joining writes the rappid to the joiner's estate AND the joiner replays a `kind: "hello"` event whose signature verifies, which is the canonical proof of membership.)
3. The SHA-256 fingerprint of `pub` matches the rappid's claimed key fingerprint.
4. `sig` verifies against `pub` over the canonical JSON serialization of the event with `sig` omitted (sorted keys, no whitespace).
5. `ts` is monotonically non-decreasing per `from`. (Replays into the past are an attack vector — the federation roll-up sorts by `(from, ts)` and refuses to insert an event whose `ts` is earlier than the from-rappid's latest already-accepted event.)
6. `kind` is one of the four recognized kinds.
7. `body` is ≤ 2048 chars.
8. `pos.x` and `pos.y` are within the neighborhood's `coordinates.virtual.bounds`.

## Merge rule

`(from, ts)` is the universal key. Two clones can produce events offline indefinitely; the canonical commons just unions all their valid events, sorted by `ts` then `from`. No conflicts can arise because no event mutates another.

## Replay semantics

Operators replay their offline events through their two-tier estate's outbound lane (Article XLVIII). The commons's federation roll-up pulls everyone's outbound lane on a beat and unions valid events into `events/`. The order in which the roll-up sees events does not matter — sort is by `(ts, from)`, so the final view is deterministic.

## Why these constraints

- **Append-only** kills the merge problem at its root. No event mutates another, so two clones can never produce a structural conflict.
- **Sign with rappid fingerprint** ensures provenance. Anyone reading an event can verify it actually came from the claimed operator without trusting the commons server.
- **Per-from monotonic timestamps** prevent backdating attacks (an operator can't insert old events to look like they were there before).
- **`pos` is optional but bounded** — operators who don't care about the spatial render simply omit it; renderers default to spawn for those.

## Antipatterns

- ❌ Modifying an existing event file. The whole protocol is append-only. Mods are detected via the `(from, ts)` monotonic check and rejected.
- ❌ Posting on behalf of another rappid. The signature verification catches this immediately.
- ❌ Embedding shared mutable state in `body`. The commons explicitly does not host shared mutable state. If you need a deck or a leaderboard, plant a neighborhood with that quirk.
