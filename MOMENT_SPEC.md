<!-- (c) 2026 Kody Wildfeuer · PolyForm Noncommercial 1.0.0 · "Moment", "Holographic Moment", "The RAPP Zoo" are trademarks -->

# RAPP Moment — Specification

**Version 1.0 · status: living · part of the RAPP ecosystem**

> **Own the moment.** Every instant in time mints one — and only one — living holographic organism. It breathes, it grows, and it is provably yours. Forever, from anywhere, with no server.

---

## 0. Philosophy

RAPP Moment is a **serverless social network of living holographic organisms**. It has three non-negotiable properties:

1. **Serverless.** All state is static data committed to a public git repository and served from a CDN (GitHub Pages / `raw.githubusercontent.com`). Every query — feed, search, analytics, ownership, history — runs **client-side in the browser**. There is no backend, no database, no account system.
2. **Cryptographic, not custodial.** Identity is a keypair. Ownership is a signature. There are no usernames or passwords; a **key is an identity**.
3. **Alive.** A post is not a video or an image. It is a **digital organism** with a heartbeat, a genome, growth over time, homeostasis, mortality, lineage, and a provable birth.

The unit, the post, the slice of time, and the living thing are all the same word: a **Moment**.

---

## 1. The Moment

A **Moment** is a walkable 3D hologram expressed as **100 frames**, where *each frame is one heartbeat*. A Moment is simultaneously:

- a **post** (the social unit),
- a **moment in time** (the exact UTC instant that minted it), and
- a **digital organism** (it has a genome, it grows, it can die, it can breed).

A Moment is encoded as a small JSON record. It can live inline in a URL (`?m=<base64url>`), as a portable `.egg` file (a *seed*), or as a record inside the public data warehouse.

---

## 2. Data model (the wire format)

A Moment record:

| Field | Type | Meaning |
|------|------|---------|
| `v`  | int | format version (`1`) |
| `t`  | string | title |
| `a`  | string | author handle (`@time`, `@place`, `@triumvirate`, or a user handle) |
| `b`  | string | biome — one of `savanna`, `canyon`, `forest`, `volcanic`, `void` |
| `k`  | array | **keyframes** (see below); the genome + grown detail |
| `born` | int | exact UTC milliseconds the Moment was minted (spacetime-born Moments only) |
| `pk` | string | **primary key** — a spacetime coordinate (§3) |
| `loc` | object? | `{lat,lng,place}` for place-bound (Pokémon-GO-style) Moments |
| `sig` | hex? | ECDSA P-256 signature over the canonical body (§6) |
| `pub` | JWK? | the signer's public key (the owner's identity) |
| `_id` | string? | lineage id (set only by a fork; §9.4) |
| `_gen`, `_stress` | int? | local homeostasis metadata (§5) |

**Keyframe** `k[i]`: `{ at, s, l, p, g, h, x, z, u? }`

- `at` — frame position `0…99` (the heartbeat index). Real-valued; fractional positions are fidelity detail.
- `s` size · `l` legs · `p` spikes · `g` glow · `h` hue (0–360) · `x,z` drift.
- `u` — **the UTC millisecond a frame was grown in** (§5.2). Its presence is the immutable/mutable boundary:
  - **no `u`** → a **genesis** frame (the deterministic birth genome — *sacred, immutable*).
  - **has `u`** → a **grown** frame (fidelity added over time — the *only* mutable part).

> **Normative:** any field whose name begins with `_` is local metadata and **MUST** be excluded from the signed body. Consumers **MUST** read all historical record shapes and **MUST NOT** rewrite identity in place.

---

## 3. Spacetime addressing (the primary key)

An organism's **primary key is a point in spacetime** — and because the organism is *deterministic from that point*, **the address IS the organism**.

- **Time domain (TLD `sky`):** `sky·<utc_ms>` — every millisecond is an address. Resolution is 1 ms, so two Moments can never collide.
- **Place domain (TLD `geohash`):** `<geohash9>·<utc_ms>` — every ~5 m cell on Earth × every instant. Place-bound Moments ("wild" catches) are seeded by location.

**Dialing.** `Organism.fromPk(pk)` regenerates the genesis genome from the address. So a Moment can be **summoned anywhere it is requested from with zero bytes of lookup** — the address is a phone number for a hologram. Surface: `?dial=<pk>`.

> **Normative:** the `pk` is the eternal join key. It is globally unique, immutable, and self-describing (`born = int(pk.split('·')[1])`). Consumers **MUST** key all per-organism operations on `pk`, never on array index or title.

---

## 4. Determinism & the birth-proof

`organismFromStamp(ms, loc?)` mints the one organism a coordinate produces by seeding a deterministic PRNG from a hash of the pk. Therefore:

