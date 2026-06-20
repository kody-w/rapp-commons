#!/usr/bin/env python3
"""
spawn_beings.py — put N independent AI beings into the unified commons as
parallel avatars, one per browser tab, populating the living world.

This is the "spin up subagents as beings on different tabs" mechanism.

How it works
------------
The commons (commons.html) is a single walkable PeerJS world. A tab with NO
``?host=`` query opens a room and prints its room id; tabs with
``?host=<id>`` join that same room. Every connected peer renders as a remote
avatar streaming its position, so a handful of joiner tabs literally appear as
neighbors walking around together.

This script:

  1. Launches ONE host tab (commons.html, no ?host) headless and reads its
     PeerJS room id from the page's console line:
         "Commons room — share to bring neighbors: <url>?host=<ID>"
  2. Launches N joiner tabs (commons.html?host=<ID>) so they all share one world.
  3. Gives each being a simple autonomous loop, driven from the page via
     ``window.commonsAgent`` (once that API exists): teleport to a random spot,
     walk a little, and every few seconds occasionally say() a short signed
     hello — for ``seconds`` total. If ``window.commonsAgent`` is not present
     yet, the joiner still appears as a presence avatar and the loop waits for
     the API to show up (fully graceful — no commons.html change required).

Usage
-----
    spawn_beings.py <N> [seconds] [base_url=http://localhost:8777/commons.html]

Run it with the brainstem venv's Python so Playwright + chromium are available:
    ~/.brainstem/venv/bin/python tools/spawn_beings.py 5 60

Robustness: every navigation has a timeout, and each being runs inside its own
try/except so one stuck tab never takes down the swarm.
"""

import sys
import time
import random
import traceback

try:
    from playwright.sync_api import sync_playwright, Error as PWError
except Exception:  # pragma: no cover - import guard
    sys.stderr.write(
        "ERROR: Playwright is not importable. Run with the brainstem venv python:\n"
        "  ~/.brainstem/venv/bin/python tools/spawn_beings.py <N> [seconds] [base_url]\n"
    )
    raise


DEFAULT_BASE_URL = "http://localhost:8777/commons.html"

# Generous per-action timeouts (ms). The commons pulls Three.js + PeerJS from
# CDNs and then negotiates a PeerJS room, which can take a few seconds.
NAV_TIMEOUT_MS = 30_000
ROOM_ID_TIMEOUT_S = 30.0     # wait this long for the host to print its room id
JOIN_SETTLE_S = 2.0          # let a joiner connect before starting its loop


# ---------------------------------------------------------------------------
# The autonomous-being loop, injected into each joiner tab.
#
# It prefers window.commonsAgent (teleport / walk / say). That API is expected
# to be added to commons.html later; until then this degrades to a heartbeat
# that keeps the tab alive as a presence avatar and polls for the API.
#
# Args are passed as a single JSON-able object: {seconds, name, fp}
# ---------------------------------------------------------------------------
BEING_LOOP_JS = r"""
async ({ seconds, name }) => {
  const sleep = (ms) => new Promise(r => setTimeout(r, ms));
  const rand  = (a, b) => a + Math.random() * (b - a);
  const log   = (...a) => { try { console.log("[being:" + name + "]", ...a); } catch (_) {} };

  const HELLOS = [
    "hello, commons",
    "wandering in",
    "anyone here?",
    "exploring the world",
    "good to be here",
    "saying hi from a new tab",
    "the world feels alive",
    "passing through",
  ];

  const deadline = Date.now() + seconds * 1000;
  let said = 0, steps = 0, sawApi = false;

  while (Date.now() < deadline) {
    const A = window.commonsAgent;
    if (A) {
      sawApi = true;
      try {
        // teleport to a random spot inside the world's soft bounds (~R=90)
        if (typeof A.teleport === "function") {
          const ang = rand(0, Math.PI * 2), r = rand(4, 70);
          A.teleport(Math.cos(ang) * r, undefined, Math.sin(ang) * r);
        }
        // walk a short burst toward a random heading
        if (typeof A.walk === "function") {
          if (typeof A.face === "function") A.face(rand(0, Math.PI * 2));
          await A.walk(["forward","back","left","right"][Math.floor(Math.random()*4)], 2 + Math.floor(Math.random()*3));
          steps++;
        }
        // occasionally say a short signed hello
        if (typeof A.say === "function" && Math.random() < 0.5) {
          const msg = HELLOS[(Math.random() * HELLOS.length) | 0] + " — " + name;
          await A.say(msg);
          said++;
        }
      } catch (e) {
        log("loop step error", e && e.message);
      }
    } else {
      // API not present yet — stay alive as a presence avatar and keep watching.
      log("waiting for window.commonsAgent…");
    }
    await sleep(rand(2500, 4500));
  }

  return { said, steps, sawApi };
}
"""


def _read_room_id(host_page, timeout_s: float) -> str:
    """Wait for the host tab to announce its PeerJS room id and return it."""
    captured = {"id": None}

    def on_console(msg):
        try:
            text = msg.text()
        except Exception:
            return
        if "Commons room" in text and "host=" in text:
            captured["id"] = text.split("host=", 1)[1].strip().strip("\"' )")

    host_page.on("console", on_console)

    deadline = time.time() + timeout_s
    while time.time() < deadline:
        if captured["id"]:
            return captured["id"]
        # Belt-and-braces: try to read it off the page in case we attached late.
        try:
            rid = host_page.evaluate(
                "() => { try { return (typeof roomId!=='undefined' && roomId) || null; }"
                " catch(e){ return null; } }"
            )
            if rid:
                return rid
        except Exception:
            pass
        time.sleep(0.25)

    raise TimeoutError(
        f"host tab did not announce a PeerJS room id within {timeout_s:.0f}s"
    )


