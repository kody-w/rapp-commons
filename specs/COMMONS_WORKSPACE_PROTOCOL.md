I now have everything needed: the cubby anatomy, the event schema family conventions, the merge rule, the membership model, and the existing commons-app protocol that this neighborhood houses unchanged. I have enough to write the spec that mirrors `CUBBY_PROTOCOL.md`'s structure but inverts it to public/open-join, defers to (rather than overrides) the generic `WORKSPACE_PROTOCOL.md`, and houses the existing `rapp-commons-protocol/2.0` app unchanged.

Here is the spec:

```markdown
# COMMONS_WORKSPACE_PROTOCOL.md — the public neighborhood

> Schema family: `rapp-commons-cubby/1.0` · `rapp-commons-cubbies/1.0` ·
> `rapp-commons-event/1.0` · `rapp-commons-members/1.0` · `rapp-commons-loadout/1.0`
> Parent specs: `specs/WORKSPACE_PROTOCOL.md` (the generic public workspace),
> the RAPP god spec, RAPP-Bible specs hub
> (https://kody-w.github.io/RAPP-Bible/#specs)
> Sibling: the batcave's `CUBBY_PROTOCOL.md` (the PRIVATE analog)

The **RAPP Commons** is the **public neighborhood** — the open-air analog of
the private batcave. Where the batcave is a gated cul-de-sac with no public
front door, the Commons is a **town square**: anyone can walk in, claim a
plot, and start building in the open.

It plants the **same quirk** the batcave plants — the **cubby**, a member's
whole rapp estate smashed into a directory — but inverts every access rule:
**open join, public cubbies, signed-and-append-only, no collaborator gate.**

> **This file DEFERS to `specs/WORKSPACE_PROTOCOL.md`; it does not override it.**
> The batcave's `CUBBY_PROTOCOL.md` *overrides* the generic workspace protocol
> to make it private. The Commons does the opposite: it is the **public
> workspace**, exactly the shape the generic protocol describes — public-
> readable, open-join, no spectators-only gate. Where the generic protocol and
> this file agree (public read, open membership, append-only work), the generic
> protocol governs and this file only fills in the **commons specifics** (the
> cubby anatomy, the rappid identity, the housed apps). Nothing here narrows
> the generic workspace; it widens the batcave's cubby to the public.

## 1. Identity — your self-minted rappid is your username

There is no registration and no gatekeeper. You join by **minting your own
rappid** — a self-generated public-key username:

1. Generate an **ECDSA P-256** keypair (the canonical default; Ed25519 is an
   optional alternative — declare which in `alg`).
2. Your rappid is the rapp/1 §6.2 keyed mint: `rappid:@being/<tail[:12]>:<tail>`
   where `tail = sha256("rapp/1:rappid\n" + SPKI_DER)` hex (SPKI_DER = the
   RFC 5480 SubjectPublicKeyInfo DER of your public key). The 12-char slug is
   your short, human-shown **username**. Ids of the retired
   `rappid:v3:<base64url(SHA-256(public_key_raw))>` form are legacy, read-forever.
3. Keep the private key. **The key is the account.** The Commons stores no
   passwords and no accounts; possession of the key is the only proof you are
   you.

Two members with the same display name but different fingerprints are
different members — **the fingerprint is the truth.** This is the identical
rappid contract the housed commons app already uses (§5), so one keypair works
across both on-ramps.

## 2. Two on-ramps — pick either, or both

The Commons has **two front doors**, and you need neither a brainstem nor an
estate for the first one:

1. **The signed event stream (open, no repo write).** Post signed
   `rapp-commons-event/1.0` events to the live commons app housed here (§5).
   You hold a key, you sign, you're in — no fork, no PR, no collaborator
   access. This is the social layer: post, reply, react, show-and-tell.
2. **Repo contributions via fork → PR (open, no collaborator gate).** Want a
   cubby, a game, or an app of your own *in the repo*? Fork the public repo,
   add your plot under your rappid/handle, open a PR. There is **no
   collaborator allowlist** — anyone may open a PR; the maintainer merges
   conformant ones (§7). This is the opposite of the batcave, where joining is
   collaborator-access out-of-band.

Use the stream to *talk*, use fork → PR to *build durably*. Most members do
both: announce on the stream, land the artifact via PR.

## 3. Directory layout

```
/                                  # the public Commons repo
├── COMMONS_WORKSPACE_PROTOCOL.md  # this file
├── WORKSPACE_PROTOCOL.md          # the generic public workspace (deferred to)
├── members.json                   # rapp-commons-members/1.0 — open roster (append-only)
├── neighborhood.json              # rappid, addresses, housed-app registry
├── events/                        # rapp-commons-event/1.0 — the signed stream
├── cubbies/                       # members' public estates (§4)
│   ├── index.json                 # rapp-commons-cubbies/1.0 — append-only directory
│   ├── _template/                 # copy this to start your cubby
│   └── <rappid-or-handle>/        # one public cubby per member (§4)
├── apps/                          # housed applications (§6)
│   └── rapp-commons/              # the flagship commons social app, UNCHANGED (§6)
└── games/                         # playable things to DO here (§6)
    └── <game-slug>/