- **`verifyCoordinate(record)`** regenerates the genesis genome from `pk` and asserts the record's `u`-less frames are byte-identical. This is the **birth-proof**.
- The birth-proof **MUST hold at every historical revision**. Any revision where it flips false is an **anomaly** (§9.1) — the public repo audits itself.

> **Normative:** the genome generator is frozen. It **MUST NOT** be changed, even to fix cosmetic quirks (e.g. two genesis keyframes rounding to the same `at`), because doing so would invalidate every existing Moment's birth-proof. Consumers **MUST** instead be robust to those quirks.

---

## 5. Organism physics

### 5.1 Homeostasis
An organism's keyframes are its life-trajectory. A new frame is **reconciled** against the established record:

- a frame at a **new** position → **refined** (absorbed; the organism grows a generation),
- a frame identical to an existing one → **redundant** ("nothing changed" — re-uploading a seed *is* this case),
- a frame that would **rewrite a settled downstream frame** → **resisted** (stress rises).

The organism **survives in homeostasis as long as it can**: it absorbs consistent frames forever, resists contradictions, and only when accumulated `stress` crosses `STRESS_LIMIT` (12) does homeostasis break (death).

> **Normative:** a same-`at` collision counts as an injury **only if a grown (`u`) frame caused it**. Two genesis frames sharing an `at` are the legitimate birth genome and **MUST NOT** be treated as a contradiction.

### 5.2 Fidelity over time
As real UTC time passes, a new frame folds into the **coarsest interval** the organism currently tracks, deepening detail **fractally** and **without bound**. Each grown frame is stamped with the UTC instant it arrived (`u`).

### 5.3 The dream-catcher weave
A grown frame is woven in **only if it stays consistent with the two neighbours it sits between** (`weaveCheck`, tolerance 0.12). A frame that would tear the web is rejected. Consistent + non-contradicting (weave + reconcile) is the full gate for all growth.

> **Invariant:** growth can never break the birth-proof or homeostasis. The genesis genome is never touched.

---

## 6. Ownership

Ownership is an **ECDSA P-256 signature** produced in the browser via Web Crypto and held in `localStorage`.

- The **canonical body** is the record with keys sorted, excluding `sig`, `pub`, and any `_`-prefixed key.
- `sig` is hex `r‖s`; `pub` is the public JWK. The signer's `pub.x` fingerprint **is the owner's identity** (a *zookeeper*).
- `verifyMoment` re-derives the body and verifies. A copy cannot forge the key, so ownership is provable and a market/leaderboard ranked by **distinct verified signers is ungameable**.

To own a moment in time, sign it.

### 6.1 The Rappid Eternity binding
A Moment's eternal address (`pk`) maps to a canonical **RAPP Eternity Standard** id: `rappid:<slug>:<64hex>`, where the 64-hex is `sha256("moment:"+pk)` (256-bit). A zookeeper key maps to `rappid:keeper:<sha256("keeper:"+pubx)>`. The id is deterministic and eternal; the **hash is the join key**. Per the eternity compatibility contract, implementations **MUST read all legacy forms forever** (a `pk`, a bare UTC ms, a `|` separator), **emit only canonical**, and **never version the string — add record fields instead**. `sig_suite` (e.g. `ecdsa-p256`) is the crypto-agility field, covered by the signature.

### 6.2 Transferable deeds
A rappid is a **transferable deed**. Ownership is the tip of a **per-rappid, hash-linked chain of transfers**: the current owner signs over the rights to a recipient key (a human *or* an agent — any key is an identity).

