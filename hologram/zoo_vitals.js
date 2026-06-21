#!/usr/bin/env node
/* (c) 2026 Kody Wildfeuer - PolyForm Noncommercial 1.0.0 - part of The RAPP Zoo */
/* zoo vitals <pk> — git-as-harness capability 3 (read side): the organism's vital-signs over its whole
   git history, so the player can TIME-TRAVEL it from static files. Walks every revision, records each
   frame the first commit it appeared in (recordedCt) WITH its values, and the homeostasis state per tick
   (gen / stress / alive). The player reconstructs the organism "as of <utc>" by keeping genesis + grown
   frames whose recordedCt <= the target tick. Writes hologram/lineage/<pk>.vitals.json. */
const fs = require("fs"), path = require("path"), G = require("./zoo_git.js");
let H = null; try { H = require("./homeostasis.js"); } catch (e) {}

const pk = process.argv[2], file = "hologram/drops.json", clone = G.CLONE;
if (!pk) { console.error("usage: zoo_vitals <pk>"); process.exit(2); }

const revs = G.revs(file, clone), frames = {}, ticks = [];
for (const r of revs) {
  const rec = G.extract(r.sha, pk, file, clone); if (!rec) continue;
  rec.k.forEach(function (f) {
    const key = f.at + "|" + (f.u == null ? "g" : f.u);
    if (!(key in frames)) frames[key] = Object.assign({}, f, { recordedCt: r.ct, recordedSha: r.sha.slice(0, 8) });
  });
  const hs = H ? H.homeostasis({ k: rec.k, gen: rec._gen, stress: rec._stress }) : { generation: rec.k.length, stress: 0, alive: true };
  ticks.push({ ct: r.ct, sha: r.sha.slice(0, 8), frames: rec.k.length, gen: hs.generation, stress: hs.stress, alive: hs.alive });
}
if (!ticks.length) { console.error("pk not found in any revision: " + pk); process.exit(1); }

const vitals = { pk: pk, born: parseInt((pk.split("·")[1] || "0"), 10) || null, frames: Object.keys(frames).map(function (k) { return frames[k]; }), ticks: ticks };
const dir = path.join(clone, "hologram/lineage"); fs.mkdirSync(dir, { recursive: true });
fs.writeFileSync(path.join(dir, pk.replace(/[^\w·.-]/g, "_") + ".vitals.json"), JSON.stringify(vitals));
const lastAlive = ticks.slice().reverse().find(function (t) { return t.alive; });
console.log("vitals " + pk + ": " + ticks.length + " ticks, " + vitals.frames.length + " distinct frames; last-alive gen " + (lastAlive ? lastAlive.gen : "—") + (ticks[ticks.length - 1].alive ? " (currently alive)" : " (CURRENTLY DEAD — restore-able)"));
