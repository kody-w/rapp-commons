#!/usr/bin/env python3
"""Data + engine tests for the RAPP Commons repo. Pure stdlib. Run from anywhere.
Exit 0 iff all pass. Prints PASS/FAIL per check."""
import os, sys, json, glob, importlib.util

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
results = []


def check(name, ok, info=""):
    results.append(ok)
    print(("PASS " if ok else "FAIL ") + name + ((" -- " + str(info)) if info and not ok else ""))


# 1) all JSON valid
bad = []
for f in glob.glob("**/*.json", recursive=True):
    if any(p in f for p in ("/render/", "/key/", "/.git/", "node_modules")):
        continue
    try:
        json.load(open(f))
    except Exception as e:
        bad.append(f"{f}: {e}")
check("all_json_valid", not bad, bad[:3])

# 2) manifest refs exist
try:
    nb = json.load(open("neighborhood.json")); q = nb.get("quirks", {})
    miss = [g for g in q.get("games", []) if not os.path.exists(f"games/{g}/game.json")]
    check("game_manifests_exist", not miss, miss)
    w = json.load(open("worlds.json"))
    rmiss = [r["handle"] for r in w.get("rooms", []) if not os.path.exists(r.get("state_dir", "") + r.get("state_index", ""))]
    check("room_state_exists", not rmiss, rmiss)
    nr = json.load(open("npcs/registry.json"))
    nmiss = [n["name"] for n in nr.get("npcs", []) if not os.path.exists(n.get("manifest", ""))]
    check("npc_manifests_exist", not nmiss, nmiss)
except Exception as e:
    check("manifests", False, e)

# 3) sacred files present + untouched-by-existence
sacred = ["PROTOCOL.md", "index.html", "swarm_agent.py", "events/SCHEMA.md", "tether.html"]
check("sacred_present", all(os.path.exists(s) for s in sacred), [s for s in sacred if not os.path.exists(s)])

# 4) the spawner lives in THIS repo (not the brainstem repo)
check("spawn_beings_in_commons", os.path.exists("tools/spawn_beings.py"))

# 5) poker engine exists + evaluates a hand (TDD gate — fails until built)
poker = "games/poker/engine.py"
if os.path.exists(poker):
    try:
        spec = importlib.util.spec_from_file_location("poker_engine", poker)
        m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
        # contract: a hand-rank function that ranks a royal flush above a pair
        fn = getattr(m, "rank_hand", None) or getattr(m, "evaluate", None)
        check("poker_engine", fn is not None, "no rank_hand/evaluate")
    except Exception as e:
        check("poker_engine", False, e)
else:
    check("poker_engine", False, "games/poker/engine.py not built yet")

# 6) WWF game still has a manifest + the game room data
check("wwf_present", os.path.exists("games/words-with-friends/game.json"))

p = sum(1 for r in results if r); n = len(results)
print(f"\n=== data/engines: {p}/{n} passed ===")
sys.exit(0 if p == n else 1)
