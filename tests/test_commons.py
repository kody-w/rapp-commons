#!/usr/bin/env python3
"""Acceptance tests for the unified commons.html (one walkable world). Playwright/headless chromium.
Run: <venv>/bin/python tests/test_commons.py   (commons must be served, default localhost:8777)
Exit 0 iff all pass. Each test prints PASS/FAIL <name>."""
import sys, os, asyncio, urllib.request
from playwright.async_api import async_playwright

BASE = os.environ.get("COMMONS_BASE", "http://localhost:8777")
URL = BASE + "/commons.html"
results = []


def check(name, ok, info=""):
    results.append(ok)
    print(("PASS " if ok else "FAIL ") + name + (("  -- " + str(info)) if info and not ok else ""))


async def run():
    # static source rule: ONE world => zero window.open (no link-outs)
    try:
        src = urllib.request.urlopen(URL, timeout=10).read().decode()
        check("no_link_outs", "window.open" not in src, "commons.html still uses window.open (link-out)")
    except Exception as e:
        check("served", False, e); print_summary(); return

    async with async_playwright() as p:
        b = await p.chromium.launch(headless=True, args=["--no-sandbox", "--use-gl=swiftshader"])
        page = await b.new_page(viewport={"width": 1280, "height": 800})
        errs = []
        page.on("pageerror", lambda e: errs.append(str(e)[:120]))
        await page.goto(URL, wait_until="domcontentloaded", timeout=30000)
        await page.wait_for_timeout(4000)
        check("no_page_errors", not errs, errs[:2])

        async def ev(js, d=None):
            try: return await page.evaluate(js)
            except Exception: return d

        api = await ev("()=>!!window.commonsAgent && typeof window.commonsAgent.where==='function'", False)
        check("coordinate_api", bool(api), "window.commonsAgent.where missing")
        methods = await ev("()=>window.commonsAgent?Object.keys(window.commonsAgent):[]", [])
        need = {"where", "teleport", "walk", "nearby", "goto", "enter", "say", "list"}
        check("coordinate_api_methods", need.issubset(set(methods or [])), "missing " + str(need - set(methods or [])))

        if api:
            moved = await ev("()=>{window.commonsAgent.teleport(12,1.6,-8);const w=window.commonsAgent.where();return Math.abs(w.x-12)<2&&Math.abs(w.z+8)<2;}", False)
            check("teleport_moves", bool(moved))
            near = await ev("()=>{try{return (window.commonsAgent.nearby()||[]).length>=0}catch(e){return false}}", False)
            check("nearby_lists", bool(near))
            areas = await ev("()=>{try{return (window.commonsAgent.list()||[]).map(a=>(a.name||a.slug||a).toString().toLowerCase())}catch(e){return[]}}", [])
            txt = " ".join(areas)
            check("game_rooms_present", ("poker" in txt) and ("words" in txt or "wwf" in txt), "list()=" + str(areas)[:120])
            check("areas_present", any(k in txt for k in ("voxel", "nexus", "square")), "list()=" + str(areas)[:120])
            posted = await ev("()=>{try{const r=window.commonsAgent.say('acceptance hello');return r!==undefined}catch(e){return false}}", False)
            check("signed_post", bool(posted))
            npc = await ev("()=>{try{const n=(window.commonsAgent.nearby()||window.commonsAgent.list()||[]).map(x=>JSON.stringify(x).toLowerCase()).join(' ');return n.includes('pip')||n.includes('atlas')}catch(e){return false}}", False)
            check("npcs", bool(npc))

            # residents_live: the world is INHABITED -- on load a few resident
            # beings spawn (each with its OWN rappid via the existing being mint)
            # and AUTONOMOUSLY wander/act on a slow client-side heartbeat. Assert
            # commonsAgent.residents() returns >=2 residents, each carrying a
            # rappid `from`, and that across a short poll at least one resident's
            # position OR lastAction CHANGES (they actually move / sign actions).
            has_res = await ev("()=>typeof window.commonsAgent.residents==='function'", False)
            if has_res:
                snap = lambda: ev(
                    "()=>{try{return (window.commonsAgent.residents()||[]).map(r=>({"
                    "name:r.name,from:r.from,"
                    "pos:[Math.round((r.pos&&r.pos.x)||0),Math.round((r.pos&&r.pos.z)||0)],"
                    "act:r.lastAction?JSON.stringify(r.lastAction):null}))}catch(e){return[]}}", [])
                first = await snap() or []
                # every resident is a real being: a rappid `from` (never a bare handle).
                all_rappid = bool(first) and all(str(r.get("from", "")).startswith("rappid:") for r in first)
                changed = False
                base = {r["name"]: (tuple(r["pos"]), r["act"]) for r in first}
                for _ in range(30):                 # ~9s of polling for movement/action
                    await page.wait_for_timeout(300)
                    cur = await snap() or []
                    for r in cur:
                        prev = base.get(r["name"])
                        if prev is None:
                            continue
                        if (tuple(r["pos"]), r["act"]) != prev:
                            changed = True
                            break
                    if changed:
                        break
                check("residents_live",
                      len(first) >= 2 and all_rappid and changed,
                      {"count": len(first), "all_rappid": all_rappid,
                       "changed": changed, "sample": first[:3]})
            else:
                check("residents_live", False, "window.commonsAgent.residents missing")

            # residents_play: the world is not just inhabited -- it has GAMES IN
            # PROGRESS, AI-vs-AI, LOCAL. The wandering residents SIT at the poker
            # table and PLAY each other (a continuous signed Hold'em hand on the
            # EXISTING pokerPlayHand loop + commit-reveal deck + rapp-poker-action/
            # 1.0, each seat signed by THAT resident's OWN rappid), and a couple
            # residents drift to the Words board and APPEND signed rapp-wwf-move/
            # 1.0 tiles so the board GROWS. Over a short poll assert:
            #   • gamesLive().poker shows a hand IN PROGRESS with >=2 seats whose
            #     `from` are rappid ids, AND a non-empty signed action stream
            #     (the live POKER.hand.log carries signed rapp-poker-action/1.0
            #     records, each with a rappid `from` + signature), AND
            #   • the WWF board's signed move/tile count INCREASES (a resident
            #     played a signed tile while we watched).
            # ZERO peer connection -- purely local AI-vs-AI on each being's rappid.
            has_live = await ev("()=>typeof window.commonsAgent.gamesLive==='function'", False)
            if has_live:
                snap = lambda: ev("()=>{try{return window.commonsAgent.gamesLive()}catch(e){return null}}", None)
                # baseline wwf move count.
                base_live = await snap() or {}
                base_wwf = (base_live.get("wwf") or {}).get("moves", 0) or 0
                poker_ok = False
                wwf_grew = False
                sample = {}
                for _ in range(60):                    # ~18s of polling for live play
                    gl = await snap() or {}
                    pk = gl.get("poker") or {}
                    seats = pk.get("seats") or []
                    rappid_seats = [s for s in seats if str(s.get("from", "")).startswith("rappid:")]
                    # a non-empty SIGNED action stream on the live hand: every entry
                    # is a rapp-poker-action/1.0 carrying a rappid `from` + a signature.
                    signed_stream = await ev(
                        "()=>{try{return (POKER.hand&&POKER.hand.log||[]).filter(a=>"
                        "a.schema==='rapp-poker-action/1.0'&&/^rappid:/.test(a.from||'')"
                        "&&typeof a.sig==='string'&&a.sig.length>0).length}catch(e){return 0}}", 0)
                    if (pk.get("inProgress") and len(seats) >= 2
                            and len(rappid_seats) >= 2 and (signed_stream or 0) >= 1):
                        poker_ok = True
                    cur_wwf = (gl.get("wwf") or {}).get("moves", 0) or 0
                    if cur_wwf > base_wwf:
                        wwf_grew = True
                    sample = {"phase": pk.get("phase"), "pot": pk.get("pot"),
                              "seats": len(seats), "rappid_seats": len(rappid_seats),
                              "signed_stream": signed_stream,
                              "wwf_base": base_wwf, "wwf_now": cur_wwf}
                    if poker_ok and wwf_grew:
                        break
                    await page.wait_for_timeout(300)
                check("residents_play", poker_ok and wwf_grew, sample)
            else:
                check("residents_play", False, "window.commonsAgent.gamesLive missing")

            # poker_renders: enter the poker room and assert the LIVE table is
            # visible/inspectable -- community cards on the felt + seats whose
            # actions are signed under per-bot rappids (never a human).
            has_state = await ev("()=>typeof window.commonsAgent.pokerState==='function'", False)
            if has_state:
                await ev("()=>{try{window.commonsAgent.enter('poker');}catch(e){}return 1}")
                # the room auto-deals one signed hand asynchronously; poll for it.
                st = None
                for _ in range(40):
                    st = await ev("()=>{try{return window.commonsAgent.pokerState()}catch(e){return null}}", None)
                    if st and st.get("community") and st.get("seats"):
                        break
                    await page.wait_for_timeout(500)
                st = st or {}
                seats = st.get("seats") or []
                community = st.get("community") or []
                rappid_seats = [s for s in seats if str(s.get("from", "")).startswith("rappid:")]
                bot_rappids = [s for s in seats if str(s.get("from", "")).startswith("rappid:") and not s.get("isHuman")]
                check("poker_renders",
                      len(community) >= 3 and len(seats) >= 2
                      and len(rappid_seats) == len(seats) and len(bot_rappids) >= 1,
                      {"community": community, "seats": seats,
                       "phase": st.get("phase"), "pot": st.get("pot")})
            else:
                check("poker_renders", False, "window.commonsAgent.pokerState missing")

            # poker_play: the table is now PLAYABLE by the human at seat 0. Start a
            # fresh INTERACTIVE hand and, whenever it is seat-0's turn
            # (pokerCanAct().toAct===0), have the human act via
            # window.commonsAgent.pokerAct(...) (check through, else call). Assert the
            # human's own signed actions land in the hand log under a rappid id and
            # the hand reaches showdown/result -- driven only via the public API.
            has_act = await ev(
                "()=>typeof window.commonsAgent.pokerAct==='function'"
                "&&typeof window.commonsAgent.pokerCanAct==='function'", False)
            if has_act:
                # ensure we're at the poker table (idempotent) and the demo deal settled.
                await ev("()=>{try{window.commonsAgent.enter('poker');}catch(e){}return 1}")
                for _ in range(40):
                    st = await ev("()=>{try{return window.commonsAgent.pokerState()}catch(e){return null}}", None)
                    if st and (st.get("phase") == "showdown" or st.get("community")):
                        break
                    await page.wait_for_timeout(300)
                # kick off a new hand that PAUSES on the human's turn (no autopilot).
                await ev("()=>{try{pokerPlayHand();}catch(e){}return 1}")
                human_acts = 0
                reached = False
                for _ in range(120):
                    can = await ev("()=>{try{return window.commonsAgent.pokerCanAct()}catch(e){return null}}", None)
                    if can and can.get("toAct") == 0:
                        opts = can.get("options") or []
                        choice = "check" if "check" in opts else "call"
                        body = await ev(
                            "()=>Promise.resolve(window.commonsAgent.pokerAct('" + choice + "'))"
                            ".then(b=>({action:b.action,seat:b.seat,frm:b.from,sig:!!b.sig}))"
                            ".catch(e=>({err:String(e)}))", None)
                        if body and body.get("seat") == 0 and str(body.get("frm", "")).startswith("rappid:") and body.get("sig"):
                            human_acts += 1
                    pst = await ev("()=>{try{return window.commonsAgent.pokerState()}catch(e){return null}}", None)
                    if pst and pst.get("phase") == "showdown":
                        reached = True
                        break
                    await page.wait_for_timeout(150)
                # the human's signed betting actions must appear in the live hand log,
                # each carrying a rappid `from` + signature (never a bare human handle).
                signed_human = await ev(
                    "()=>{try{return (POKER.hand.log||[]).filter(a=>a.seat===0"
                    "&&/^rappid:/.test(a.from||'')&&!!a.sig"
                    "&&['check','call','bet','raise','fold'].includes(a.action)).length}catch(e){return -1}}", -1)
                has_result = await ev("()=>{try{return !!POKER.lastResult}catch(e){return false}}", False)
                check("poker_play",
                      human_acts >= 1 and signed_human >= 1 and reached and bool(has_result),
                      {"human_acts": human_acts, "signed_human": signed_human,
                       "reached_showdown": reached, "has_result": has_result})
            else:
                check("poker_play", False, "window.commonsAgent.pokerAct/pokerCanAct missing")

            # wwf_renders: enter the Words-with-Friends room and assert the LIVE
            # 3D board is visible/inspectable -- it surfaces the EXISTING signed
            # match (tiles read straight off games/words-with-friends/matches/),
            # so every tile's `from` is a signed rappid id (never a human).
            has_wwf = await ev("()=>typeof window.commonsAgent.wwfState==='function'", False)
            if has_wwf:
                await ev("()=>{try{window.commonsAgent.enter('words');}catch(e){}return 1}")
                # the room loads the signed match asynchronously; poll for the board.
                wst = None
                for _ in range(40):
                    wst = await ev("()=>{try{return window.commonsAgent.wwfState()}catch(e){return null}}", None)
                    if wst and wst.get("board") and wst.get("tiles"):
                        break
                    await page.wait_for_timeout(500)
                wst = wst or {}
                board = wst.get("board") or []
                tiles = wst.get("tiles") or []
                players = wst.get("players") or []
                rappid_tiles = [t for t in tiles if str(t.get("from", "")).startswith("rappid:")]
                check("wwf_renders",
                      len(board) == 15 and all(len(row) == 15 for row in board)
                      and len(tiles) >= 1 and len(rappid_tiles) == len(tiles)
                      and len(players) >= 2 and wst.get("toMove") is not None,
                      {"tiles": len(tiles), "rappid_tiles": len(rappid_tiles),
                       "players": players, "toMove": wst.get("toMove"),
                       "sample": tiles[:3]})
            else:
                check("wwf_renders", False, "window.commonsAgent.wwfState missing")

            # voxel_area: enter the NATIVE voxel-build zone (must NOT open an
            # iframe/window — it's a merged plot of the ONE scene), place a block,
            # and assert voxelState() shows the placed block carrying a rappid
            # `from` (signed by the player's OWN rappid, never a human stand-in).
            has_voxel = await ev("()=>typeof window.commonsAgent.voxelState==='function'", False)
            if has_voxel:
                await ev("()=>{try{window.commonsAgent.enter('voxel');}catch(e){}return 1}")
                # the plot seeds from the existing signed ops asynchronously; poll.
                st = None
                for _ in range(40):
                    st = await ev("()=>{try{return window.commonsAgent.voxelState()}catch(e){return null}}", None)
                    if st and st.get("built"):
                        break
                    await page.wait_for_timeout(250)
                # place a block via the player's own rappid, then re-read state.
                placed = await ev(
                    "()=>{try{return Promise.resolve(window.commonsAgent.voxelPlace(3,0,5,'ruby'))"
                    ".then(()=>true)}catch(e){return false}}", False)
                # voxelPlace is async (signs the op) — give it a tick to settle.
                await page.wait_for_timeout(500)
                st = await ev("()=>{try{return window.commonsAgent.voxelState()}catch(e){return null}}", None) or {}
                blocks = st.get("blocks") or []
                mine = [b for b in blocks
                        if b.get("x") == 3 and b.get("y") == 0 and b.get("z") == 5
                        and str(b.get("from", "")).startswith("rappid:")]
                rappid_blocks = [b for b in blocks if str(b.get("from", "")).startswith("rappid:")]
                check("voxel_area",
                      bool(placed) and len(mine) >= 1 and len(blocks) >= 1
                      and len(rappid_blocks) == len(blocks) and st.get("seed") is not None,
                      {"placed": placed, "blocks": len(blocks),
                       "rappid_blocks": len(rappid_blocks),
                       "seed": st.get("seed"), "sample": blocks[:3]})
            else:
                check("voxel_area", False, "window.commonsAgent.voxelState missing")

            # nexus_native: the LAST link-out portal (Nexus Worlds) is now a
            # NATIVE holographic-portals zone of the ONE scene. Entering it must
            # NOT spawn any new visible iframe (the Nexus PATTERN ported in, not
            # the external app embedded) and must expose a native frames surface.
            # Record the visible-iframe count, enter('nexus'), then assert:
            #   (i)  no NEW visible iframe was created,
            #   (ii) nexusArea().native === true,
            #   (iii) frames.length >= 1.
            # A "visible iframe" = an <iframe> with a non-empty src that is shown
            # (the inline surface panel uses one such iframe for link-out worlds;
            # nexus must add ZERO of them).
            vis_iframes = (
                "()=>Array.from(document.querySelectorAll('iframe')).filter(f=>{"
                "const s=f.getAttribute('src');"
                "const cs=getComputedStyle(f);"
                "return !!(s&&s.trim())&&cs.display!=='none'&&cs.visibility!=='hidden'"
                "&&f.offsetParent!==null;}).length")
            has_nexus = await ev("()=>typeof window.commonsAgent.nexusArea==='function'", False)
            if has_nexus:
                before = await ev(vis_iframes, 0)
                await ev("()=>{try{window.commonsAgent.enter('nexus');}catch(e){}return 1}")
                await page.wait_for_timeout(500)
                after = await ev(vis_iframes, 0)
                na = await ev(
                    "()=>{try{const a=window.commonsAgent.nexusArea();"
                    "return {native:a&&a.native===true,"
                    "frames:(a&&a.frames&&a.frames.length)||0,"
                    "sample:(a&&a.frames)?a.frames.slice(0,3):[]}}"
                    "catch(e){return {native:false,frames:0,sample:[]}}}", None) or {}
                check("nexus_native",
                      (after - before) <= 0 and bool(na.get("native"))
                      and (na.get("frames") or 0) >= 1,
                      {"iframes_before": before, "iframes_after": after,
                       "native": na.get("native"), "frames": na.get("frames"),
                       "sample": na.get("sample")})
            else:
                check("nexus_native", False, "window.commonsAgent.nexusArea missing")

            # persistence: the world REMEMBERS across a reload. The persistence
            # layer is additive + read-only -- every signed action this session
            # is ALSO mirrored into a localStorage append-only log right after it
            # is signed (signing itself is untouched). Place a signed voxel block,
            # confirm the SIGNED op now lives in localStorage, then call
            # window.commonsAgent.rehydrate() (simulating a reload's replay, which
            # signature-verifies + re-applies the stream through voxApplyOp) and
            # assert the block is STILL present in voxelState() afterward, its
            # `from` a rappid -- i.e. it survived rehydration as a signed record.
            has_persist = await ev(
                "()=>typeof window.commonsAgent.persist==='function'"
                "&&typeof window.commonsAgent.rehydrate==='function'", False)
            if has_persist:
                await ev("()=>{try{window.commonsAgent.enter('voxel');}catch(e){}return 1}")
                # place a uniquely-located signed block via the player's own rappid.
                await ev(
                    "()=>{try{return Promise.resolve(window.commonsAgent.voxelPlace(7,0,11,'sapphire'))"
                    ".then(()=>true)}catch(e){return false}}", False)
                await page.wait_for_timeout(500)
                # the freshly-signed op must now be in the localStorage append-only log,
                # carrying a rappid `from` + a real signature (read straight from storage).
                in_storage = await ev(
                    "()=>{try{const raw=localStorage.getItem('rapp-commons:persist:log/1');"
                    "if(!raw)return false;const log=JSON.parse(raw);"
                    "return log.some(r=>r.schema==='rapp-world-op/1.0'&&r.x===7&&r.y===0&&r.z===11"
                    "&&/^rappid:/.test(r.from||'')&&typeof r.sig==='string'&&r.sig.length>0);}"
                    "catch(e){return false}}", False)
                # simulate a reload's replay: rehydrate re-verifies + re-applies the
                # persisted stream. Returns the count of records replayed (>=1 here).
                replayed = await ev(
                    "()=>Promise.resolve(window.commonsAgent.rehydrate())"
                    ".then(n=>n).catch(()=>-1)", -1)
                await page.wait_for_timeout(300)
                # after rehydration the block is STILL on the plot, still signed.
                st = await ev("()=>{try{return window.commonsAgent.voxelState()}catch(e){return null}}", None) or {}
                blocks = st.get("blocks") or []
                survived = [b for b in blocks
                            if b.get("x") == 7 and b.get("y") == 0 and b.get("z") == 11
                            and str(b.get("from", "")).startswith("rappid:")]
                check("persistence",
                      bool(in_storage) and isinstance(replayed, (int, float)) and replayed >= 1
                      and len(survived) >= 1,
                      {"in_storage": in_storage, "replayed": replayed,
                       "survived": len(survived), "blocks": len(blocks)})
            else:
                check("persistence", False,
                      "window.commonsAgent.persist/rehydrate missing")
        await b.close()
    print_summary()


def print_summary():
    p = sum(1 for r in results if r); n = len(results)
    print(f"\n=== commons.html: {p}/{n} passed ===")
    sys.exit(0 if p == n and n > 0 else 1)

asyncio.run(run())
