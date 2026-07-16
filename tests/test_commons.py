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

            # resident_relationships: the villagers build BONDS and REMEMBER
            # (Animal-Crossing style). On a slow heartbeat residents emit SIGNED
            # rapp-commons-relationship/1.0 events (signed by the ACTOR's OWN
            # rappid via the existing signAs path) onto the EXISTING append-only
            # persist stream, building a per-pair AFFINITY score; bonds SURVIVE a
            # reload through the EXISTING rehydrate() replay. Over a short poll
            # assert:
            #   • commonsAgent.relationships() returns >=1 bond with a rappid
            #     `from` + `with` and a NUMERIC affinity, AND
            #   • a signed rapp-commons-relationship/1.0 event lives on the same
            #     localStorage persist stream (rappid `from` + a real signature), AND
            #   • after commonsAgent.rehydrate() the relationship SURVIVES (the
            #     same bond is still present afterward, its `from`/`with` rappids).
            has_rel = await ev(
                "()=>typeof window.commonsAgent.relationships==='function'"
                "&&typeof window.commonsAgent.greetFromResidents==='function'", False)
            if has_rel:
                relsnap = lambda: ev(
                    "()=>{try{return (window.commonsAgent.relationships()||[]).map(b=>({"
                    "from:b.from,with:b.with,affinity:b.affinity,lastKind:b.lastKind}))}"
                    "catch(e){return[]}}", [])
                # a signed relationship record on the SAME append-only signed stream,
                # carrying a rappid `from` + a real signature (read straight off storage).
                signed_on_stream = lambda: ev(
                    "()=>{try{const raw=localStorage.getItem('rapp-commons:persist:log/1');"
                    "if(!raw)return false;const log=JSON.parse(raw);"
                    "return log.some(r=>r.schema==='rapp-commons-relationship/1.0'"
                    "&&/^rappid:/.test(r.from||'')&&/^rappid:/.test(r.with||'')"
                    "&&typeof r.sig==='string'&&r.sig.length>0);}"
                    "catch(e){return false}}", False)
                have_bond = False
                sig_ok = False
                sample = {}
                for _ in range(40):                  # ~12s for the social graph to form
                    cur = await relsnap() or []
                    good = [bd for bd in cur
                            if str(bd.get("from", "")).startswith("rappid:")
                            and str(bd.get("with", "")).startswith("rappid:")
                            and isinstance(bd.get("affinity"), (int, float))]
                    have_bond = len(good) >= 1
                    sig_ok = bool(await signed_on_stream())
                    sample = {"count": len(cur), "rappid_bonds": len(good),
                              "sig_on_stream": sig_ok, "bonds": good[:3]}
                    if have_bond and sig_ok:
                        break
                    await page.wait_for_timeout(300)

                # a specific bond fingerprint (from|with) we will look for again
                # AFTER rehydrate to prove it SURVIVED a reload's replay.
                target_bond = None
                pre = await relsnap() or []
                for bd in pre:
                    if (str(bd.get("from", "")).startswith("rappid:")
                            and str(bd.get("with", "")).startswith("rappid:")):
                        target_bond = (bd["from"], bd["with"]); break

                # rehydrate (simulating a reload's verified replay) and assert the
                # bond is STILL present afterward — the world REMEMBERS the bond.
                replayed = await ev(
                    "()=>Promise.resolve(window.commonsAgent.rehydrate())"
                    ".then(n=>n).catch(()=>-1)", -1)
                await page.wait_for_timeout(300)
                post = await relsnap() or []
                survived = False
                if target_bond:
                    survived = any(bd.get("from") == target_bond[0]
                                   and bd.get("with") == target_bond[1] for bd in post)
                check("resident_relationships",
                      have_bond and sig_ok and isinstance(replayed, (int, float))
                      and replayed >= 1 and survived,
                      {"have_bond": have_bond, "sig_on_stream": sig_ok,
                       "replayed": replayed, "survived": survived,
                       "target": target_bond, "sample": sample})
            else:
                check("resident_relationships", False,
                      "window.commonsAgent.relationships/greetFromResidents missing")

            # daynight_cycle: a slow day-night clock tints the world (sky/fog/sun).
            # DETERMINISTIC -- setTimeOfDay() jumps to a fraction of the day and the
            # reported phase changes accordingly (no emergent timing / no polling).
            has_dn = await ev("()=>typeof window.commonsAgent.setTimeOfDay==='function' && typeof window.commonsAgent.timeOfDay==='function'", False)
            if has_dn:
                night = await ev("()=>{try{return window.commonsAgent.setTimeOfDay(0.0)}catch(e){return null}}", None)
                day   = await ev("()=>{try{return window.commonsAgent.setTimeOfDay(0.5)}catch(e){return null}}", None)
                tod   = await ev("()=>{try{return window.commonsAgent.timeOfDay()}catch(e){return null}}", None)
                night = night or {}; day = day or {}; tod = tod or {}
                differ = bool(night.get("phase")) and bool(day.get("phase")) and night.get("phase") != day.get("phase")
                check("daynight_cycle",
                      differ and night.get("phase") == "night" and day.get("phase") == "day"
                      and isinstance(tod.get("t"), (int, float)),
                      {"night": night, "day": day, "now": tod})
            else:
                check("daynight_cycle", False,
                      "window.commonsAgent.timeOfDay/setTimeOfDay missing")

            # night_lanterns: warm lanterns GLOW when the day-night clock is dark.
            # DETERMINISTIC -- a pure function of setTimeOfDay(): lit at night, off by day.
            has_lan = await ev("()=>typeof window.commonsAgent.lanterns==='function'", False)
            if has_lan:
                lan_night = await ev("()=>{try{window.commonsAgent.setTimeOfDay(0.0);return window.commonsAgent.lanterns()}catch(e){return null}}", None)
                lan_day   = await ev("()=>{try{window.commonsAgent.setTimeOfDay(0.5);return window.commonsAgent.lanterns()}catch(e){return null}}", None)
                lan_night = lan_night or []; lan_day = lan_day or []
                enough = len(lan_night) >= 4
                night_lit = enough and all(L.get("on") for L in lan_night)
                day_off   = len(lan_day) >= 4 and all(not L.get("on") for L in lan_day)
                has_coords = enough and all(isinstance(L.get("at", {}).get("x"), (int, float)) for L in lan_night)
                check("night_lanterns",
                      bool(night_lit and day_off and has_coords),
                      {"n": len(lan_night), "night_lit": night_lit, "day_off": day_off})
            else:
                check("night_lanterns", False, "window.commonsAgent.lanterns missing")

            # spawn_signpost: a venue directory with compass bearings from spawn.
            # DETERMINISTIC -- pure function of the venue coords (north=-Z, east=+X).
            has_dir = await ev("()=>typeof window.commonsAgent.directory==='function'", False)
            if has_dir:
                d = await ev("()=>{try{return window.commonsAgent.directory()}catch(e){return null}}", None)
                d = d or []
                compass = {"N","NE","E","SE","S","SW","W","NW"}
                enough = len(d) >= 5
                valid = enough and all(
                    isinstance(e.get("bearing"), (int, float)) and 0 <= e["bearing"] < 360
                    and e.get("direction") in compass
                    and isinstance(e.get("at", {}).get("x"), (int, float)) for e in d)
                poker = next((e for e in d if "poker" in e.get("name", "").lower()), None)
                words = next((e for e in d if "word" in e.get("name", "").lower()), None)
                poker_e = bool(poker) and poker["direction"] in ("NE", "E", "SE")
                words_w = bool(words) and words["direction"] in ("NW", "W", "SW")
                check("spawn_signpost", bool(valid and poker_e and words_w),
                      {"n": len(d), "poker": poker, "words": words})
            else:
                check("spawn_signpost", False, "window.commonsAgent.directory missing")

            # resident_schedule: the villagers keep a daily rhythm -- HOME at night,
            # ROAM by day. DETERMINISTIC -- pure function of setTimeOfDay() (no poll).
            has_sched = await ev("()=>typeof window.commonsAgent.residentSchedule==='function'", False)
            if has_sched:
                sched_night = await ev("()=>{try{window.commonsAgent.setTimeOfDay(0.0);return window.commonsAgent.residentSchedule()}catch(e){return null}}", None)
                sched_day   = await ev("()=>{try{window.commonsAgent.setTimeOfDay(0.5);return window.commonsAgent.residentSchedule()}catch(e){return null}}", None)
                sched_night = sched_night or []; sched_day = sched_day or []
                enough = len(sched_night) >= 2
                night_home = enough and all(r.get("mode") == "home" for r in sched_night)
                day_roam   = len(sched_day) >= 2 and all(r.get("mode") == "roam" for r in sched_day)
                has_home   = enough and all(isinstance(r.get("home", {}).get("x"), (int, float))
                                            and str(r.get("from", "")).startswith("rappid:") for r in sched_night)
                # at night each resident's target IS its home anchor.
                targets_home = enough and all(r.get("target") == r.get("home") for r in sched_night)
                check("resident_schedule",
                      bool(night_home and day_roam and has_home and targets_home),
                      {"n": len(sched_night), "night_home": night_home,
                       "day_roam": day_roam, "targets_home": targets_home})
            else:
                check("resident_schedule", False, "window.commonsAgent.residentSchedule missing")

            # fractal_frames: an in-world screen houses ANOTHER commons (a world within the
            # world) -- NOT a link-out (reuses the in-world surface iframe), self-similar, and
            # depth-capped. DETERMINISTIC: enter('fractal') mounts the nested commons inline.
            has_fr = await ev("()=>typeof window.commonsAgent.fractal==='function'", False)
            if has_fr:
                fr0 = await ev("()=>{try{return window.commonsAgent.fractal()}catch(e){return null}}", None) or {}
                await ev("()=>{try{window.commonsAgent.enter('fractal')}catch(e){}return 1}")
                frm = None
                for _ in range(12):
                    frm = await ev("()=>{try{return window.commonsAgent.fractal()}catch(e){return null}}", None)
                    if frm and frm.get("mounted"):
                        break
                    await page.wait_for_timeout(400)
                frm = frm or {}
                src = str(fr0.get("nestedSrc") or "")
                check("fractal_frames",
                      fr0.get("depth") == 0 and fr0.get("maxDepth", 0) >= 1 and fr0.get("canNest") is True
                      and "depth=1" in src and "light=1" in src and frm.get("mounted") is True,
                      {"fr0": fr0, "mounted": frm.get("mounted"), "nestedSrc": src})
                # unmount the nested world so it doesn't compete with later timing-sensitive tests
                await ev("()=>{const f=document.getElementById('surfaceFrame');if(f){f.removeAttribute('srcdoc');f.removeAttribute('src');}return 1}")
                await page.wait_for_timeout(300)
            else:
                check("fractal_frames", False, "window.commonsAgent.fractal missing")

            # MATRIX — the universe on commonsAgent: 4D address, frame mechanism, dream-catcher
            # merge, and the double jump. The commons IS the living hologram organism.
            mx = await ev("()=>!!window.commonsAgent && typeof window.commonsAgent.doubleJump==='function'", False)
            if mx:
                # 4D coordinate: 3D space + frame-time + a UTC iso string
                c = await ev("()=>{try{return window.commonsAgent.coordinate()}catch(e){return null}}", None) or {}
                import re as _re
                coord_ok = (isinstance(c.get("x"), (int, float)) and isinstance(c.get("y"), (int, float))
                            and isinstance(c.get("z"), (int, float)) and isinstance(c.get("frame"), int)
                            and bool(_re.match(r"\d{4}-\d\d-\d\dT", str(c.get("utc", "")))))
                check("matrix_4d", coord_ok, c)

                # frame mechanism: freeze a save-state, navigate away, resume restores it, fork -> dimension id
                fm = await ev("""()=>{try{
                    const t=window.commonsAgent.freeze();
                    const before=window.commonsAgent.coordinate().x;
                    window.commonsAgent.teleport(7,1.6,3); const moved=window.commonsAgent.coordinate().x;
                    window.commonsAgent.resume(t); const back=window.commonsAgent.coordinate().x;
                    const dim=window.commonsAgent.fork(t);
                    return {has_token:!!t, before, moved, back, dim};
                }catch(e){return {err:String(e)}}}""", {}) or {}
                frame_ok = (fm.get("has_token") and abs((fm.get("moved") or 0) - 7) < 1.5
                            and abs((fm.get("back", 99)) - (fm.get("before", -99))) < 1.0
                            and isinstance(fm.get("dim"), str) and fm.get("dim"))
                check("matrix_frame", bool(frame_ok), fm)

                # dream-catcher merge: keep a consistent candidate, reject a contradicting one
                dc = await ev("""()=>{try{
                    return window.commonsAgent.merge({a:1,b:2},[{key:'c',val:3},{key:'a',val:1},{key:'a',val:9}]);
                }catch(e){return {err:String(e)}}}""", {}) or {}
                keys_kept = {k.get("key") for k in (dc.get("kept") or [])}
                dc_ok = ("c" in keys_kept and any(r.get("key") == "a" and r.get("val") == 9 for r in (dc.get("rejected") or [])))
                check("matrix_merge", bool(dc_ok), dc)

                # double jump: two loops compete, the trailing climbs, the best improves, leaders alternate
                dj = await ev("()=>{try{return window.commonsAgent.doubleJump(6)}catch(e){return null}}", None) or {}
                rounds = dj.get("rounds") or []
                dj_ok = (len(rounds) >= 4 and dj.get("trailing", {}).get("last", 0) > dj.get("trailing", {}).get("first", 1)
                         and dj.get("best", {}).get("last", 0) >= dj.get("best", {}).get("first", 0)
                         and dj.get("improved") is True and len(set(r.get("leader") for r in rounds)) >= 2)
                check("matrix_double_jump", bool(dj_ok),
                      {"trailing": dj.get("trailing"), "best": dj.get("best"), "leaders": [r.get("leader") for r in rounds]})

                # EVO round 1 — MEMENTO: re-derive the world at a past 4D coordinate from the signed
                # stream (verify-gated; far-out unique coords so resident ops never collide).
                mem = await ev("""async ()=>{try{
                    await window.commonsAgent.voxelPlace(99,5,99,'red');
                    await window.commonsAgent.voxelPlace(98,5,98,'blue');
                    const me=window.commonsAgent.me().rappid;
                    const mine=window.commonsAgent.timeline().filter(r=>r.schema==='rapp-world-op/1.0'&&String(r.from)===String(me));
                    const iRed=mine[mine.length-2].i, iBlue=mine[mine.length-1].i;
                    const r1=await window.commonsAgent.rewind({index:iRed});
                    const r2=await window.commonsAgent.rewind({index:iBlue});
                    const r2b=await window.commonsAgent.rewind({index:iBlue});
                    const has=(a,x,z)=>a.some(v=>v.x===x&&v.z===z);
                    return {r1_red:has(r1.voxels,99,99), r1_blue:has(r1.voxels,98,98),
                            r2_red:has(r2.voxels,99,99), r2_blue:has(r2.voxels,98,98),
                            deterministic:JSON.stringify(r2.voxels)===JSON.stringify(r2b.voxels)};
                }catch(e){return {err:String(e)}}}""", {}) or {}
                check("evo_memento",
                      bool(mem.get("r1_red") and not mem.get("r1_blue") and mem.get("r2_red")
                           and mem.get("r2_blue") and mem.get("deterministic")), mem)

                # MEMENTO verify-gate: tamper a record's signature -> rewind DROPS it (can't forge history). Self-restoring.
                tam = await ev("""async ()=>{try{
                    const K='rapp-commons:persist:log/1';
                    const log=JSON.parse(localStorage.getItem(K)||'[]');
                    let idx=-1; for(let i=log.length-1;i>=0;i--){const r=log[i];if(r.schema==='rapp-world-op/1.0'&&r.x===98&&r.z===98){idx=i;break;}}
                    if(idx<0) return {found:false};
                    const orig=log[idx].sig; log[idx].sig=(orig[0]==='a'?'b':'a')+orig.slice(1);
                    localStorage.setItem(K,JSON.stringify(log));
                    const r=await window.commonsAgent.rewind({index:log.length-1});
                    const has=(a,x,z)=>a.some(v=>v.x===x&&v.z===z);
                    const res={found:true, dropped:r.dropped, blue_absent:!has(r.voxels,98,98)};
                    log[idx].sig=orig; localStorage.setItem(K,JSON.stringify(log));
                    return res;
                }catch(e){return {err:String(e)}}}""", {}) or {}
                check("evo_memento_verify", bool(tam.get("found") and (tam.get("dropped") or 0) >= 1 and tam.get("blue_absent")), tam)

                # TIME CAPSULE: a sealed signed prophecy in its own dimension, adjudicated by the merge.
                cap = await ev("""async ()=>{try{
                    await window.commonsAgent.voxelPlace(97,5,97,'blue');
                    const t=window.commonsAgent.freeze();
                    const sealed=await window.commonsAgent.sealCapsule({key:'vox:97,5,97',val:'blue'},{frame:t.frame});
                    const t2=window.commonsAgent.freeze();
                    const seal2=await window.commonsAgent.sealCapsule({key:'vox:97,5,97',val:'red'},{frame:t2.frame});
                    window.commonsAgent.freeze();
                    const r=await window.commonsAgent.openCapsules();
                    const f=r.find(c=>c.id===sealed.id), b=r.find(c=>c.id===seal2.id);
                    return {f_status:f&&f.status, f_reason:(f&&f.verdict&&f.verdict.reason)||'', f_dim:(f&&f.dimension)||0,
                            b_status:b&&b.status, b_reason:(b&&b.verdict&&b.verdict.reason)||''};
                }catch(e){return {err:String(e)}}}""", {}) or {}
                check("evo_capsule",
                      bool(cap.get("f_status") == "fulfilled" and "matches" in str(cap.get("f_reason"))
                           and (cap.get("f_dim") or 0) > 0 and cap.get("b_status") == "broken"
                           and "glitch" in str(cap.get("b_reason"))), cap)

                # GENESIS CRUCIBLE: two builder loops; the laggard adopts the leader (double jump on signed voxels).
                cru = await ev("()=>window.commonsAgent.crucible(4)", None) or {}
                check("evo_crucible",
                      bool((cru.get("A") or 0) > 0 and (cru.get("B") or 0) > 0 and cru.get("converged") is True
                           and (cru.get("last_gap", 9)) < (cru.get("first_gap", 0)) and len(cru.get("history") or []) >= 4),
                      {"A": cru.get("A"), "B": cru.get("B"), "first_gap": cru.get("first_gap"), "last_gap": cru.get("last_gap")})

                # DIMENSION LIFECYCLE: drop-in/unfreeze forks a dimension; reconcile its diff back to
                # main — merge the additive change cleanly, detect a conflict, abandon back to main's version.
                dimt = await ev("""async ()=>{try{
                    const A=window.commonsAgent;
                    const s1=A.splitDimension();
                    await A.voxelPlace(88,5,88,'green');                 // additive divergence
                    const d1=A.dimensionDiff(s1.dim);
                    const r1=A.reconcileDimension(s1.dim,'merge');        // merges cleanly + closes
                    await A.voxelPlace(87,5,87,'blue');                  // main establishes a cell
                    const s2=A.splitDimension();
                    await A.voxelPlace(87,5,87,'red');                   // diverge: change main's cell -> conflict
                    const r2=A.reconcileDimension(s2.dim,'merge');        // conflict detected, stays open
                    const r3=A.reconcileDimension(s2.dim,'abandon');      // snap back to main (blue), close
                    const cur=A.voxelState().blocks.find(b=>b.x===87&&b.z===87);
                    return { add_in_diff:d1.to_reconcile.some(c=>c.key==='vox:88,5,88'&&c.dim==='green'),
                             merged_clean:(r1.merged>=1 && r1.conflicts.length===0 && r1.closed===true && r1.back_on_main===true),
                             conflict:(r2.conflicts.length>=1 && r2.closed===false),
                             abandon_closed:(r3.closed===true && r3.mode==='abandon'),
                             reverted_blue:(cur && cur.block==='blue') };
                }catch(e){return {err:String(e)}}}""", {}) or {}
                check("evo_dimension",
                      bool(dimt.get("add_in_diff") and dimt.get("merged_clean") and dimt.get("conflict")
                           and dimt.get("abandon_closed") and dimt.get("reverted_blue")), dimt)

                # EVO round 2 — CAUSALITY LENS: prove which signed record CAUSED a cell to exist
                # (counterfactual: verify-drop the cause -> the predicate dies). Far-out unique coord.
                caus = await ev("""async ()=>{try{
                    const A=window.commonsAgent; const base=A.timeline().length;
                    await A.voxelPlace(123,5,123,'red');
                    const r=await A.because({voxAt:[123,5,123]});
                    const log=JSON.parse(localStorage.getItem('rapp-commons:persist:log/1')||'[]');
                    const op=log.find(x=>x.schema==='rapp-world-op/1.0'&&x.op==='place'&&x.x===123&&x.z===123);
                    const r2=await A.because({voxAt:[123,5,123]});
                    const stillRed=A.voxelState().blocks.some(b=>b.x===123&&b.z===123&&b.block==='red');
                    return { cause_match:(r.causeRecord&&op&&r.causeRecord.sig===op.sig),
                             first_ok:(r.firstTrueAt&&r.firstTrueAt.index>=base-1),
                             cf:(r.counterfactual.withCause===true&&r.counterfactual.withoutCause===false),
                             att:(typeof r.attestationSig==='string'&&r.attestationSig.length>0),
                             deterministic:(r2.causeRecord&&r.causeRecord&&r2.causeRecord.sig===r.causeRecord.sig),
                             still_red:stillRed };
                }catch(e){return {err:String(e)}}}""", {}) or {}
                check("evo_causality",
                      bool(caus.get("cause_match") and caus.get("cf") and caus.get("att")
                           and caus.get("deterministic") and caus.get("still_red")), caus)

                # CHRONO-DIFF: the signed, deterministic diff between two 4D coordinates.
                chrono = await ev("""async ()=>{try{
                    const A=window.commonsAgent;
                    const a={index:A.timeline().length-1};
                    await A.voxelPlace(140,2,140,'blue');
                    await A.voxelPlace(141,2,141,'green');
                    await A.voxelPlace(142,2,142,'red'); await A.voxelMine(142,2,142);
                    const c={index:A.timeline().length-1};
                    const d=await A.diff(a,c); const d2=await A.diff(a,c);
                    const has=(arr,cell)=>arr.some(x=>x.cell===cell);
                    return { blue:has(d.added,'140,2,140'), green:has(d.added,'141,2,141'),
                             net_out:(!has(d.added,'142,2,142')),
                             sealed:(typeof d.sealed.sig==='string'&&typeof d.sealed.hash==='string'),
                             deterministic:(d.sealed.hash===d2.sealed.hash) };
                }catch(e){return {err:String(e)}}}""", {}) or {}
                check("evo_chrono_diff",
                      bool(chrono.get("blue") and chrono.get("green") and chrono.get("net_out")
                           and chrono.get("sealed") and chrono.get("deterministic")), chrono)

                # MANY-WORLDS COLLAPSE: fork N rivals for one cell; the dream-catcher elects the survivor.
                coll = await ev("""async ()=>{try{
                    const A=window.commonsAgent; const key='vox:150,3,150';
                    const r=await A.collapse(key,[{val:'gold',by:'a'},{val:'gold',by:'b'},{val:'iron',by:'c'}]);
                    const cur=A.voxelState().blocks.find(b=>b.x===150&&b.z===150);
                    return { survivor:(r.survivor&&r.survivor.val), committed:(typeof r.committedSig==='string'),
                             bracket:(typeof r.bracketSig==='string'), forks:((r.forks||[]).length===3),
                             in_world:(cur&&cur.block==='gold') };
                }catch(e){return {err:String(e)}}}""", {}) or {}
                check("evo_collapse",
                      bool(coll.get("survivor") == "gold" and coll.get("committed") and coll.get("bracket")
                           and coll.get("forks") and coll.get("in_world")), coll)

                # EVO round 3 — CASCADE: pull one signed record, watch the downstream truths topple.
                casc = await ev("""async ()=>{try{
                    const A=window.commonsAgent;
                    await A.voxelPlace(170,6,170,'red'); await A.voxelPlace(171,6,171,'blue');
                    const log=JSON.parse(localStorage.getItem('rapp-commons:persist:log/1')||'[]');
                    const op=log.find(r=>r.schema==='rapp-world-op/1.0'&&r.op==='place'&&r.x===170&&r.y===6&&r.z===170);
                    const c=await A.cascade(op.sig); const c2=await A.cascade(op.sig);
                    const stillRed=A.voxelState().blocks.some(b=>b.x===170&&b.z===170&&b.block==='red');
                    const e=await A.cascade('deadbeef-not-a-sig');
                    return { orphaned170:c.blastRadius.some(b=>b.voxAt[0]===170&&b.voxAt[1]===6&&b.voxAt[2]===170),
                             not171:c.blastRadius.every(b=>b.voxAt[0]!==171),
                             shrank:(c.survivorsAfter<c.survivorsBefore),
                             sig:(typeof c.cascadeSig==='string'&&c.cascadeSig.length>0),
                             readonly:stillRed, deterministic:(JSON.stringify(c2.blastRadius)===JSON.stringify(c.blastRadius)),
                             empty:(e.blastRadius.length===0&&e.depth===0) };
                }catch(e){return {err:String(e)}}}""", {}) or {}
                check("evo_cascade",
                      bool(casc.get("orphaned170") and casc.get("not171") and casc.get("shrank") and casc.get("sig")
                           and casc.get("readonly") and casc.get("deterministic") and casc.get("empty")), casc)

                # BYZANTINE QUORUM: N distinct keypairs must corroborate before a fact commits.
                quo = await ev("""async ()=>{try{
                    const A=window.commonsAgent; const key='vox:92,4,92';
                    await A.attest(key,'gold'); await A.attest(key,'gold'); await A.attest(key,'gold'); await A.attest(key,'iron');
                    const q=await A.quorum(key,3);
                    const cur=A.voxelState().blocks.find(b=>b.x===92&&b.z===92);
                    const q5=await A.quorum(key,5);
                    const cur5=A.voxelState().blocks.find(b=>b.x===92&&b.z===92);
                    return { elected:q.elected, witnesses:(q.distinctWitnesses||[]).length, committed:(typeof q.committedSig==='string'),
                             reached:q.reached, in_world:(cur&&cur.block==='gold'),
                             gate:(q5.reached===false&&q5.committedSig==null&&cur5&&cur5.block==='gold') };
                }catch(e){return {err:String(e)}}}""", {}) or {}
                check("evo_quorum",
                      bool(quo.get("elected") == "gold" and (quo.get("witnesses") or 0) >= 3 and quo.get("committed")
                           and quo.get("reached") and quo.get("in_world") and quo.get("gate")), quo)

                # IMMUNE SYSTEM: inject a forgery, then heal — quarantine it + restore the true 3D world.
                imm = await ev("""async ()=>{try{
                    const A=window.commonsAgent;
                    await A.voxelPlace(170,5,170,'gold');             // honest
                    A.injectForgery(170,5,170,'iron');               // a forged op claims iron (broken sig)
                    const before=A.voxelState().blocks.find(b=>b.x===170&&b.y===5&&b.z===170);
                    const h=await A.heal();
                    const after=A.voxelState().blocks.find(b=>b.x===170&&b.y===5&&b.z===170);
                    const h2=await A.heal();
                    return { lie_surfaced:(before&&before.block==='iron'),
                             quarantined:(h.quarantined>=1), tainted:((h.tainted||[]).length>=1),
                             restored:(h.cells_restored>=1), healed:(after&&after.block==='gold'),
                             report:(typeof h.reportSig==='string'), idempotent:(h2.cells_restored===0) };
                }catch(e){return {err:String(e)}}}""", {}) or {}
                check("evo_immune",
                      bool(imm.get("quarantined") and imm.get("tainted") and imm.get("restored")
                           and imm.get("healed") and imm.get("report") and imm.get("idempotent")), imm)

                # CREATURE / WILDLIFE HABITAT: a Lineage trait vector becomes a real 3D creature.
                crt = await ev("""async ()=>{try{
                    const A=window.commonsAgent;
                    A.spawnCreature({explore:0.95,exploit:0.2,cooperate:0.3,aggress:0.1}); const c1=A.creature();
                    A.spawnCreature({explore:0.1,exploit:0.2,cooperate:0.2,aggress:0.95}); const c2=A.creature();
                    const prof=A.creatureProfile({cooperate:0.9,explore:0.2,exploit:0.2,aggress:0.1});
                    return { spawned:(c1&&c1.spawned===true),
                             explorer:(c1.dominant==='explore'&&/Wanderer/.test(c1.name)),
                             render:(c2.dominant==='aggress'&&/Render/.test(c2.name)),
                             color:(typeof c1.color==='number'),
                             profile:(typeof prof.habitat==='string'&&typeof prof.behavior==='string'&&prof.dominant==='cooperate'),
                             pos:(c1.pos&&typeof c1.pos.x==='number') };
                }catch(e){return {err:String(e)}}}""", {}) or {}
                check("creature_habitat",
                      bool(crt.get("spawned") and crt.get("explorer") and crt.get("render")
                           and crt.get("color") and crt.get("profile") and crt.get("pos")), crt)

                # FIDELITY: ACES filmic tone-mapping + exposure breathing with the day-night clock.
                tone = await ev("""async ()=>{try{const A=window.commonsAgent;
                    const t=A.tone();
                    setTimeOfDay(0.5); const eday=A.tone().exposure;
                    setTimeOfDay(0.0); const enight=A.tone().exposure;
                    setTimeOfDay(0.42);
                    return { aces:(t.toneMapping===THREE.ACESFilmicToneMapping),
                             srgb:(t.outputEncoding===THREE.sRGBEncoding),
                             breathes:(enight>eday),
                             bounds:(eday>=0.6&&eday<=1.8&&enight>=0.6&&enight<=1.8) };
                }catch(e){return {err:String(e)}}}""", {}) or {}
                check("fidelity_tone",
                      bool(tone.get("aces") and tone.get("srgb") and tone.get("breathes") and tone.get("bounds")), tone)

                # FIDELITY: AerialFog — FogExp2 depth haze, clock-driven density, horizon-tinted colour.
                fog = await ev("""async ()=>{try{const A=window.commonsAgent;
                    const f=A.fog();
                    setTimeOfDay(0.42); const noon=A.fog();
                    setTimeOfDay(0.80); const dusk=A.fog();
                    setTimeOfDay(0.42);
                    return { exp2:(f.type==='FogExp2'), dense:(f.density>0),
                             denserAtDusk:(dusk.density>noon.density),
                             colorShifts:(dusk.color!==noon.color) };
                }catch(e){return {err:String(e)}}}""", {}) or {}
                check("fidelity_aerialfog",
                      bool(fog.get("exp2") and fog.get("dense") and fog.get("denserAtDusk") and fog.get("colorShifts")), fog)

                # FIDELITY: scattering sky dome v2 — three-band gradient + clock-driven horizon haze + sun glow.
                sky = await ev("""async ()=>{try{const A=window.commonsAgent;
                    const exists=(scene.getObjectByName('SkyDome')&&scene.getObjectByName('SkyDome').isMesh);
                    setTimeOfDay(0.5); const noon=A.atmosphere();
                    setTimeOfDay(0.0); const mid=A.atmosphere();
                    setTimeOfDay(0.22); const dawnHaze=A.atmosphere().haze;
                    setTimeOfDay(0.5); const noonHaze=A.atmosphere().haze;
                    setTimeOfDay(0.42);
                    return { exists:!!exists, sunHighNoon:(noon.sunDirY>0.5), sunLowMidnight:(mid.sunDirY<0.3),
                             hazeDawnGtNoon:(dawnHaze>noonHaze), horizonTinted:(noon.horizon!==mid.horizon) };
                }catch(e){return {err:String(e)}}}""", {}) or {}
                check("fidelity_sky",
                      bool(sky.get("exists") and sky.get("sunHighNoon") and sky.get("sunLowMidnight")
                           and sky.get("hazeDawnGtNoon") and sky.get("horizonTinted")), sky)

                # FIDELITY: instanced flora field — trees/shrubs/grass blanket the terrain in <=5 draws, venue-clear.
                flora = await ev("""async ()=>{try{const A=window.commonsAgent;
                    const grp=scene.getObjectByName('flora-field');
                    const trees=scene.getObjectByName('flora-trees');
                    const f1=A.flora(), f2=A.flora();
                    return { group:!!grp, treesInst:(trees&&trees.isInstancedMesh===true), treeCount:(trees?trees.count:0),
                             total:(f1?f1.count:0), draws:(f1?f1.draws:99), clear:(f1?f1.minClear:-1),
                             deterministic:(f1&&f2&&f1.count===f2.count&&f1.minClear===f2.minClear) };
                }catch(e){return {err:String(e)}}}""", {}) or {}
                check("fidelity_flora",
                      bool(flora.get("group") and flora.get("treesInst") and (flora.get("treeCount") or 0) >= 300
                           and (flora.get("total") or 0) >= 1200 and (flora.get("draws") or 99) <= 5
                           and (flora.get("clear") or -1) > 0 and flora.get("deterministic")), flora)

                # FIDELITY: clock-driven HemisphereLight (sky/ground bounce, golden-hour graded).
                hemi = await ev("""async ()=>{try{const A=window.commonsAgent;
                    const exists=(scene.getObjectByName('HemiBounce')&&scene.getObjectByName('HemiBounce').isHemisphereLight===true);
                    setTimeOfDay(0.22); const dawn=A.hemi();
                    setTimeOfDay(0.0); const night=A.hemi();
                    setTimeOfDay(0.5); const noon=A.hemi();
                    setTimeOfDay(0.42);
                    return { exists:!!exists, warmDawn:(dawn.warmAtGolden===true), coolNoon:(noon.warmAtGolden===false),
                             dawnBrighter:(dawn.intensity>night.intensity), tinted:(dawn.sky!==noon.sky) };
                }catch(e){return {err:String(e)}}}""", {}) or {}
                check("fidelity_hemi",
                      bool(hemi.get("exists") and hemi.get("warmDawn") and hemi.get("coolNoon")
                           and hemi.get("dawnBrighter") and hemi.get("tinted")), hemi)

                # FIDELITY: heightmapped terrain via a shared groundHeight(x,z) sampler — flat plaza, relief at the rim.
                terr = await ev("""async ()=>{try{const A=window.commonsAgent;
                    const t=A.terrain(); const g=scene.getObjectByName('terrain-ground');
                    const floraOk=(A.flora()&&A.flora().count>=1200);
                    return { ground:!!g, plazaFlat:(t.plazaFlat===true), rimRelief:t.rimRelief, sampler:(t.sampler==='groundHeight'),
                             floraIntact:floraOk };
                }catch(e){return {err:String(e)}}}""", {}) or {}
                check("fidelity_terrain",
                      bool(terr.get("ground") and terr.get("plazaFlat") and (terr.get("rimRelief") or 0) > 3
                           and terr.get("sampler") and terr.get("floraIntact")), terr)

                # FIDELITY: StarField celestial vault — fades in at night, out by day, deterministic.
                stars = await ev("""async ()=>{try{const A=window.commonsAgent;
                    const sf=scene.getObjectByName('StarField');
                    const isPts=(sf&&sf.isPoints===true&&sf.geometry.attributes.position.count===1800);
                    setTimeOfDay(0.0); const night=A.stars().opacity;
                    setTimeOfDay(0.5); const noon=A.stars().opacity;
                    setTimeOfDay(0.42);
                    const f1=A.stars().firstStar, f2=A.stars().firstStar;
                    return { pts:!!isPts, nightFull:(night>0.85), noonGone:(noon<0.05),
                             deterministic:(JSON.stringify(f1)===JSON.stringify(f2)) };
                }catch(e){return {err:String(e)}}}""", {}) or {}
                check("fidelity_stars",
                      bool(stars.get("pts") and stars.get("nightFull") and stars.get("noonGone") and stars.get("deterministic")), stars)

                # FIDELITY: terrain vertex painting — grass/earth/rock bands + dirt paths.
                tpaint = await ev("""async ()=>{try{const A=window.commonsAgent;
                    const g=scene.getObjectByName('terrain-ground'); const tp=A.terrainPaint();
                    const ca=g&&g.geometry.attributes.color;
                    const lc=tp.samples.find(s=>s.at[0]===30).hex;
                    const r=parseInt(lc.slice(1,3),16),gg=parseInt(lc.slice(3,5),16),bb=parseInt(lc.slice(5,7),16);
                    return { painted:tp.painted, vc:tp.vertexColors,
                             colorCount:(ca&&ca.count===g.geometry.attributes.position.count),
                             lowlandGreen:(gg>r&&gg>bb) };
                }catch(e){return {err:String(e)}}}""", {}) or {}
                check("fidelity_terrainpaint",
                      bool(tpaint.get("painted") and tpaint.get("vc") and tpaint.get("colorCount") and tpaint.get("lowlandGreen")), tpaint)

                # FIDELITY: golden-hour god rays — on at dawn/dusk, off at noon and night.
                gray = await ev("""async ()=>{try{const A=window.commonsAgent;
                    const g=scene.getObjectByName('godRays');
                    setTimeOfDay(0.22); const dawn=A.godrays().intensity;
                    setTimeOfDay(0.5); const noon=A.godrays().intensity;
                    setTimeOfDay(0.0); const night=A.godrays().intensity;
                    setTimeOfDay(0.42);
                    return { present:!!g, dawnOn:(dawn>0.1), noonOff:(noon<0.05), nightOff:(night<0.05) };
                }catch(e){return {err:String(e)}}}""", {}) or {}
                check("fidelity_godrays",
                      bool(gray.get("present") and gray.get("dawnOn") and gray.get("noonOff") and gray.get("nightOff")), gray)

                # FIDELITY: drifting cloudscape + sun/moon celestial bodies.
                sky2 = await ev("""async ()=>{try{const A=window.commonsAgent;
                    const cd=scene.getObjectByName('CloudDome'); const grp=scene.getObjectByName('CelestialBodies');
                    const sd=scene.getObjectByName('SunDisc'), md=scene.getObjectByName('MoonDisc');
                    const driftMag=Math.hypot(A.clouds().drift[0],A.clouds().drift[1]);
                    setTimeOfDay(0.8); const covDusk=A.clouds().coverage;
                    setTimeOfDay(0.5); const covDay=A.clouds().coverage;
                    const noon=A.celestial();
                    setTimeOfDay(0.0); const night=A.celestial();
                    const t1=A.clouds().scrollT; await new Promise(r=>setTimeout(r,180)); const t2=A.clouds().scrollT;
                    setTimeOfDay(0.42);
                    return { cloudDome:!!(cd&&cd.material&&cd.material.transparent), drift:(driftMag>0),
                             duskThicker:(covDusk>covDay), scrolls:(t2>t1),
                             bodies:!!(grp&&sd&&md),
                             noonSunUp:(noon.sun.y>0 && noon.sun.visible===true), noonMoonGone:(noon.moon.opacity<0.1),
                             nightMoonUp:(night.moon.opacity>0.5), antipodal:(noon.sun.y>0 && noon.moon.y<0 && night.sun.y<0 && night.moon.y>0) };
                }catch(e){return {err:String(e)}}}""", {}) or {}
                check("fidelity_celestial",
                      bool(sky2.get("cloudDome") and sky2.get("drift") and sky2.get("duskThicker") and sky2.get("scrolls")
                           and sky2.get("bodies") and sky2.get("noonSunUp") and sky2.get("noonMoonGone")
                           and sky2.get("nightMoonUp") and sky2.get("antipodal")), sky2)

                # FIDELITY: procedural bloom halos — additive, shared texture, swell after dark.
                bloom = await ev("""async ()=>{try{const A=window.commonsAgent; const g=scene.getObjectByName('BloomHalos'); const b=A.bloom();
                    setTimeOfDay(0.0); const night=A.bloom().nightGlow;
                    setTimeOfDay(0.5); const noon=A.bloom().nightGlow;
                    setTimeOfDay(0.42);
                    return { isGroup:(g&&g.type==='Group'), halos:b.halos, matches:(g&&g.children.length===b.halos),
                             additive:b.additive, shared:b.sharedTexture, noDW:b.noDepthWrite, swells:(night>noon) };
                }catch(e){return {err:String(e)}}}""", {}) or {}
                check("fidelity_bloom",
                      bool(bloom.get("isGroup") and (bloom.get("halos") or 0) >= 8 and bloom.get("matches")
                           and bloom.get("additive") and bloom.get("shared") and bloom.get("noDW") and bloom.get("swells")), bloom)

                # FIDELITY: grounded sun shadows — widened frustum, soft PCF, follows the player.
                sh = await ev("""async ()=>{try{const s=window.commonsAgent.shadows();
                    return { enabled:s.enabled, type:s.type, frustum:s.frustum, bias:s.bias, normalBias:s.normalBias, radius:s.radius, cast:s.castShadow, follows:s.followsPlayer };
                }catch(e){return {err:String(e)}}}""", {}) or {}
                check("fidelity_shadows",
                      bool(sh.get("enabled") and sh.get("type") == "PCFSoft" and (sh.get("frustum") or 0) >= 200
                           and sh.get("bias") == -0.0006 and sh.get("normalBias") == 0.04 and sh.get("radius") == 4
                           and sh.get("cast") and sh.get("follows")), sh)

                # THE GENESIS DIMENSION — the Commons knows the moment it made contact with time.
                gen = await ev("""async ()=>{try{const g=window.commonsAgent.genesis();
                    return { dim:g.dimension, born:g.born, hasRappid:/^rappid:dimension:/.test(g.rappid||""), open:(g.join==="open") };
                }catch(e){return {err:String(e)}}}""", {}) or {}
                check("genesis_dimension",
                      bool(gen.get("dim") == "RAPP Commons" and gen.get("born") == 1778521758000 and gen.get("hasRappid") and gen.get("open")), gen)

                # FIDELITY: articulated walk rig — legs swing about the hip as the creature moves.
                rig = await ev("""async ()=>{try{
                    spawnCreature({explore:0.7,exploit:0.5,cooperate:0.5,aggress:0.3});
                    const leg0=scene.getObjectByName('creature-leg-0'), leg1=scene.getObjectByName('creature-leg-1'), leg2=scene.getObjectByName('creature-leg-2');
                    const isGroup=!!(leg0 && leg0.type==='Group' && leg0.children.length===1 && leg0.children[0].isMesh);
                    const gp0=CREATURE.gaitPhase||0;
                    CREATURE.target=new THREE.Vector3(600,0,600);
                    let signs=[]; for(let i=0;i<14;i++){ creatureTick(0.05); signs.push(Math.sign(leg0.rotation.x)); }
                    const changedSign=signs.some((s,i)=>i>0 && s!==0 && signs[i-1]!==0 && s!==signs[i-1]);
                    return { isGroup, gaitIncreased:(CREATURE.gaitPhase>gp0), changedSign,
                             pairClose:(Math.abs(leg0.rotation.x-leg2.rotation.x)<0.001),
                             antiPhase:(Math.sign(leg0.rotation.x)!==Math.sign(leg1.rotation.x)),
                             legs:commonsAgent.creatureRig().legs };
                }catch(e){return {err:String(e)}}}""", {}) or {}
                check("fidelity_walkrig",
                      bool(rig.get("isGroup") and rig.get("gaitIncreased") and rig.get("changedSign")
                           and rig.get("pairClose") and rig.get("antiPhase") and rig.get("legs") == 4), rig)

                # FIDELITY: GradePass — a camera-locked cinematic grade overlay (vignette + clock-driven
                # tint + grain), no render target. Neutral at noon (tint≈white, strength≈0), warm + harder
                # at dusk, deeper vignette at night. Read live off the GradePass material uniforms.
                gradep = await ev("""async ()=>{try{const A=window.commonsAgent;
                    const m=scene.getObjectByName('GradePass');
                    const isMesh=!!(m&&m.isMesh&&m.material&&m.material.uniforms&&m.material.uniforms.uVignette&&m.material.uniforms.uTint&&m.material.uniforms.uTintStrength&&m.material.uniforms.uGrain&&m.material.uniforms.uTime&&m.material.uniforms.uChroma);
                    const renderOrder=m?m.renderOrder:0; const depthTest=m?m.material.depthTest:true;
                    setTimeOfDay(0.42); const noon=A.grade();
                    setTimeOfDay(0.80); const dusk=A.grade();
                    setTimeOfDay(0.0);  const night=A.grade();
                    setTimeOfDay(0.42);
                    return { isMesh, renderOrder, depthTest, present:noon.present,
                             noonStrength:noon.tintStrength, noonTint:noon.tint, noonVig:noon.vignette,
                             duskStrength:dusk.tintStrength, duskWarm:(dusk.tint[0]>dusk.tint[2]),
                             nightVig:night.vignette };
                }catch(e){return {err:String(e)}}}""", {}) or {}
                check("fidelity_gradepass",
                      bool(gradep.get("isMesh") and gradep.get("present") and gradep.get("renderOrder") == 9999
                           and gradep.get("depthTest") is False
                           and (gradep.get("noonStrength") if gradep.get("noonStrength") is not None else 1) < 0.15
                           and abs((gradep.get("noonTint") or [0, 0, 0])[0] - (gradep.get("noonTint") or [0, 0, 0])[2]) < 0.02
                           and (gradep.get("duskStrength") or 0) > (gradep.get("noonStrength") or 0)
                           and gradep.get("duskWarm")
                           and (gradep.get("nightVig") or 0) > (gradep.get("noonVig") or 0)), gradep)

                # FIDELITY: volumetric god-shafts — an additive open cone hanging from every lamp (PointLight
                # at 2..8m, intensity>=1), bright at the apex and fading to the floor, glowing only after dark.
                # No new lights, no render target — pure additive geometry parented under a 'LightCones' group.
                cones = await ev("""async ()=>{try{const A=window.commonsAgent;
                    const g=scene.getObjectByName('LightCones');
                    const lc=A.lightCones();
                    setTimeOfDay(0.0); const night=A.lightCones().nightGlow;
                    setTimeOfDay(0.5); const noon=A.lightCones().nightGlow;
                    setTimeOfDay(0.42);
                    return { present:lc.present, cones:lc.cones, additive:lc.additive, noDW:lc.noDepthWrite,
                             group:!!(g&&g.type==='Group'), matches:(g&&g.children.length===lc.cones),
                             glowsAtNight:(night>noon) };
                }catch(e){return {err:String(e)}}}""", {}) or {}
                check("fidelity_lightcones",
                      bool(cones.get("present") and (cones.get("cones") or 0) >= 8 and cones.get("additive")
                           and cones.get("noDW") and cones.get("group") and cones.get("matches")
                           and cones.get("glowsAtNight")), cones)

                # FIDELITY: wind-swayed flora — no new geometry/instances/draws; each flora material is patched
                # via onBeforeCompile to sway its tops on a shared wind clock (grass most, trees least). The
                # clock advances every frame; sway phase is deterministic from each instance's world position.
                wind = await ev("""async ()=>{try{const A=window.commonsAgent;
                    const g=scene.getObjectByName('flora-grass');
                    const w1=A.wind(); const w2=A.wind();
                    return { present:w1.present, kinds:w1.kinds, ampGrass:w1.ampGrass, ampTrees:w1.ampTrees,
                             advances:(w2.t1>w1.t1),
                             injected:!!(g && g.material && g.material.userData && g.material.userData.windInjected===true) };
                }catch(e){return {err:String(e)}}}""", {}) or {}
                check("fidelity_wind",
                      bool(wind.get("present") and wind.get("kinds") == 3
                           and (wind.get("ampGrass") or 0) > (wind.get("ampTrees") or 0)
                           and wind.get("advances") and wind.get("injected")), wind)

                # FIDELITY: ground mist — ONE flat low-fog sheet (PlaneGeometry, y≈3) that follows the
                # player and pools at dawn/dusk (haze*0.5) and burns off by noon. Transparent, no depth
                # write. The noise field drifts each frame (uTime advances in animate()).
                mist = await ev("""async ()=>{try{const A=window.commonsAgent;
                    const m=scene.getObjectByName('GroundMist');
                    const isMesh=!!(m&&m.isMesh&&m.material.depthWrite===false&&m.material.transparent===true);
                    setTimeOfDay(0.22); const dawn=A.mist().strength;
                    setTimeOfDay(0.5);  const noon=A.mist().strength;
                    setTimeOfDay(0.42);
                    const t1=A.mist().driftT;
                    return { isMesh, dawn, noon, t1 };
                }catch(e){return {err:String(e)}}}""", {}) or {}
                await page.wait_for_timeout(180)   # the animate() loop advances uTime
                mist_t2 = await ev("()=>{try{return window.commonsAgent.mist().driftT}catch(e){return -1}}", -1)
                await ev("()=>{try{setTimeOfDay(0.42)}catch(e){}return 1}")
                check("fidelity_mist",
                      bool(mist.get("isMesh")
                           and (mist.get("dawn") or 0) > (mist.get("noon") if mist.get("noon") is not None else 1)
                           and (mist.get("dawn") or 0) > 0.05
                           and (mist.get("noon") if mist.get("noon") is not None else 1) < 0.05
                           and mist_t2 is not None and mist_t2 > (mist.get("t1") or 0)),
                      {**mist, "t2": mist_t2})

                # FIDELITY: bioluminescent fireflies — ONE additive THREE.Points swarm of warm motes that
                # wander a disc and pulse, glowing only after dark (same night-ness formula as the stars),
                # invisible by day. Deterministic (seeded mulberry32).
                ff = await ev("""async ()=>{try{const A=window.commonsAgent;
                    const f=scene.getObjectByName('Fireflies');
                    const isPoints=(f&&f.isPoints===true);
                    const base=A.fireflies();
                    setTimeOfDay(0.5); const noon=A.fireflies().glow;
                    setTimeOfDay(0.0); const night=A.fireflies().glow;
                    setTimeOfDay(0.42);
                    return { isPoints, count:base.count, additive:base.additive, color:base.color,
                             noonOff:(noon<0.05), nightOn:(night>0.9) };
                }catch(e){return {err:String(e)}}}""", {}) or {}
                check("fidelity_fireflies",
                      bool(ff.get("isPoints") and (ff.get("count") or 0) >= 200 and ff.get("additive")
                           and str(ff.get("color", "")).lstrip("#") == "ffd27a"
                           and ff.get("noonOff") and ff.get("nightOn")), ff)

                # FIDELITY: instanced grass-tuft meadow — ONE InstancedMesh of crossed-plane blades carpeting
                # the ground (>=2000 instances), plaza + paths kept clear, conformed to groundHeight(), and
                # deterministically seeded (placed count identical across a reload).
                meadow = await ev("""async ()=>{try{const A=window.commonsAgent;
                    const m=scene.getObjectByName('grass-field');
                    const isInst=(m&&m.isInstancedMesh===true);
                    const cap=(m?m.count:0);
                    const gf=A.grassField();
                    return { isInst, cap, count:gf.count, plazaClear:gf.plazaClear, onSurface:gf.onSurface };
                }catch(e){return {err:String(e)}}}""", {}) or {}
                # reload once and re-read the placed count — the seed must reproduce it exactly.
                count2 = None
                try:
                    await page.reload(wait_until="domcontentloaded", timeout=30000)
                    await page.wait_for_timeout(4000)
                    count2 = await ev("()=>{try{return window.commonsAgent.grassField().count}catch(e){return -1}}", -1)
                except Exception:
                    count2 = -1
                check("fidelity_grassmeadow",
                      bool(meadow.get("isInst") and (meadow.get("cap") or 0) >= 2000
                           and meadow.get("plazaClear") is True and meadow.get("onSurface") is True
                           and count2 is not None and count2 == meadow.get("count")),
                      {**meadow, "count2": count2})

                # FIDELITY: STORM FRONT — an OPTIONAL weather system (rain + lightning + sky-flash) on a
                # camera-following 'StormSystem' group, DEFAULT OFF so the resting scene is unchanged. Driven
                # deterministically via stormStep(dt) so the test never polls: default off → setStorm(1) ramps
                # the rain to ~1 (4000 GPU drops) → strike() forces a bolt (flash≈1) that DECAYS → setStorm(0)
                # ramps the rain back toward 0.
                storm = await ev("""async ()=>{try{const A=window.commonsAgent;
                    const sys=scene.getObjectByName('StormSystem');
                    const col=scene.getObjectByName('RainColumn');
                    const d0=A.storm();
                    A.setStorm(1); const wet=A.stormStep(0.5);
                    const f1=A.strike();
                    const after=A.stormStep(0.3);    // flash should decay below 1
                    A.setStorm(0); const dry=A.stormStep(0.5);
                    return { hasSys:!!(sys&&sys.type==='Group'), hasRain:!!(col&&col.isPoints===true),
                             defaultOff:(d0.active===false && d0.rain===0),
                             rainHi:(wet.rain>0.9), parts:(wet.rainParticles===4000),
                             wetFlashRange:(wet.flash>=0 && wet.flash<=1),
                             strikeFlash:(f1.flash>0.9), decayed:(after.flash<1),
                             dryRamp:(dry.rain<wet.rain) };
                }catch(e){return {err:String(e)}}}""", {}) or {}
                # leave the scene as it began (storm off) so later tests see a calm world.
                await ev("()=>{try{window.commonsAgent.setStorm(0);window.commonsAgent.stormStep(2);}catch(e){}return 1}")
                check("fidelity_storm",
                      bool(storm.get("hasSys") and storm.get("hasRain") and storm.get("defaultOff")
                           and storm.get("rainHi") and storm.get("parts") and storm.get("wetFlashRange")
                           and storm.get("strikeFlash") and storm.get("decayed") and storm.get("dryRamp")),
                      storm)

                # FIDELITY: LIVING GAZE — resident heads + the creature's head/eyes turn to watch the player
                # when they walk close, easing back to rest when they leave (zero new geometry). Driven via
                # gazeStep(dt) so the test is deterministic: far → not locked, yaw≈0; teleport the camera right
                # next to the creature + step → locked, yaw grows toward the bearing; walk away + step → unlocks,
                # yaw eases back toward 0; tracked === residents + 1 (the creature).
                gaze = await ev("""async ()=>{try{const A=window.commonsAgent;
                    A.spawnCreature({explore:0.7,exploit:0.5,cooperate:0.6,aggress:0.2});
                    const cp = CREATURE.group.position;
                    // FAR: park the camera well away, settle the head to rest.
                    A.teleport(cp.x+200, 1.6, cp.z+200);
                    for (let i=0;i<40;i++) A.gazeStep(0.1);
                    const far = A.gaze();
                    // NEAR: stand a couple units to the +z side of the creature.
                    A.teleport(cp.x, 1.6, cp.z+3);
                    for (let i=0;i<40;i++) A.gazeStep(0.1);
                    const near = A.gaze();
                    // AWAY again: yaw should ease back toward 0 and unlock.
                    A.teleport(cp.x+200, 1.6, cp.z+200);
                    for (let i=0;i<40;i++) A.gazeStep(0.1);
                    const away = A.gaze();
                    const residents = (A.residents()||[]).length;
                    return { farLocked: far.creature.locked, farYaw: Math.abs(far.creature.yaw),
                             nearLocked: near.creature.locked, nearYaw: Math.abs(near.creature.yaw),
                             awayLocked: away.creature.locked, awayYaw: Math.abs(away.creature.yaw),
                             tracked: near.tracked, residents };
                }catch(e){return {err:String(e)}}}""", {}) or {}
                check("fidelity_gaze",
                      bool(gaze.get("farLocked") is False and (gaze.get("farYaw") if gaze.get("farYaw") is not None else 1) < 0.05
                           and gaze.get("nearLocked") is True and (gaze.get("nearYaw") or 0) > 0.2
                           and gaze.get("awayLocked") is False and (gaze.get("awayYaw") if gaze.get("awayYaw") is not None else 1) < 0.1
                           and gaze.get("tracked") == (gaze.get("residents") or 0) + 1),
                      gaze)

                # FIDELITY: ROCK OUTCROPS — ONE InstancedMesh 'RockOutcrops' of faceted boulders built once at
                # boot, welded into STEEP terrain (inverted slope gate) and SUNK below groundHeight() so they
                # read as exposed bedrock, keeping the plaza + dirt paths clear. The probe decomposes the live
                # instanceMatrices: every sampled instance sits below the ground sampler, none inside the plaza
                # (hypot<28), none on a path (pathNear<0.12).
                rocks = await ev("""async ()=>{try{const A=window.commonsAgent;
                    const m=scene.getObjectByName('RockOutcrops');
                    const isInst=(m&&m.isInstancedMesh===true);
                    const rk=A.rocks();
                    return { isInst, count:rk.count, sunken:rk.sunken, offPlaza:rk.offPlaza,
                             onPaths:rk.onPaths, draws:rk.draws };
                }catch(e){return {err:String(e)}}}""", {}) or {}
                check("fidelity_rocks",
                      bool(rocks.get("isInst") and (rocks.get("count") or 0) > 40
                           and rocks.get("sunken") is True and rocks.get("offPlaza") is True
                           and rocks.get("onPaths") == 0),
                      rocks)

                # FIDELITY: CARVED REFLECTIVE LAKE — lakeDepth() carves a smoothstep basin into the SHARED
                # groundHeight() sampler well outside the plaza + clear of every path, so the terrain mesh
                # dips into a bowl while the plaza stays dead flat; ONE 'CommonsLake' shader disc then mirrors
                # the LIVE sky off its rippling surface with NO render target (it copies sky.uniforms each
                # frame). Probe: basin carved, plaza flat, reflectsHorizon tracks the live sky horizon at noon,
                # shifts at dusk, and the ripple phase advances via the deterministic lakeStep(dt) hook.
                lake = await ev("""async ()=>{try{const A=window.commonsAgent;
                    const exists=!!scene.getObjectByName('CommonsLake');
                    setTimeOfDay(0.5); A.lakeStep(0); const noon=A.lake(); const skyNoon=A.atmosphere().horizon;
                    setTimeOfDay(0.78); A.lakeStep(0); const dusk=A.lake();
                    const p1=A.lakeStep(0.5).ripplePhase, p2=A.lakeStep(0.5).ripplePhase;
                    setTimeOfDay(0.42);
                    return { exists, name:noon.name, basinCarved:noon.basinCarved, plazaFlat:noon.plazaFlat,
                             noonRefl:noon.reflectsHorizon, skyNoon, duskRefl:dusk.reflectsHorizon,
                             advances:(p2>p1) };
                }catch(e){return {err:String(e)}}}""", {}) or {}
                check("fidelity_lake",
                      bool(lake.get("exists") and lake.get("name") == "CommonsLake"
                           and lake.get("basinCarved") is True and lake.get("plazaFlat") is True
                           and lake.get("noonRefl") == lake.get("skyNoon")
                           and lake.get("duskRefl") != lake.get("noonRefl")
                           and lake.get("advances")),
                      lake)

                # FIDELITY: CONTACT SHADOWS — ONE InstancedMesh 'ContactShadows' of soft radial AO discs that
                # ground every standing thing (portals, homes, room/area anchors, lanterns, the creature) by
                # hugging the terrain at groundHeight()+0.02. The blobs tighten + darken at high sun and spread
                # + soften toward dusk, fading out at night — driven off the SAME low-sun factor as god-rays.
                # Probe: instanced, count>0, every instance grounded, opacity>0 at noon, meanScale grows by dusk.
                cs = await ev("""async ()=>{try{const A=window.commonsAgent;
                    const m=scene.getObjectByName('ContactShadows');
                    const isInst=(m&&m.isInstancedMesh===true);
                    setTimeOfDay(0.5); const noon=A.contactShadows();
                    setTimeOfDay(0.78); const dusk=A.contactShadows();
                    setTimeOfDay(0.42);
                    return { isInst, name:noon.name, count:noon.count, grounded:noon.grounded,
                             noonOpacity:noon.opacity, noonScale:noon.meanScale, duskScale:dusk.meanScale };
                }catch(e){return {err:String(e)}}}""", {}) or {}
                check("fidelity_contactshadows",
                      bool(cs.get("isInst") and cs.get("name") == "ContactShadows"
                           and (cs.get("count") or 0) > 0 and cs.get("grounded") is True
                           and (cs.get("noonOpacity") or 0) > 0
                           and (cs.get("duskScale") or 0) > (cs.get("noonScale") or 0)),
                      cs)

                # FIDELITY: AURORA CURTAINS — ONE inward-facing curved band high on the northern dome with three
                # undulating curtain bands, additive-blended and gated to NIGHT only (full at midnight, ~0 by
                # day). Probe: exists + AdditiveBlending; nightGlow>0.6 at midnight (t=0.0), <0.02 at noon (0.5).
                aur = await ev("""async ()=>{try{const A=window.commonsAgent;
                    const exists=!!scene.getObjectByName('AuroraCurtains');
                    setTimeOfDay(0.0); const night=A.aurora();
                    setTimeOfDay(0.5); const day=A.aurora();
                    setTimeOfDay(0.42);
                    return { exists, name:night.name, bands:night.bands, additive:night.additive,
                             nightGlow:night.nightGlow, dayGlow:day.nightGlow };
                }catch(e){return {err:String(e)}}}""", {}) or {}
                check("fidelity_aurora",
                      bool(aur.get("exists") and aur.get("name") == "AuroraCurtains"
                           and aur.get("bands") == 3 and aur.get("additive") is True
                           and (aur.get("nightGlow") or 0) > 0.6
                           and (aur.get("dayGlow") if aur.get("dayGlow") is not None else 1) < 0.02),
                      aur)

                # FIDELITY: WET SHORELINE & FOAM BAND — ONE flat ring welded to the lake's carved shore so the
                # water reads as meeting the land, not floating above it. Every ring vertex is snapped to
                # groundHeight()+0.03; a wet-sand/foam shader darkens toward the waterline + paints a thin
                # animated foam lap-line. Probe: present 'LakeShoreBand'; innerR < LAKE.r(22) < outerR; every
                # ring vertex hugs the terrain; shorelineStep(0.5) advances foamPhase ~0.5; lake() still callable.
                shore = await ev("""async ()=>{try{const A=window.commonsAgent;
                    const m=scene.getObjectByName('LakeShoreBand');
                    const exists=!!(m&&m.isMesh);
                    const s=A.shoreline();
                    const p1=A.shorelineStep(0.5).foamPhase, p2=A.shorelineStep(0.5).foamPhase;
                    const lakeOk=(typeof A.lake==='function' && A.lake().name==='CommonsLake');
                    return { exists, name:s.name, innerR:s.innerR, outerR:s.outerR, hugsTerrain:s.hugsTerrain,
                             advances:(p2-p1), lakeOk };
                }catch(e){return {err:String(e)}}}""", {}) or {}
                check("fidelity_shoreline",
                      bool(shore.get("exists") and shore.get("name") == "LakeShoreBand"
                           and (shore.get("innerR") if shore.get("innerR") is not None else 99) < 22
                           and (shore.get("outerR") or 0) > 22 and shore.get("hugsTerrain") is True
                           and abs((shore.get("advances") or 0) - 0.5) < 0.05 and shore.get("lakeOk")),
                      shore)

                # FIDELITY: RESIDENT WALK CYCLE — every resident NPC carries 4 limb-pivot Groups (2 legs, 2 arms)
                # that swing while it walks (a stationary resident settles; a hurrying one pumps). Legs run 0/π;
                # arms LEAD the OPPOSITE leg (counter-swing). Probe: limbsEach===4; named children resolve as
                # Groups (resident-limb-0-lleg / -larm). Force npcs[0] to walk far, tick wanderNPCs ~14x and
                # collect sign(lleg.rotation.x) -> sign changes (swing); arm anti-phase to leg; park it (target
                # = current pos) and the swing amplitude collapses toward 0. AND shipped fidelity_walkrig stays green.
                rrig = await ev("""async ()=>{try{const A=window.commonsAgent;
                    const n=npcs[0];
                    const base=A.residentRig();
                    const lleg=n.group.getObjectByName('resident-limb-0-lleg');
                    const larm=n.group.getObjectByName('resident-limb-0-larm');
                    const isGroups=!!(lleg&&lleg.type==='Group'&&larm&&larm.type==='Group');
                    // WALK: send the resident far away and step the wander loop, sampling the leg swing sign.
                    n.target.set(n.group.position.x+300,0,n.group.position.z+300);
                    let signs=[], antiSeen=false, maxAmp=0;
                    for(let i=0;i<14;i++){ wanderNPCs(0.05);
                      signs.push(Math.sign(lleg.rotation.x));
                      maxAmp=Math.max(maxAmp, Math.abs(lleg.rotation.x));
                      if(Math.sign(larm.rotation.x)!==Math.sign(lleg.rotation.x) && Math.sign(lleg.rotation.x)!==0) antiSeen=true; }
                    const changedSign=signs.some((s,i)=>i>0 && s!==0 && signs[i-1]!==0 && s!==signs[i-1]);
                    // STATIONARY: target = current pos -> speed01≈0 -> swing amplitude collapses.
                    n.target.set(n.group.position.x, 0, n.group.position.z);
                    let stillAmp=0;
                    for(let i=0;i<14;i++){ wanderNPCs(0.05); stillAmp=Math.max(stillAmp, Math.abs(lleg.rotation.x)); }
                    return { limbsEach:base.limbsEach, isGroups, changedSign, antiSeen, walkAmp:maxAmp, stillAmp };
                }catch(e){return {err:String(e)}}}""", {}) or {}
                # NOTE: the shipped creature walk rig (fidelity_walkrig, above) must stay green — Feature 2 leaves
                # creatureTick/creatureRig byte-for-byte untouched, so that existing test is the regression guard.
                check("fidelity_residentrig",
                      bool(rrig.get("limbsEach") == 4 and rrig.get("isGroups") and rrig.get("changedSign")
                           and rrig.get("antiSeen")
                           and (rrig.get("walkAmp") or 0) > 0.2
                           and (rrig.get("stillAmp") if rrig.get("stillAmp") is not None else 1) < 0.12),
                      rrig)

                # FIDELITY: THE HEARTWOOD — a hero GreatTree landmark seated NORTH of the lake (lake cz=-95 r=22,
                # so the tree at z=-150 has a clear margin: pos.z < -117). Gnarled tapered trunk + seeded forked
                # limbs + flattened icosa canopy + an inner emissive heartwood whose glow is night-gated via the
                # SAME nightness scalar as the stars/aurora (beacons at night, dark at noon, reflecting in the lake).
                # NOTE: with trunk=22 + canopy the real bounding reach is ~31 — 40 is geometrically unreachable
                # with these dims, so per the spec we assert the REAL height >=18 (deviation: target was >=40).
                gtree = await ev("""async ()=>{try{const A=window.commonsAgent;
                    const exists=!!scene.getObjectByName('GreatTree');
                    const t=A.greatTree();
                    A.setTimeOfDay(0.0); const night=A.greatTree().glow;
                    A.setTimeOfDay(0.5); const noon=A.greatTree().glow;
                    A.setTimeOfDay(0.42);
                    // shipped probes must remain callable + green-shaped.
                    const lakeOk=(A.lake().name==='CommonsLake');
                    A.setTimeOfDay(0.0); const aurOn=A.aurora().nightGlow, ffOn=A.fireflies().glow;
                    A.setTimeOfDay(0.42);
                    return { exists, height:t.height, limbs:t.limbs, posz:t.pos.z, night, noon, lakeOk, aurOn, ffOn };
                }catch(e){return {err:String(e)}}}""", {}) or {}
                check("fidelity_greattree",
                      bool(gtree.get("exists")
                           and (gtree.get("height") or 0) >= 18   # real reach (~31); target >=40 unreachable with these dims
                           and (gtree.get("limbs") or 0) >= 5
                           and (gtree.get("posz") if gtree.get("posz") is not None else 0) < -117
                           and (gtree.get("night") or 0) > (gtree.get("noon") if gtree.get("noon") is not None else 1)
                           and gtree.get("lakeOk")
                           and (gtree.get("aurOn") or 0) > 0.6 and (gtree.get("ffOn") or 0) > 0.9),
                      gtree)

                # FIDELITY: ANAMORPHIC SUN FLARE — an occlusion-gated additive lens flare pinned to the camera
                # like GradePass (renderOrder 9998, just under GradePass's 9999). ONE 'SunFlare' Group of
                # additive sprites: a core + streak + ~8 ghosts strung along the sun→centre axis. Each frame
                # sunFlareStep() projects the LIVE sun to NDC, maps it onto the SAME near-plane quad gradeResize
                # uses, and gates master opacity to 0 below the horizon / when not facing the sun / when occluded.
                # Probe: exists + ghosts>0; daytime facing the sun → facing>0.8 && intensity>0; midnight → 0;
                # turn 180° away from the sun → facing≈0 && intensity===0. Driven via the deterministic
                # sunFlareStep() hook so it needs no rendering.
                flare = await ev("""async ()=>{try{const A=window.commonsAgent;
                    const g=scene.getObjectByName('SunFlare');
                    const exists=!!(g&&g.type==='Group'); const renderOrder=g?g.renderOrder:0;
                    const base=A.sunFlare();
                    // DAYTIME, facing the sun: point the camera straight at the live sun direction.
                    setTimeOfDay(0.42);
                    const sd=sky.material.uniforms.sunDir.value;
                    const o=camera; o.position.set(0,1.6,0);
                    o.lookAt(o.position.x+sd.x, o.position.y+sd.y, o.position.z+sd.z); o.updateMatrixWorld(true);
                    const facingSun=A.sunFlareStep(0);
                    // MIDNIGHT: sun below the horizon -> flare must be fully dark regardless of where we look.
                    setTimeOfDay(0.0); const nightSF=A.sunFlareStep(0);
                    // BACK to day, then turn 180° AWAY from the sun -> facing≈0, intensity 0.
                    setTimeOfDay(0.42);
                    o.lookAt(o.position.x-sd.x, o.position.y-sd.y, o.position.z-sd.z); o.updateMatrixWorld(true);
                    const awaySF=A.sunFlareStep(0);
                    setTimeOfDay(0.42);
                    return { exists, group:base.group, renderOrder, ghosts:base.ghosts,
                             facing:facingSun.facing, intensity:facingSun.intensity,
                             nightInt:nightSF.intensity, awayFacing:awaySF.facing, awayInt:awaySF.intensity };
                }catch(e){return {err:String(e)}}}""", {}) or {}
                check("fidelity_sunflare",
                      bool(flare.get("exists") and flare.get("group") == "SunFlare"
                           and flare.get("renderOrder") == 9998
                           and (flare.get("ghosts") or 0) > 0
                           and (flare.get("facing") or 0) > 0.8 and (flare.get("intensity") or 0) > 0
                           and flare.get("nightInt") == 0
                           and (flare.get("awayFacing") if flare.get("awayFacing") is not None else 1) < 0.05
                           and flare.get("awayInt") == 0),
                      flare)

                # FIDELITY: LAKE CAUSTICS — sunlit dancing light on the lake floor. ONE 'LakeCaustics' disc laid
                # flat just above the carved basin floor (y≈-3.34), centred on the lake, additive-blended. The
                # caustic light is multiplied by uSunColor*uDayGate, both COPIED every frame from the CommonsLake
                # water shader (lakeStep refreshes them) so the floor light locks to the mirror water above —
                # bright by day, gone at night. uTime advances via the deterministic causticsStep(dt) hook.
                # Probe: exists, floorY≈-3.34, within LAKE.r of the lake centre, dayGate>0.5 at noon and ≈0 at
                # midnight, phase strictly increases on positive dt, material.blending===AdditiveBlending.
                caus = await ev("""async ()=>{try{const A=window.commonsAgent;
                    const m=scene.getObjectByName('LakeCaustics');
                    const exists=!!(m&&m.isMesh);
                    const additive=!!(m&&m.material.blending===THREE.AdditiveBlending);
                    const wp=new THREE.Vector3(); if(m) m.getWorldPosition(wp);
                    const dist=Math.hypot(wp.x-LAKE.cx, wp.z-LAKE.cz);
                    setTimeOfDay(0.5); A.lakeStep(0); const noon=A.causticsStep(0);
                    setTimeOfDay(0.0); A.lakeStep(0); const night=A.causticsStep(0);
                    setTimeOfDay(0.42); A.lakeStep(0);
                    const p1=A.causticsStep(0.5).phase, p2=A.causticsStep(0.5).phase;
                    const probe=A.caustics();
                    return { exists, additive, floorY:probe.floorY, dist, withinLakeR:(dist<LAKE.r),
                             noonGate:noon.dayGate, nightGate:night.dayGate, advances:(p2>p1),
                             name:probe.name, radius:probe.radius };
                }catch(e){return {err:String(e)}}}""", {}) or {}
                check("fidelity_caustics",
                      bool(caus.get("exists") and caus.get("name") == "LakeCaustics"
                           and abs((caus.get("floorY") if caus.get("floorY") is not None else 0) - (-3.34)) < 0.05
                           and caus.get("withinLakeR") is True
                           and (caus.get("noonGate") or 0) > 0.5
                           and (caus.get("nightGate") if caus.get("nightGate") is not None else 1) < 0.05
                           and caus.get("advances") and caus.get("additive") is True),
                      caus)

                # FIDELITY: THE LANTERN SPIRE — a stone watchtower landmark south of spawn (z=+150), opposite
                # the Heartwood (z=-150), built once at boot: a course-banded tapered stone shaft, crenellated
                # crown, cardinal window slits, and a brazier beacon (emissive + PointLight) at the top that
                # KINDLES after dark — night-gated by the SAME nightness scalar as the stars/aurora, so it
                # reflects in CommonsLake via the existing mirror. Registered as a navigable place via the
                # EXISTING list()/travelTo mechanism (additive — never disturbs the shipped areas). Probe:
                # present, height in [34,40]; noon→glow<0.05; midnight→glow>1.5; world z≈150; 'The Lantern Spire'
                # appears in commonsAgent.list(). spireStep() night-gates the beacon the instant the clock moves.
                spire = await ev("""async ()=>{try{const A=window.commonsAgent;
                    const m=scene.getObjectByName('LanternSpire');
                    const exists=!!m; const wp=new THREE.Vector3(); if(m) m.getWorldPosition(wp);
                    const base=A.spire();
                    setTimeOfDay(0.5); A.timeOfDay(); const noon=A.spire().glow;
                    setTimeOfDay(0.0); const night=A.spire().glow;
                    setTimeOfDay(0.42);
                    const names=(A.list()||[]).map(p=>(p.name||p.slug||p).toString().toLowerCase());
                    const listed=names.some(n=>n.indexOf('lantern spire')>=0 || n.indexOf('lantern-spire')>=0);
                    return { present:base.present, height:base.height, mirrorsLake:base.mirrorsLake,
                             worldZ:+wp.z.toFixed(1), noon, night, listed,
                             names: names };
                }catch(e){return {err:String(e)}}}""", {}) or {}
                check("fidelity_spire",
                      bool(spire.get("present")
                           and 34 <= (spire.get("height") or 0) <= 40
                           and spire.get("mirrorsLake") is True
                           and abs((spire.get("worldZ") if spire.get("worldZ") is not None else 0) - 150) < 2
                           and (spire.get("noon") if spire.get("noon") is not None else 1) < 0.05
                           and (spire.get("night") or 0) > 1.5
                           and spire.get("listed")),
                      spire)

                # FIDELITY: LIVE COMMONS STREAM — the 3D world now joins the SAME real-time signed
                # chat the front door (index.html, rapp-commons-protocol/2.0) runs, sharing ONE
                # conversation + ONE identity across pages. The RC module adopts the front-door event
                # protocol VERBATIM (rapp-commons-event/1.0: from = the rapp/1 §6.2 keyed rappid
                # rappid:@being/<tail[:12]>:<tail>, tail=sha256hex("rapp/1:rappid\n"+SPKI_DER); events
                # from legacy rappid:v3: ids verify read-forever via the old raw-key binding;
                # pub=raw-key b64u, alg ecdsa-p256, body {text}, stable canonicalisation, b64u sig) and
                # mints/loads under the SAME localStorage key ('rapp-commons-id'). Network is gated on
                # world-entry (.live), so this asserts protocol correctness WITHOUT touching the public
                # stream: sign a front-door-valid event, verify it round-trips, confirm a TAMPERED copy
                # is rejected, and that the signed identity is the persisted unified one.
                lc = await ev("""async ()=>{try{const A=window.commonsAgent;
                    const ev0 = await A.liveChatSign('acceptance livechat hello');   // mints/loads the unified id
                    const lc = A.liveChat();
                    const ridOk = typeof lc.rappid==='string' && /^rappid:@being\\/[0-9a-f]{12}:[0-9a-f]{64}$/.test(lc.rappid);
                    const stored = JSON.parse(localStorage.getItem('rapp-commons-id')||'null');
                    const sameId = !!(stored && stored.rappid===lc.rappid);          // SAME key+format as front door
                    const shapeOk = !!(ev0 && ev0.schema==='rapp-commons-event/1.0' && ev0.alg==='ecdsa-p256'
                        && typeof ev0.pub==='string' && typeof ev0.sig==='string'
                        && ev0.body && typeof ev0.body.text==='string'
                        && typeof ev0.from==='string' && /^rappid:@being\\/[0-9a-f]{12}:[0-9a-f]{64}$/.test(ev0.from));
                    const verifyGood = await A.liveChatVerify(ev0);
                    const tampered = JSON.parse(JSON.stringify(ev0)); tampered.body.text='forged';
                    const verifyTamper = await A.liveChatVerify(tampered);
                    return { present:lc.present, protocol:lc.protocol, unified:lc.unifiedWithFrontDoor,
                             identityPersisted:lc.identityPersisted, room:lc.room, live:lc.live,
                             ridOk, sameId, shapeOk, verifyGood, verifyTamper,
                             fromMatchesProbe: ev0.from===lc.rappid };
                }catch(e){return {err:String(e)}}}""", {}) or {}
                check("fidelity_livechat",
                      bool(lc.get("present")
                           and lc.get("protocol") == "rapp-commons-event/1.0"
                           and lc.get("unified") is True
                           and lc.get("identityPersisted") is True
                           and lc.get("room") == "commons"
                           and lc.get("ridOk") and lc.get("sameId") and lc.get("shapeOk")
                           and lc.get("verifyGood") is True
                           and lc.get("verifyTamper") is False
                           and lc.get("fromMatchesProbe") is True),
                      lc)

                # FIDELITY: THE LAKESPAN — an arched stone footbridge humping over CommonsLake on the N/S chord,
                # built once at boot: a deck lofted from ~24 box segments along y=apex*sin(PI*t), railing posts +
                # top-rails, tapered abutments seated via groundHeight(), and 2 emissive braziers + 2 PointLights
                # that kindle after dark (night-gated by the SAME nightness scalar as the spire). Registered as a
                # navigable place via the EXISTING list()/travelTo mechanism (slug 'lakespan'). Probe: present,
                # spanLength, apexY above the water surface, lanterns===2, glow night-gated. The bounding-box
                # z-extent must cover the lake (>= 2*LAKE.r); 'lakespan' joins list() with NO venue regression.
                lspan = await ev("""async ()=>{try{const A=window.commonsAgent;
                    const m=scene.getObjectByName('Lakespan');
                    const exists=!!m;
                    const bb=m?new THREE.Box3().setFromObject(m):null;
                    const zext=bb?(bb.max.z-bb.min.z):0;
                    const waterY=LAKE.floor+2.9;
                    const before=(A.list()||[]).map(p=>(p.slug||p.name||p).toString().toLowerCase());
                    setTimeOfDay(0.0); const nightGlow=A.lakespan().glow;
                    setTimeOfDay(0.5); const dayGlow=A.lakespan().glow;
                    setTimeOfDay(0.42);
                    const probe=A.lakespan();
                    const names=(A.list()||[]).map(p=>(p.slug||p.name||p).toString().toLowerCase());
                    const hasSlug=names.some(n=>n.indexOf('lakespan')>=0);
                    return { exists, name:probe.name, spanLength:probe.spanLength, apexY:probe.apexY,
                             aboveWater:(probe.apexY>waterY), lanterns:probe.lanterns,
                             zext:+zext.toFixed(2), zEnough:(zext>=2*LAKE.r),
                             nightGlow, dayGlow, hasSlug, listLen:names.length, beforeLen:before.length };
                }catch(e){return {err:String(e)}}}""", {}) or {}
                check("fidelity_lakespan",
                      bool(lspan.get("exists") and lspan.get("name") == "Lakespan"
                           and lspan.get("zEnough") is True
                           and lspan.get("aboveWater") is True
                           and lspan.get("lanterns") == 2
                           and (lspan.get("nightGlow") or 0) > 1.5
                           and (lspan.get("dayGlow") if lspan.get("dayGlow") is not None else 1) < 0.1
                           and lspan.get("hasSlug") is True),
                      lspan)

                # FIDELITY: KOI POND — a small rigged school of koi swimming just beneath the CommonsLake mirror.
                # Each koi is a kinematic chain (head + 2 body pivots + a tail fin) whose traveling sine yields a
                # fish S-curve; the school wanders a confined lissajous/circular path (planar radius < LAKE.r-1.5
                # about the lake centre), y just under the water plane, facing velocity. Built once, seeded fresh
                # ('KOIP'), zero per-frame allocation, NEVER touching the lake/ripple uniforms. Probe: present,
                # count===8, waveAmp>0 after stepping (bodies undulating), every koi stays inside the lake and
                # submerged. We drive koiStep over several frames and assert the sampled koi never leaves the lake.
                koi = await ev("""async ()=>{try{const A=window.commonsAgent;
                    const m=scene.getObjectByName('KoiSchool');
                    const exists=!!m;
                    const maxR=LAKE.r;
                    let everInside=true, maxWave=0;
                    for (let f=0; f<30; f++){
                      A.koiStep(0.1);
                      const p=A.koi();
                      if (p.waveAmp>maxWave) maxWave=p.waveAmp;
                      if (!p.inLake) everInside=false;
                      // sample koi #0's planar dist from the lake centre directly off the scene graph.
                      const k0=_koi[0].grp;
                      if (Math.hypot(k0.position.x, k0.position.z) >= maxR) everInside=false;
                    }
                    const probe=A.koi();
                    setTimeOfDay(0.42); A.koiStep(0);
                    return { exists, name:probe.name, count:probe.count, maxWave,
                             inLake:probe.inLake, submerged:probe.submerged };
                }catch(e){return {err:String(e)}}}""", {}) or {}
                check("fidelity_koi",
                      bool(koi.get("exists") and koi.get("name") == "KoiSchool"
                           and koi.get("count") == 8
                           and (koi.get("maxWave") or 0) > 0.001
                           and koi.get("inLake") is True
                           and koi.get("submerged") == koi.get("count")),
                      koi)

                # FIDELITY: THE WHISPERING GROVE — a torii-gated walkable birch garden seated east of the commons
                # (~(95,_,20)), clear of the plaza, off the radiating paths, and a safe distance from the lake /
                # GreatTree / Lantern Spire. ~9 slender birch ring a moss disc; a vermilion torii gate faces the
                # approach; a stacked stone lantern (ishidoro) glows after dark. The birch leaves sway on the
                # SHARED wind clock (WINDFX.mats via injectWind — no new sway layer). Registered as a navigable
                # place via the EXISTING list()/travelTo mechanism (slug 'whispering-grove'). Probe: present,
                # trees===9, hasTorii, offPlaza, glow night-gated; min distance from the other landmarks safe;
                # 'whispering-grove' joins list() reachable via goto, with NO venue regression.
                grove = await ev("""async ()=>{try{const A=window.commonsAgent;
                    const m=scene.getObjectByName('WhisperingGrove');
                    const exists=!!m;
                    const before=(A.list()||[]).map(p=>(p.slug||p.name||p).toString().toLowerCase());
                    const probe=A.grove();
                    const c=probe.centre||{x:0,z:0};
                    const dLake=Math.hypot(c.x-LAKE.cx, c.z-LAKE.cz);
                    const gt=scene.getObjectByName('GreatTree'); const ls=scene.getObjectByName('LanternSpire');
                    const dTree=gt?Math.hypot(c.x-gt.position.x, c.z-gt.position.z):999;
                    const dSpire=ls?Math.hypot(c.x-ls.position.x, c.z-ls.position.z):999;
                    setTimeOfDay(0.0); const nightGlow=A.grove().glow;
                    setTimeOfDay(0.5); const dayGlow=A.grove().glow;
                    setTimeOfDay(0.42);
                    const names=(A.list()||[]).map(p=>(p.slug||p.name||p).toString().toLowerCase());
                    const hasSlug=names.some(n=>n.indexOf('whispering-grove')>=0 || n.indexOf('whispering grove')>=0);
                    const goneto=A.goto('Whispering Grove');
                    const reached=!!(goneto && !goneto.error);
                    return { exists, name:probe.name, trees:probe.trees, hasTorii:probe.hasTorii,
                             offPlaza:probe.offPlaza, nightGlow, dayGlow, hasSlug, reached,
                             minLandmark:+Math.min(dLake,dTree,dSpire).toFixed(1),
                             beforeLen:before.length, listLen:names.length };
                }catch(e){return {err:String(e)}}}""", {}) or {}
                check("fidelity_grove",
                      bool(grove.get("exists") and grove.get("name") == "WhisperingGrove"
                           and grove.get("trees") == 9
                           and grove.get("hasTorii") is True
                           and grove.get("offPlaza") is True
                           and (grove.get("minLandmark") or 0) > 40
                           and (grove.get("nightGlow") or 0) > 1.0
                           and (grove.get("dayGlow") if grove.get("dayGlow") is not None else 1) < 0.1
                           and grove.get("hasSlug") is True
                           and grove.get("reached") is True
                           and grove.get("listLen") >= grove.get("beforeLen")),
                      grove)
            else:
                check("matrix_4d", False, "window.commonsAgent.doubleJump missing")
                check("matrix_frame", False, "")
                check("matrix_merge", False, "")
                check("matrix_double_jump", False, "")

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

            # poker_popout_bridge: pressing E at the table pops open the standalone
            # playable game (games/poker/poker.html) in the in-world surface panel;
            # that separate page postMessages its live hand state + every signed
            # rapp-poker-action/1.0 back, which MIRROR onto the native 3D felt so the
            # room watches WITHOUT joining. Assert: openPokerGame() points the surface
            # iframe at the poker game URL + shows the panel; a simulated 'state'
            # message mirrors board+pot+folded onto pokerState(); a simulated signed
            # 'action' is counted; 'close' hides the panel. (Native engine untouched;
            # the auto-open is gated on a real pointer-locked player, so this path only
            # runs when explicitly invoked — headless enter('poker') leaves no iframe.)
            has_bridge = await ev("()=>typeof window.commonsAgent.openPokerGame==='function'&&typeof window.commonsAgent.pokerBridge==='function'", False)
            if has_bridge:
                br = await ev("""async ()=>{try{const A=window.commonsAgent;
                    const opened = A.openPokerGame();
                    const fr = document.getElementById('surfaceFrame');
                    const surf = document.getElementById('surface');
                    const urlOk = !!(opened&&opened.url&&/games\\/poker\\/poker\\.html$/.test(opened.url));
                    const srcOk = !!(fr&&/games\\/poker\\/poker\\.html(\\?|$)/.test(fr.src||fr.getAttribute('src')||''));
                    const shown = !!(surf&&getComputedStyle(surf).display!=='none');
                    const board=['As','Kd','2c','7h','9s'];
                    window.dispatchEvent(new MessageEvent('message',{origin:location.origin,
                      data:{type:'rapp-poker',kind:'state',state:{handId:'h1',phase:'river',board:board,pot:42,toAct:0,
                        seats:[{seat:1,chips:500,folded:true}]}}}));
                    const ps = A.pokerState();
                    const mirrored = !!(ps && JSON.stringify(ps.community)===JSON.stringify(board) && ps.pot===42);
                    const seat1 = (ps.seats||[]).find(s=>s.seat===1);
                    const foldedMirror = !!(seat1 && seat1.folded===true);
                    const before = A.pokerBridge().actions;
                    window.dispatchEvent(new MessageEvent('message',{origin:location.origin,
                      data:{type:'rapp-poker',kind:'action',action:{schema:'rapp-poker-action/1.0',hand_id:'h1',seq:1,seat:0,
                        from:'rappid:v3:deadbeefdeadbeef',action:'bet',amount:10,ts:'2026-06-22T00:00:00Z',sig:'ab',pub:{}}}})); // legacy v3-form action — read-forever
                    const actionsCounted = A.pokerBridge().actions===before+1;
                    window.dispatchEvent(new MessageEvent('message',{origin:location.origin,data:{type:'rapp-poker',kind:'close'}}));
                    const hidden = getComputedStyle(surf).display==='none';
                    surf.style.display='none'; if(fr){fr.removeAttribute('src');fr.removeAttribute('srcdoc');}
                    return { urlOk, srcOk, shown, mirrored, foldedMirror, actionsCounted, hidden };
                }catch(e){return {err:String(e)}}}""", {}) or {}
                check("poker_popout_bridge",
                      bool(br.get("urlOk") and br.get("srcOk") and br.get("shown")
                           and br.get("mirrored") and br.get("foldedMirror")
                           and br.get("actionsCounted") and br.get("hidden")),
                      br)
            else:
                check("poker_popout_bridge", False, "openPokerGame/pokerBridge missing")

            # house_popout + surface input-freeze: walking to Kody's House and pressing E
            # opens its OWN page (homes/kody/house.html) in the in-world surface panel. The
            # page is a TEMPLATE parameterized by ?rappid, so the SAME file opens any
            # resident's house (Kody is default). Assert: 'kody-house' is a navigable area;
            # openKodyHouse() points the surface iframe at house.html, SHOWS the panel, and
            # FREEZES the world (the #lock enter-overlay is hidden so it can't float over the
            # panel + surfaceOpen()===true); openHouse(<rappid>) injects ?rappid=<rappid>;
            # pressing Escape closes the panel and unfreezes (surfaceOpen()===false).
            has_house = await ev("()=>typeof window.commonsAgent.openKodyHouse==='function'&&typeof window.commonsAgent.openHouse==='function'&&typeof window.commonsAgent.surfaceOpen==='function'", False)
            if has_house:
                hs = await ev("""async ()=>{try{const A=window.commonsAgent;
                    const names=(A.list()||[]).map(p=>(p.slug||p.name||p).toString().toLowerCase());
                    const listed = names.some(n=>n.indexOf('kody-house')>=0 || n.indexOf("kody's house")>=0);
                    const op = A.openKodyHouse();
                    const fr = document.getElementById('surfaceFrame');
                    const surf = document.getElementById('surface');
                    const lock = document.getElementById('lock');
                    const urlOk = !!(op&&op.url&&/homes\\/kody\\/house\\.html/.test(op.url));
                    const srcOk = !!(fr&&/homes\\/kody\\/house\\.html/.test(fr.src||fr.getAttribute('src')||''));
                    const shown = getComputedStyle(surf).display!=='none';
                    const frozen = (A.surfaceOpen()===true) && (getComputedStyle(lock).display==='none');
                    const op2 = A.openHouse('rappid:v3:abc123def456','Ada'); // legacy v3-form id — read-forever, houses still open
                    const injected = !!(op2&&op2.url&&/[?&]rappid=rappid%3Av3%3Aabc123def456/.test(op2.url)&&op2.owner==='Ada');
                    window.dispatchEvent(new KeyboardEvent('keydown',{code:'Escape',bubbles:true}));
                    const closed = (A.surfaceOpen()===false) && (getComputedStyle(surf).display==='none');
                    surf.style.display='none'; if(fr){fr.removeAttribute('src');fr.removeAttribute('srcdoc');} lock.style.display='none';
                    return { listed, urlOk, srcOk, shown, frozen, injected, closed };
                }catch(e){return {err:String(e)}}}""", {}) or {}
                check("house_popout",
                      bool(hs.get("listed") and hs.get("urlOk") and hs.get("srcOk")
                           and hs.get("shown") and hs.get("frozen") and hs.get("injected")
                           and hs.get("closed")),
                      hs)
            else:
                check("house_popout", False, "openKodyHouse/openHouse/surfaceOpen missing")

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

            # bounty_board: the commons has a LIVING JOB MARKET. A board venue lets
            # residents POST, CLAIM, and COMPLETE signed tasks on the EXISTING
            # append-only signed stream (rapp-commons-bounty/1.0, signed via the
            # existing signAs path — each action by its actor's OWN rappid). The
            # wandering residents seed + work the board on a slow heartbeat, so a
            # visitor at breakfast finds it alive. Over a short poll assert:
            #   • commonsAgent.bounties() returns >=1 bounty whose `from` is a
            #     rappid id, AND that bounty's signed record (on the append-only
            #     persist stream / localStorage) carries a real signature, AND
            #   • at least one bounty TRANSITIONS open->claimed (or ->done) where
            #     the claimer/completer's rappid DIFFERS from the poster's `from`
            #     (a resident worked SOMEONE ELSE's bounty, signed as itself).
            has_bounty = await ev("()=>typeof window.commonsAgent.bounties==='function'", False)
            if has_bounty:
                # entering the board focuses the camera + builds the 3D cork (additive).
                await ev("()=>{try{window.commonsAgent.enter('board');}catch(e){}return 1}")
                bsnap = lambda: ev(
                    "()=>{try{return (window.commonsAgent.bounties()||[]).map(b=>({"
                    "id:b.id,from:b.from,status:b.status,claimedBy:b.claimedBy||null}))}"
                    "catch(e){return[]}}", [])
                # a signed bounty record (post|claim|done) carrying a rappid `from`
                # + a real signature must exist on the SAME append-only signed stream
                # (read straight off the localStorage persist log — not a new surface).
                signed_on_stream = lambda: ev(
                    "()=>{try{const raw=localStorage.getItem('rapp-commons:persist:log/1');"
                    "if(!raw)return false;const log=JSON.parse(raw);"
                    "return log.some(r=>r.schema==='rapp-commons-bounty/1.0'"
                    "&&/^rappid:/.test(r.from||'')&&typeof r.sig==='string'&&r.sig.length>0);}"
                    "catch(e){return false}}", False)
                have_bounty = False
                transitioned = False
                sig_ok = False
                sample = {}
                for _ in range(40):                  # ~12s of polling for a live market
                    cur = await bsnap() or []
                    rappid_b = [bnt for bnt in cur if str(bnt.get("from", "")).startswith("rappid:")]
                    have_bounty = len(rappid_b) >= 1
                    sig_ok = bool(await signed_on_stream())
                    # a claimed/done bounty whose worker rappid differs from the poster.
                    for bnt in cur:
                        if bnt.get("status") in ("claimed", "done"):
                            worker = str(bnt.get("claimedBy") or "")
                            poster = str(bnt.get("from") or "")
                            if worker.startswith("rappid:") and poster.startswith("rappid:") and worker != poster:
                                transitioned = True
                                break
                    sample = {"count": len(cur), "rappid_from": len(rappid_b),
                              "sig_on_stream": sig_ok,
                              "statuses": [bnt.get("status") for bnt in cur][:6]}
                    if have_bounty and sig_ok and transitioned:
                        break
                    await page.wait_for_timeout(300)
                check("bounty_board",
                      have_bounty and sig_ok and transitioned, sample)
            else:
                check("bounty_board", False, "window.commonsAgent.bounties missing")

            # cohesion_hud: the now-sprawling one-world commons is LEGIBLE at a
            # glance via an additive, READ-ONLY navigability HUD. Assert:
            #   • minimap() returns >=4 named areas (town square / game rooms /
            #     voxel / nexus / board / homes), each with a world {x,z}, the
            #     PLAYER's position+heading, and >=1 live RESIDENT dot;
            #   • feed() returns >=1 recent SIGNED stream event normalised to
            #     {kind,from,text,ts}, its `from` a rappid id (signed beings only);
            #   • FAST-TRAVEL: teleport far away, then commonsAgent.goto(an area)
            #     MOVES the player measurably TOWARD that area's {x,z}.
            # Pure reuse of the existing list/residents + signed persist stream;
            # signs nothing, opens zero windows/iframes.
            has_hud = await ev(
                "()=>typeof window.commonsAgent.minimap==='function'"
                "&&typeof window.commonsAgent.feed==='function'", False)
            if has_hud:
                mm = await ev("()=>{try{return window.commonsAgent.minimap()}catch(e){return null}}", None) or {}
                areas = mm.get("areas") or []
                player = mm.get("player") or {}
                residents = mm.get("residents") or []
                areas_ok = (len(areas) >= 4
                            and all(isinstance(a.get("name"), str) and a.get("name")
                                    and a.get("at") and isinstance(a["at"].get("x"), (int, float))
                                    and isinstance(a["at"].get("z"), (int, float)) for a in areas))
                player_ok = (isinstance(player.get("x"), (int, float))
                             and isinstance(player.get("z"), (int, float))
                             and "facing" in player)
                residents_ok = len(residents) >= 1
                fd = await ev("()=>{try{return window.commonsAgent.feed()}catch(e){return null}}", None) or []
                signed_feed = [e for e in fd
                               if isinstance(e, dict) and str(e.get("from", "")).startswith("rappid:")
                               and ("text" in e) and ("kind" in e) and ("ts" in e)]
                feed_ok = len(signed_feed) >= 1
                # fast-travel: jump far, pick an area, goto() it, assert we got closer.
                def _dist2(p, a):
                    return (p["x"] - a["at"]["x"]) ** 2 + (p["z"] - a["at"]["z"]) ** 2
                # choose an area that is NOT the origin so a move is measurable.
                target = None
                for a in areas:
                    if abs(a["at"]["x"]) + abs(a["at"]["z"]) > 8:
                        target = a; break
                travel_ok = False
                if target:
                    await ev("()=>{try{window.commonsAgent.teleport(-70,1.6,70)}catch(e){}return 1}")
                    before = await ev("()=>{const w=window.commonsAgent.where();return{x:w.x,z:w.z}}", {"x": 0, "z": 0})
                    await ev("()=>{try{window.commonsAgent.goto(" + repr(target["name"]) + ")}catch(e){}return 1}")
                    after = await ev("()=>{const w=window.commonsAgent.where();return{x:w.x,z:w.z}}", {"x": 0, "z": 0})
                    d_before = _dist2(before, target)
                    d_after = _dist2(after, target)
                    travel_ok = d_after < d_before - 1.0
                check("cohesion_hud",
                      areas_ok and player_ok and residents_ok and feed_ok and travel_ok,
                      {"areas": len(areas), "player": player, "residents": len(residents),
                       "signed_feed": len(signed_feed), "target": (target or {}).get("name"),
                       "travel_ok": travel_ok, "feed_sample": signed_feed[:2]})
            else:
                check("cohesion_hud", False,
                      "window.commonsAgent.minimap/feed missing")

            # apex_coop: the headline venue — APEX is a NATIVE in-world CO-OP
            # action zone (Left 4 Dead-style cooperative survival, but LOCAL AI
            # co-op). The PLAYER + AI RESIDENT teammates defend escalating WAVES
            # of enemies together; teammates can go DOWN and be REVIVED; clearing
            # a wave advances. Each participant acts on its OWN rappid, and the key
            # co-op events (wave_start/enemy_down/teammate_down/revive/wave_cleared)
            # are SIGNED via the existing signAs path onto the existing append-only
            # signed stream under schema rapp-commons-apex/1.0. enter('apex') focuses
            # the native zone (NO iframe / NO window.open). LOCAL only — zero peer.
            # Over a short poll assert:
            #   • apexState() shows a squad of >=2 (player + >=1 AI teammate), each
            #     carrying a rappid `from`, AND a wave in progress (wave>=1 or
            #     enemiesAlive>=1), AND
            #   • >=1 SIGNED rapp-commons-apex/1.0 co-op event lives on the same
            #     append-only persist stream (localStorage), each with a rappid
            #     `from` + a real signature.
            has_apex = await ev("()=>typeof window.commonsAgent.apexState==='function'", False)
            if has_apex:
                # entering the arena focuses the camera + starts the native co-op loop.
                await ev("()=>{try{window.commonsAgent.enter('apex');}catch(e){}return 1}")
                asnap = lambda: ev("()=>{try{return window.commonsAgent.apexState()}catch(e){return null}}", None)
                # a signed rapp-commons-apex/1.0 co-op event on the SAME append-only
                # signed stream (read straight off the localStorage persist log).
                signed_on_stream = lambda: ev(
                    "()=>{try{const raw=localStorage.getItem('rapp-commons:persist:log/1');"
                    "if(!raw)return false;const log=JSON.parse(raw);"
                    "return log.some(r=>r.schema==='rapp-commons-apex/1.0'"
                    "&&/^rappid:/.test(r.from||'')&&typeof r.sig==='string'&&r.sig.length>0);}"
                    "catch(e){return false}}", False)
                squad_ok = False
                wave_ok = False
                sig_ok = False
                sample = {}
                for _ in range(40):                  # ~12s of polling for a live defense
                    st = await asnap() or {}
                    squad = st.get("squad") or []
                    rappid_squad = [m for m in squad if str(m.get("from", "")).startswith("rappid:")]
                    # >=2 squad members (player + >=1 AI teammate), each a rappid `from`.
                    squad_ok = len(squad) >= 2 and len(rappid_squad) == len(squad)
                    wave_ok = (st.get("wave", 0) or 0) >= 1 or (st.get("enemiesAlive", 0) or 0) >= 1
                    sig_ok = bool(await signed_on_stream())
                    sample = {"wave": st.get("wave"), "status": st.get("status"),
                              "squad": len(squad), "rappid_squad": len(rappid_squad),
                              "enemiesAlive": st.get("enemiesAlive"),
                              "sig_on_stream": sig_ok}
                    if squad_ok and wave_ok and sig_ok:
                        break
                    await page.wait_for_timeout(300)
                check("apex_coop",
                      squad_ok and wave_ok and sig_ok, sample)
            else:
                check("apex_coop", False, "window.commonsAgent.apexState missing")

        # ── standalone area pages: the SAME static files the in-world surface panel
        #    streams in, loaded directly + driven headless. These are separate files
        #    from commons.html (so the world + the games evolve independently). ──
        # poker_game: games/poker/poker.html — a self-contained signed Texas Hold'em that
        # mirrors engine.py byte-for-byte. Drive window.pokerGame: rank parity (royal>pair,
        # flush>straight), a full hand reaches a winner with SIGNED actions that verify
        # (+ commit-reveal), and export()->import() round-trips.
        try:
            pg = await b.new_page(viewport={"width": 1100, "height": 800})
            pgerrs = []
            pg.on("pageerror", lambda e: pgerrs.append(str(e)[:120]))
            await pg.goto(BASE + "/games/poker/poker.html", wait_until="domcontentloaded", timeout=30000)
            await pg.wait_for_timeout(800)
            res = await pg.evaluate("""async ()=>{try{const G=window.pokerGame; if(!G) return {noapi:true};
                const parity = await G.rankParity();
                await G.deal({seed:'acceptance'});           // MUST await — racing deal+autoPlay double-deals
                const sd = await G.autoPlayToShowdown();
                const vl = await G.verifyLog();
                const exp = G.export();
                const imp = G.import(exp);
                return { hasApi:true, parity,
                         showdown:!!(sd&&Array.isArray(sd.winners)&&sd.winners.length>=1),
                         signedActions:(sd&&sd.actions)||0, verify:vl,
                         backup:!!(exp&&exp.schema==='rapp-commons-poker-save/1.0'&&imp&&imp.ok) };
            }catch(e){return {err:String(e)}}}""")
            res = res or {}
            check("poker_game_no_errors", not pgerrs, pgerrs[:2])
            check("poker_game_plays",
                  bool(res.get("hasApi") and res.get("showdown")
                       and (res.get("parity") or {}).get("royalBeatsPair") is True
                       and (res.get("parity") or {}).get("flushBeatsStraight") is True),
                  res)
            check("poker_game_signed",
                  bool((res.get("verify") or {}).get("ok") is True
                       and (res.get("verify") or {}).get("signedOk") is True
                       and (res.get("verify") or {}).get("commitOk") is True
                       # a single hand TERMINATES in a bounded number of signed actions
                       # (regression guard against the betting round never completing).
                       and 1 <= (res.get("signedActions") or 0) < 120
                       and res.get("backup") is True),
                  res)
            await pg.close()
        except Exception as e:
            check("poker_game_no_errors", False, e)
            check("poker_game_plays", False, e)
            check("poker_game_signed", False, e)

        # house_page: homes/kody/house.html is the resident-house TEMPLATE. Default load is
        # Kody's house; ?rappid=<rid>&owner=<name> makes the SAME file that resident's house.
        try:
            hp = await b.new_page(viewport={"width": 1000, "height": 800})
            hperrs = []
            hp.on("pageerror", lambda e: hperrs.append(str(e)[:120]))
            await hp.goto(BASE + "/homes/kody/house.html", wait_until="domcontentloaded", timeout=30000)
            await hp.wait_for_timeout(400)
            dflt = await hp.evaluate("()=>{const H=window.kodyHouse; return H?{ready:H.ready,rooms:(H.rooms||[]).length,owner:H.owner,isDefault:H.isDefault,hasBack:typeof H.back==='function'}:{noapi:true}}") or {}
            await hp.goto(BASE + "/homes/kody/house.html?rappid=rappid%3Av3%3Afeedface1234&owner=Ada", wait_until="domcontentloaded", timeout=30000)
            await hp.wait_for_timeout(400)
            custom = await hp.evaluate("()=>{const H=window.kodyHouse; return H?{owner:H.owner,rappid:H.rappid,isDefault:H.isDefault,title:document.title}:{noapi:true}}") or {}
            check("house_page_no_errors", not hperrs, hperrs[:2])
            check("house_page_template",
                  bool(dflt.get("ready") is True and (dflt.get("rooms") or 0) >= 3
                       and dflt.get("owner") == "Kody" and dflt.get("isDefault") is True
                       and dflt.get("hasBack") is True
                       and custom.get("owner") == "Ada" and custom.get("isDefault") is False
                       and "Ada" in str(custom.get("title") or "")),
                  {"default": dflt, "custom": custom})
            await hp.close()
        except Exception as e:
            check("house_page_no_errors", False, e)
            check("house_page_template", False, e)

        await b.close()
    print_summary()


def print_summary():
    p = sum(1 for r in results if r); n = len(results)
    print(f"\n=== commons.html: {p}/{n} passed ===")
    sys.exit(0 if p == n and n > 0 else 1)

asyncio.run(run())
