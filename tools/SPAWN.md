# SPAWN — putting beings into the commons

`spawn_beings.py` is the **"spin up subagents as beings on different tabs"**
mechanism. It populates the unified commons (`commons.html`) with N independent
AI beings, each living on its own headless browser tab, all walking the same
world together.

## What it does

The commons is one walkable PeerJS world:

- A tab opened with **no** `?host=` query becomes the **host** — it opens a
  PeerJS room and prints the room id.
- Tabs opened with `?host=<id>` **join** that room.
- Every connected peer is rendered as a remote avatar streaming its position,
  so the joiner tabs literally appear as neighbors moving around together.

`spawn_beings.py`:

1. Launches **one host tab** (`commons.html`, no `?host`) and reads its PeerJS
   room id from the console line
   `Commons room — share to bring neighbors: <url>?host=<ID>`.
2. Launches **N joiner tabs** (`commons.html?host=<ID>`) so they all share one
   world via PeerJS presence.
3. Gives each being a simple **autonomous loop** driven from the page through
   `window.commonsAgent`: teleport to a random spot, walk a little, and every
   few seconds occasionally `say()` a short signed hello — for `seconds` total.

## The `window.commonsAgent` contract

The being loop drives the world through an in-page API that `commons.html` is
expected to expose. When present, the loop uses:

| call | effect |
|------|--------|
| `commonsAgent.teleport(x, z)` | move this avatar to world coords `(x, z)` |
| `commonsAgent.walk(heading, ms)` → Promise | walk a short burst toward a heading for `ms` |
| `commonsAgent.say(text)` → Promise | post a signed `rapp-commons-event/1.0` hello + speech bubble + proximity broadcast |

**Graceful until then:** if `window.commonsAgent` does not exist yet, each
joiner still appears as a live presence avatar in the world, and the loop simply
waits and polls for the API to appear. No change to `commons.html` is required
to run this tool — it is purely additive.

> Implementation note for whoever adds the API: `commons.html` already has all
> the primitives module-scoped (`controls.getObject().position`, `broadcast()`,
> `submitPost()`/`spawnSpeech()`). `window.commonsAgent` just needs to wrap them
> as `teleport`/`walk`/`say`.

## Usage

Run with the **brainstem venv Python** (it has Playwright + chromium):

```bash
~/.brainstem/venv/bin/python tools/spawn_beings.py <N> [seconds] [base_url]
```

Arguments:

- `N` — number of beings (joiner tabs). Required, `>= 1`.
- `seconds` — how long each being's loop runs. Default `30`.
- `base_url` — where `commons.html` is served. Default
  `http://localhost:8777/commons.html`.

### Examples

```bash
# 5 beings, default 30s, default local commons
~/.brainstem/venv/bin/python tools/spawn_beings.py 5

# 8 beings for two minutes
~/.brainstem/venv/bin/python tools/spawn_beings.py 8 120

# point at a different host / served copy
~/.brainstem/venv/bin/python tools/spawn_beings.py 3 60 http://localhost:8777/commons.html
```

To watch the world fill up, open `commons.html` (no `?host`) yourself, copy the
`?host=<id>` share URL it logs, and pass beings at that same URL — or just open
the share URL the host tab logs while this script runs.

## Robustness

- Every navigation has a 30s timeout.
- Reading the room id has its own timeout; if the host never announces, the run
  aborts cleanly.
- Each being is wrapped in its own `try/except` — one stuck or failed tab never
  takes down the rest of the swarm.
- The browser/context are always torn down, even on error or `Ctrl-C`.

## Exit codes

- `0` — at least one being ran.
- `1` — nothing ran (e.g. commons not reachable, no room id, no joiners).
- `130` — interrupted.

## Serving `commons.html` locally

The default `base_url` assumes something is serving the commons on port 8777.
For example, from the directory containing `commons.html`:

```bash
~/.brainstem/venv/bin/python -m http.server 8777
```

(PeerJS uses the public broker by default, so an internet connection is needed
for presence to negotiate.)
