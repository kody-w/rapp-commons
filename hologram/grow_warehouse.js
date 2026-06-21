#!/usr/bin/env node
/* grow_warehouse <capFramesPerOrg> <utcMs> <stepPerRun> — the autonomous grower. Walks the static
   drops + feed (GitHub-raw data) and deepens each spacetime-born organism's frame fidelity over UTC
   time via fidelity.js/homeostasis (never contradicting its established frames, genesis stays intact),
   capped so the static files stay lean. The data is grown in place. */
const fs = require("fs"), Fid = require("./fidelity.js"), dir = __dirname;
const CAP = parseInt(process.argv[2] || "48", 10), NOW = parseInt(process.argv[3] || "0", 10), STEP = parseInt(process.argv[4] || "1", 10);
function load(p) { try { return JSON.parse(fs.readFileSync(p)); } catch (e) { return null; } }
function grow(m, ms) { if (!m || !Array.isArray(m.k) || m.born == null) return 0; let g = 0;
  for (let i = 0; i < STEP && m.k.length < CAP; i++) { const r = Fid.refineOverTime(m, ms + i);
    if (r.accepted) { m.k = r.organism.k; m._gen = r.organism._gen; m._stress = r.organism._stress; g++; } else break; } return g; }
let total = 0, touched = 0;
const drops = load(dir + "/drops.json");
(drops && drops.drops || []).forEach(m => { const g = grow(m, NOW); if (g) { total += g; touched++; } });
if (drops) fs.writeFileSync(dir + "/drops.json", JSON.stringify(drops));
const feed = load(dir + "/moments.json");                         // mirror grown drops back into the feed
if (feed && drops) { const byT = {}; (drops.drops || []).forEach(d => byT[d.t] = d);
  (feed.moments || []).forEach((m, i) => { if (byT[m.t]) feed.moments[i] = byT[m.t]; }); fs.writeFileSync(dir + "/moments.json", JSON.stringify(feed)); }
console.log("grew", total, "frames across", touched, "organisms (cap " + CAP + ")");