- A **transfer** is `{rappid, from, to, prev, ts, hash, sig, pub}`. `hash = sha256` of the canonical body; `prev` links to the previous transfer's hash (or the rappid, for the first); `sig` is the **current owner's** signature, and `pub.x` **MUST** equal `from`.
- **Resolution** (`deedChain`): start at the minter (the Moment's original signer), walk transfers by `prev`-linkage; each is applied **only if** `from` equals the then-current owner *and* its body hashes to `hash`. The tip is the current owner. Unauthorized or tampered transfers are ignored.
- The deed ledger (`lineage/transfers.jsonl`) is **permissionless-append** (a mempool); validity is decided at resolution, not at write. To send the rights to a Moment you already own, sign a transfer to the recipient's rappid/key and record it on the chain.

---

## 7. The Drop Stream

Generation costs ~2 µs/organism (~400 k/s); the real floor is the 1 ms pk resolution. So the **Drop Stream** mints **up to 1 000 globally-unique organisms per second**, one per UTC millisecond, rolling-windowed. The stream is a dense slice of time at millisecond resolution. (`drops.html`)

---

## 8. The social layer

- **A zookeeper is a key.** No accounts. A keeper's public menagerie is the set of warehouse organisms they signed.
- **Visit by key:** `?keeper=<fp>` walks any keeper's menagerie. `keepers.html` is the directory of all keepers.
- **My Zoo** (`?zoo`) is your *local* menagerie keyed by your key; **the feed is the zoo floor**.
- Language for the collection + identity layer: *plant, seed, garden, companion, menagerie, zookeeper*.

---

## 9. Git-as-harness

An organism is a record by `pk` inside shared minified JSON, so **git is its control plane** — via *revision-walk + extract-by-pk + structural diff*, never by sharding files. The browser cannot run git, so a brainstem-side `zoo` CLI deposits static `lineage/*.json` artifacts the player dials (`?dial=<pk>&{bio,grew,at,lineage}`).

| Capability | Git verb | Organism operation |
|---|---|---|
| **bio** | log + show | the dated **biography** + per-frame provenance; re-verifies the birth-proof at every revision |
| **grew** | record-aware diff | what it **became** between two instants — lossless, physics-classified |
| **checkout / restore / revert** | show ancestor / forward-commit | **time-travel + self-heal** to the last revision still in homeostasis; APPEND-ONLY, birth-proof-gated, witnessed in `events.jsonl` |
| **fork / merge** | branch + custom merge driver | **speciation + hybridization** — merge resolves per-frame via weave + reconcile; cross-species genesis is rejected; an over-stressed cross is sterile |

> **Normative:** every harness write is **append-only** — public `main` is never rewritten. Every write is gated by `verifyCoordinate` and refuses signed/owner-only records.

---

## 10. Serverless architecture (the data warehouse)

The **Simon Willison free-data-warehouse / git-scraping pattern**, applied to a living ecosystem:

- `moments.json` (feed) · `drops.json` (UTC stream) · `warehouse.json` (fingerprints) — static, committed, served from the CDN.
- Every tick a stats snapshot is committed (`stats.json` + `stats_history.json`), so the **git history of `stats.json` *is* the time-series database** (`stats.html`, the Zoo Desk).
- All ranking, similarity, analytics, ownership checks, biographies, and time-travel run **in the browser** over static files. Two backends, zero servers: **GitHub raw is the warehouse, git history is the time machine.**

---

## 10½. ⛓ The Chain (consensus & permanence)

The data warehouse is not merely *stored in* git — **it is a blockchain, and git is the chain.**

- **Blocks are commits.** Every git commit's SHA-1/256 hash covers its parent's hash, its tree, and its metadata. The commit graph is therefore a hash-linked, tamper-evident chain — the same Merkle-DAG structure a blockchain is. Mutating any historical block changes every descendant hash, exactly as in Bitcoin.
- **Transactions are Moments.** A new minted organism, a grown frame, a re-signing, a fork or merge — each is a state transition recorded in a block.
- **Consensus is the push-race.** A push to the shared branch is accepted **only if it fast-forwards** the current tip. When two committers race to push *their* update, the first to land wins the tip; the loser's push is rejected (non-fast-forward) and they must rebase onto the new head and try again. This is "longest valid chain wins" — Nakamoto consensus with git's fast-forward rule as the validity predicate. There is no proof-of-work; the scarce resource being raced for is **the tip itself**.
- **The witness is the committer date.** `%ct` (committer UTC) is the un-backdateable wall-clock stamp on each block — the chain's native timestamp, cross-checked against each organism's self-reported `born`/`u`.
- **It can never die.** Git is distributed: every clone is a complete replica of the entire chain, history and all. The public copy is served globally from the CDN, but its life does not depend on any one host — mirror it anywhere and the chain continues. There is no single point of failure to switch off.

**Validity rules of the chain** (a "full node" — `zoo_chain` — checks these across the whole history):

1. **Hash-linkage** — every block links to its parent (inherent to git; `git fsck`).
2. **Birth-proof permanence** — `verifyCoordinate` holds for every organism at **every** block; a genesis genome is never rewritten (§4). This is the chain's immutability law for identity.
3. **Append-only** — public `main` is never rewritten; state only moves forward (§9, §12.4).
4. **Signature validity** — owned organisms carry a verifiable ECDSA signature; ownership is provable per block (§6).

A block that violates rule 2 or 4 is **invalid** and self-flags as an anomaly (§9.1) — the chain audits itself, in the browser, from static files.

> **Normative:** the chain is **append-only and forward-only**. Implementations **MUST NOT** rewrite published history. Forks (§9.4) are branches off the chain; merges reconcile by the organism's own survival law, never by destroying a block.

---

## 11. Similarity (Kindred)

Each organism is scored into a portable **32-D fingerprint** by sampling its whole 100-frame trajectory (per-field mean/std/range, an 8-bin hue histogram + circular mean, motion/jerk/glow energy). `?dial`/Kindred ranks "organisms more similar to mine than others" entirely client-side by fingerprint distance.

---

## 11½. Dimensions, the genesis Commons & overlay

- **The Commons is a dimension.** The RAPP Commons world (`commons.html`) is itself an organism that **made contact with time** at its genesis commit (`sky·1778521758000`, `rappid:dimension:0c0ba7…`, 2026-05-11 17:49:18 UTC). It is the **genesis dimension** — the first to exist on the chain. `commonsAgent.genesis()` declares it; `genesis.json` is its manifest, proven not by a signature but by the chain's genesis block (the un-backdateable first commit).
- **Every Moment is a dimension**, born of its own instant. By default a Moment **joins** the genesis Commons (its resolution `dimension` anchor), and any dimension may anchor to any other — *others can join*.
- **Overlay.** Many dimensions of the **same** moment (sharing one genesis genome / pk) can be **laid over each other and merged coherently** via the **dream-catcher** (`overlay()` folds each layer's grown frames through `weaveFrame`): consistent overlays are inherited, contradictions resisted, the result is one coherent composite. A different moment (genesis mismatch) cannot overlay. This is how many contributors over a single moment compose into a richer whole.

## 11¾. The Gateway (universal resolution & marketplace interop)

A rappid is a **gateway**. `Resolve.document(moment)` produces one standard document any system — a wallet, an NFT marketplace, another world entirely — can fetch to render, verify, extend, and trade the Moment:

- **NFT/marketplace-native** (ERC-721 / OpenSea-compatible): `name`, `description`, `image`, **`animation_url`** (the live `?dial=<pk>` hologram — marketplaces embed it, so the *actual walkable Moment renders in-place*), `external_url`, `attributes` (biome/keyframes/born/… as traits).
- **RAPP Eternity extensions:** `rappid`, `pk`, `born`, `owner` (deed-resolved `rappid:keeper`), `sig_suite`, `chain` (the git-blockchain + its validator), `dimension` (the dimension it joins).
- **Extensible — `sources`:** external references the owner ties in to **continue the dimension into any system, even outside this ecosystem**.

`resolve.html?{m|id}=…` is the human + `?format=json` machine gateway, emitting OpenGraph/Twitter-player meta so public crawlers and marketplaces index it. The Moment becomes accessible to the full public marketplace with **zero servers** — a static document on the CDN, the live hologram one dial away.

## 12. Invariants (conformance)

A conforming implementation **MUST**:

1. Preserve the **birth-proof**: never alter a genesis frame; `verifyCoordinate` holds for all time.
2. Treat the genome generator as **frozen** (§4).
3. Keep all `_`-prefixed metadata **out of the signed body** (§2, §6).
4. Make every harness/edit operation **append-only** and birth-proof-gated (§9).
5. Stay **drop-in serverless** — static data, client-side queries, no new server (§10).
6. Read **all** historical record shapes; emit only canonical; never rewrite identity in place.
7. Gate all growth by **weave + reconcile**; never let growth break homeostasis (§5).

---

## 13. Surfaces

| Surface | URL | What |
|---|---|---|
| Feed | `./` | the zoo floor |
| Player | `?m=<token>` / `?dial=<pk>` | walk a Moment; ⧉ PiP, 🔬 scan (pause+orbit), 📜 Bio |
| My Zoo | `?zoo` | your local menagerie |
| Keeper | `?keeper=<fp>` | a zookeeper's public menagerie |
| Keepers | `keepers.html` | the directory of keepers |
| Drop Stream | `drops.html` | 1 ms-gap UTC organisms |
| Market | `market.html` | ungameable leaderboard (distinct verified signers) |
| Zoo Desk | `stats.html` | git-scraped data journalism |
| Harness | `?dial=<pk>&{bio,grew,at,lineage}` | git-as-harness views |

---

## 14. Glossary

**Moment** — a 100-frame living hologram; a post; a moment in time. · **Organism** — what a Moment is. · **Genesis** — the immutable birth genome (no `u`). · **Grown frame** — fidelity added over time (has `u`). · **pk** — the spacetime primary key / address. · **Dial** — summon by address. · **Zookeeper** — a signing key = an identity. · **Seed (`.egg`)** — a portable Moment you plant. · **Homeostasis** — the survival law. · **Birth-proof** — `verifyCoordinate`. · **Harness** — git as the organism's control plane.

---

*Engine, not experience. Drop-in, serverless, alive.*
