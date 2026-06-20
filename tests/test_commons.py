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
        await b.close()
    print_summary()


def print_summary():
    p = sum(1 for r in results if r); n = len(results)
    print(f"\n=== commons.html: {p}/{n} passed ===")
    sys.exit(0 if p == n and n > 0 else 1)

asyncio.run(run())
