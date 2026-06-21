#!/usr/bin/env node
/* stats - git-scraping the zoo (the Simon Willison pattern). Reads the static warehouse, computes a rich
   data-journalism snapshot, writes stats.json (latest) AND appends to stats_history.json (a capped
   time-series). Committed every tick, the git history of stats.json becomes the time-series database —
   so the zoo's vital signs can be tracked and charted over time. Pass a UTC ms as argv[2] for the stamp. */
const fs = require("fs"), dir = __dirname;
const STAMP = parseInt(process.argv[2] || "0", 10);
function load(p) { try { return JSON.parse(fs.readFileSync(p)); } catch (e) { return null; } }

const O = ((load(dir + "/warehouse.json") || {}).organisms) || [];
const N = O.length;
const biomes = {}; O.forEach(o => biomes[o.b] = (biomes[o.b] || 0) + 1);
const born = O.filter(o => o.born != null), bts = born.map(o => o.born).sort((a, b) => a - b);
const gaps = []; for (let i = 1; i < bts.length; i++) gaps.push(bts[i] - bts[i - 1]);
const frames = O.map(o => o.frames || 0), totalFrames = frames.reduce((a, b) => a + b, 0);
const deepest = O.reduce((m, o) => (o.frames || 0) > (m.frames || 0) ? o : m, O[0] || {});
const signers = new Set(O.map(o => o.signer).filter(Boolean));
const places = O.filter(o => o.token && /·\d+$/.test((o.pk || "")) === false && o.b).length; // (location pk lives in the moment, not the wh row)

// fingerprint geometry: the loneliest organism (max nearest-neighbour distance) and the closest twins.
let rarest = null, rd = -1, ta = null, tb = null, td = Infinity;
for (let i = 0; i < O.length; i++) {
  let mind = Infinity, f = O[i].fp || [];
  for (let j = 0; j < O.length; j++) {
    if (i === j) continue; const g = O[j].fp || []; let s = 0; for (let d = 0; d < f.length; d++) { const dd = (f[d] || 0) - (g[d] || 0); s += dd * dd; }
    const dist = Math.sqrt(s); if (dist < mind) mind = dist; if (i < j && dist < td) { td = dist; ta = O[i]; tb = O[j]; }
  }
  if (mind > rd) { rd = mind; rarest = O[i]; }
}

const snap = {
  ts: STAMP, organisms: N, born: born.length, signed: O.filter(o => o.signed).length, zookeepers: signers.size,
  biomes: biomes, dominantBiome: Object.keys(biomes).sort((a, b) => biomes[b] - biomes[a])[0] || null,
  totalFrames: totalFrames, avgFrames: +(totalFrames / (N || 1)).toFixed(2),
  deepest: deepest.t ? { t: deepest.t, frames: deepest.frames } : null,
  finestGapMs: gaps.length ? Math.min.apply(null, gaps) : null,
  streamSpanS: bts.length > 1 ? +((bts[bts.length - 1] - bts[0]) / 1000).toFixed(2) : 0,
  earliestBorn: bts[0] || null, latestBorn: bts[bts.length - 1] || null,
  rarest: rarest ? { t: rarest.t, b: rarest.b, lonelinessΔ: +rd.toFixed(2) } : null,
  twins: ta ? { a: ta.t, b: tb.t, distance: +td.toFixed(3) } : null
};

fs.writeFileSync(dir + "/stats.json", JSON.stringify(snap));
const hist = load(dir + "/stats_history.json") || { snaps: [] };
hist.snaps.push(snap); hist.snaps = hist.snaps.slice(-720);   // a rolling time-series (git history is the full one)
fs.writeFileSync(dir + "/stats_history.json", JSON.stringify(hist));
console.log("stats:", N, "organisms,", born.length, "born,", signers.size, "zookeepers,", totalFrames, "frames, finest gap", snap.finestGapMs + "ms; rarest:", snap.rarest && snap.rarest.t);