def spawn(n: int, seconds: int, base_url: str) -> int:
    """Spawn 1 host + n joiner beings. Returns the count that ran successfully."""
    print(f"[spawn] host={base_url}  beings={n}  seconds={seconds}")
    ok = 0

    with sync_playwright() as pw:
        browser = pw.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--use-fake-ui-for-media-stream",
                  "--use-fake-device-for-media-stream"],
        )
        context = browser.new_context()

        # 1) HOST tab — opens the room, prints the room id.
        host_page = context.new_page()
        try:
            host_page.goto(base_url, timeout=NAV_TIMEOUT_MS, wait_until="load")
        except PWError as e:
            print(f"[spawn] FATAL: could not load host tab: {e}")
            context.close()
            browser.close()
            return 0

        try:
            room_id = _read_room_id(host_page, ROOM_ID_TIMEOUT_S)
        except Exception as e:
            print(f"[spawn] FATAL: {e}")
            context.close()
            browser.close()
            return 0

        print(f"[spawn] commons room id: {room_id}")
        join_url = f"{base_url}{'&' if '?' in base_url else '?'}host={room_id}"

        # 2) N JOINER tabs — each becomes a being in the shared world.
        beings = []  # (page, name, future-handle)
        for i in range(n):
            name = f"being-{i+1:02d}"
            try:
                page = context.new_page()
                page.goto(join_url, timeout=NAV_TIMEOUT_MS, wait_until="load")
                page.on(
                    "console",
                    lambda m, nm=name: _maybe_print(nm, m),
                )
                beings.append((page, name))
                print(f"[spawn] {name}: joined {room_id[:8]}…")
            except Exception as e:
                print(f"[spawn] {name}: FAILED to join — {e}")
                traceback.print_exc()

        if not beings:
            print("[spawn] no beings joined; nothing to do")
            context.close()
            browser.close()
            return 0

        # Let the mesh settle so presence/hello exchanges land.
        time.sleep(JOIN_SETTLE_S)

        # 3) Kick off each being's autonomous loop. We run them concurrently by
        #    starting each non-blocking and then awaiting via a shared deadline:
        #    Playwright's sync API is single-threaded, so we drive the loop in
        #    the page (async JS) and just collect results at the end. Each call
        #    is wrapped so one stuck tab can't abort the swarm.
        results = []
        # Start every being's loop. evaluate() blocks until the JS resolves, so
        # to keep them parallel we give the page-side loop its own deadline and
        # call them in sequence — each returns only after `seconds`. To make
        # them genuinely overlap, we launch via evaluate on a tiny stagger and
        # rely on the in-page async loops all running against wall-clock.
        #
        # Practical approach: dispatch all loops without awaiting by using
        # page.evaluate on a fire-and-forget promise stored on window, then poll.
        for page, name in beings:
            try:
                page.evaluate(
                    "(args) => { window.__beingDone = (" + BEING_LOOP_JS + ")(args)"
                    ".then(r => { window.__beingResult = r; return r; })"
                    ".catch(e => { window.__beingResult = {error: String(e)}; }); }",
                    {"seconds": seconds, "name": name},
                )
            except Exception as e:
                print(f"[spawn] {name}: could not start loop — {e}")

        # Poll until the deadline, then collect each being's result.
        end = time.time() + seconds + 5
        time.sleep(seconds)  # let the in-page loops run their course
        for page, name in beings:
            try:
                # give a moment past the deadline for the promise to resolve
                res = None
                while time.time() < end and res is None:
                    res = page.evaluate("() => window.__beingResult || null")
                    if res is None:
                        time.sleep(0.5)
                if res is None:
                    print(f"[spawn] {name}: loop did not report (still alive)")
                    ok += 1  # it was a live avatar regardless
                elif "error" in res:
                    print(f"[spawn] {name}: loop error — {res['error']}")
                else:
                    print(
                        f"[spawn] {name}: ok  said={res.get('said')} "
                        f"steps={res.get('steps')} sawApi={res.get('sawApi')}"
                    )
                    ok += 1
                results.append((name, res))
            except Exception as e:
                print(f"[spawn] {name}: result collection failed — {e}")

        # Tear down.
        try:
            context.close()
        except Exception:
            pass
        try:
            browser.close()
        except Exception:
            pass

    print(f"[spawn] done — {ok}/{n} beings ran")
    return ok


def _maybe_print(name: str, msg) -> None:
    """Surface a being's in-page logs (kept quiet unless it's our marker)."""
    try:
        text = msg.text()
    except Exception:
        return
    if text.startswith("[being:"):
        print("  " + text)


def _parse_args(argv):
    if len(argv) < 2 or argv[1] in ("-h", "--help"):
        print(__doc__)
        sys.exit(0 if len(argv) >= 2 else 2)

    try:
        n = int(argv[1])
    except ValueError:
        sys.stderr.write(f"N must be an integer, got: {argv[1]!r}\n")
        sys.exit(2)
    if n < 1:
        sys.stderr.write("N must be >= 1\n")
        sys.exit(2)

    seconds = 30
    if len(argv) >= 3:
        try:
            seconds = int(argv[2])
        except ValueError:
            sys.stderr.write(f"seconds must be an integer, got: {argv[2]!r}\n")
            sys.exit(2)

    base_url = argv[3] if len(argv) >= 4 else DEFAULT_BASE_URL
    return n, seconds, base_url


def main(argv):
    n, seconds, base_url = _parse_args(argv)
    try:
        ran = spawn(n, seconds, base_url)
    except KeyboardInterrupt:
        print("\n[spawn] interrupted")
        return 130
    return 0 if ran > 0 else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