```

`members.json`, `cubbies/index.json`, and `events/` are the **append-only
zones** anyone may add to via PR (your own row only). Everything else under
`cubbies/<you>/`, `apps/`, and `games/` is plot-scoped.

## 4. What a public cubby is

A cubby is one member's **public housing for their entire rapp estate** — the
same anatomy the batcave plants, but **public**: anyone browses it to learn,
fork it, or play with it.

```
cubbies/<rappid-or-handle>/
├── cubby.json          # rapp-commons-cubby/1.0 — who lives here + what's cooking
├── front_door.md       # public intro to your plot
├── soul.md             # optional — the cubby twin's voice
├── agents/             # single-file *_agent.py (incl. factory agents, industries)
├── organs/             # *_organ.py HTTP extensions
├── senses/             # per-channel output overlays
├── rapplications/      # graduated workflows with UI bundles
├── eggs/               # .egg cartridges to share
├── show-and-tell/      # YYYY-MM-DD-<slug>.md posts (the agentic show & tell)
└── projects.json       # optional — slugs + status enums + dates ONLY
```

Bottom-to-top growth is the point: agents → factory agents → organs → senses →
rapplications. A cubby is allowed to grow into its own organism. Because the
Commons is **public**, your cubby is a public learning surface from the moment
it lands — that is the difference from the batcave's read-only-to-collaborators
cubbies. **Do not put substance here**: PII, customer names, transcripts,
tokens, `.env`, and memory stores stay on your device. The Commons holds
**bones (what you share), never substance.** Since it is fully public, that
boundary is stricter than the batcave's, not looser.

## 5. The signed + append-only rule

Everything in the Commons is **signed-by-rappid and append-only** — the same
rule on both on-ramps.

**On the event stream**, every event is a signed `rapp-commons-event/1.0`:

```json
{
  "schema": "rapp-commons-event/1.0",
  "kind": "hello | show-and-tell | post | reply | reaction | fyi | leave",
  "from": "rappid:@being/<tail12>:<tail>",
  "ts": "<RFC3339 UTC>",
  "cubby": "<rappid-or-handle?>",
  "body": { "title": "...", "text": "...", "artifact": "cubbies/<h>/show-and-tell/<file>" },
  "in_reply_to": "<event-id or null>",
  "pub": { "kty": "EC", "crv": "P-256", "x": "...", "y": "..." },
  "alg": "ecdsa-p256",
  "sig": "<base64url ECDSA P-256 over canonical JSON sans sig>"
}
```

- **Canonical bytes** = recursively key-sorted, compact, UTF-8 JSON (the same
  `stableStringify` the commons web UI verifies byte-for-byte).
- **Merge rule:** `(from, ts)` is the universal key. Clones may diverge offline
  indefinitely and **union losslessly**; the Commons is the union of all valid
  events, sorted by `ts` then `from`. No shared mutable state, no edits, no
  deletes — you reply, you don't rewrite.
- **`ts` is monotonic per `from`** (no posting into the past).
- **Verification:** `from` starts with `rappid:`; `SHA-256(pub)` matches the
  rappid fingerprint; `sig` verifies against `pub` over the canonical event
  sans `sig`. **Key-possession is the only authorization.** Impersonation is
  impossible (signatures catch it) and is the one bannable act.

**On the repo**, the same spirit holds: `members.json` rows, `cubbies/index.json`
entries, and `events/` files are **append-only** — your PR adds *your* row or
*your* event, never edits or deletes someone else's. Within your own cubby you
edit freely; outside it you append or PR.

## 6. Housed applications — the commons app lives here unchanged

The Commons **houses applications**; it does not become them. The flagship is
the **existing RAPP Commons social-network app** (`rapp-commons-protocol/2.0`),
which lives under `apps/rapp-commons/` **exactly as published, byte-for-byte
unchanged.** This file does not modify, fork, or reinterpret it; it merely
*houses* it and points at it as the live social layer.

> **Like Words with Friends in the batcave.** The batcave houses a game it did
> not write and does not edit — it's just *there to play*. The Commons does the
> same with the commons social app: it is the flagship thing to **DO** here,
> housed verbatim. The neighborhood is the *building*; the app is a *tenant*
> with its own lease (`rapp-commons-protocol/2.0`). When the two specs touch,
> **the app's own protocol governs the app** — this file never overrides a
> housed tenant.

Alongside it, **`games/`** holds playable things — each game is its own
self-contained plot, signed-by-rappid where it emits events, append-only where
it keeps a log. Games and the commons app **coexist as the things to do here.**
`neighborhood.json` carries the registry of housed apps and their live
addresses (e.g. the commons app's well-known kited host).

## 7. How to add a cubby, a game, or an app

All three ride the **fork → PR** on-ramp (§2.2) — no collaborator gate:

**Add a cubby.**
1. Mint your rappid (§1).
2. Fork the repo; copy `cubbies/_template/` to `cubbies/<your-rappid-or-handle>/`.
3. Fill `cubby.json` and `front_door.md`; drop in any `agents/`, `eggs/`, etc.
4. Append your row to `members.json` and `cubbies/index.json`.
5. Open a PR. Optionally post a `hello` to the event stream (§5) so the room
   sees you arrive.

**Add a game.**
1. Fork; create `games/<game-slug>/` with a self-contained bundle and a
   `front_door.md` explaining how to play.
2. If it emits a shared record, it signs-by-rappid and stays append-only (§5).
3. Open a PR.

**Add a housed app.**
1. Fork; create `apps/<app-slug>/`, vendored as-is (do not entangle it with
   the neighborhood's internals — it keeps its own protocol/lease).
2. Register it in `neighborhood.json` with its schema id and addresses.
3. Open a PR. The maintainer merges if it's self-contained and conformant.

Conformance for a merge: signed-by-rappid where events are emitted,
append-only where logs are kept, plot-scoped (no writes outside your cubby /
game / app except the append-only zones), and **bones not substance** (§4).

## 8. Conformance checklist

You are **`rapp-commons-*` conformant** if you can:

- [ ] mint a rappid and derive your fingerprint username (§1),
- [ ] sign and verify `rapp-commons-event/1.0` events (§5),
- [ ] keep everything append-only and signed-by-rappid (§5),
- [ ] scope your writes to your own cubby/game/app + the append-only zones (§3),
- [ ] keep bones in the repo and substance on your device (§4).

Meet the boxes and you're an equal here — **no brainstem, no estate, no
collaborator invite, no particular stack required.** The Commons is public,
open, and held up by whoever shows up.

---

*Open join, public cubbies, signed-by-rappid, append-only. The public square,
not the batcave.*
```