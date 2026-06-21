#!/usr/bin/env node
/* (c) 2026 Kody Wildfeuer - PolyForm Noncommercial 1.0.0 - part of The RAPP Zoo */
/* zoo grew <pk> [utcA] [utcB] — git-as-harness capability 2: what did THIS creature BECOME between two
   instants? A semantic, physics-classified frame-level changelog (instead of the meaningless textual diff
   of a 500KB minified line). Resolves each UTC to the commit at-or-before it, extracts the record by pk at
   both, and reports: frames grown (which coarsest gaps deepened, finest-resolution before→after, each new
   frame's u-stamp), trajectory drift per field, generation/stress deltas, genesis integrity, and a LOSSLESS
   guarantee (applying the added frames to A reproduces B). With no A/B it diffs the last two revs that
   touched the pk. Writes hologram/lineage/<pk>.grew.json for the player's "how I grew" card. */
const fs = require("fs"), path = require("path"), G = require("./zoo_git.js");
let Fid = null, H = null; try { Fid = require("./fidelity.js"); H = require("./homeostasis.js"); } catch (e) {}
const SAMPLES = [10, 25, 40, 55, 70, 85];

// PURE: physics-classified diff of two organism records (also usable client-side on two fetched snapshots)
function growthReport(a, b) {
  const d = G.diffOrganism(a, b), grown = d.added.filter(function (f) { return f.u != null; });
  const corrupt = (Fid ? grown.filter(function (f) { return !Fid.weaveCheck(a.k, f).ok; }) : []);
  const drift = {};
  if (H) G.FIELDS.forEach(function (fl) { drift[fl] = +(SAMPLES.reduce(function (s, at) { return s + ((H.valueAt(b.k, at)[fl] || 0) - (H.valueAt(a.k, at)[fl] || 0)); }, 0) / SAMPLES.length).toFixed(3); });
  const srt = function (k) { return k.slice().sort(function (x, y) { return (x.at - y.at) || ((x.u || 0) - (y.u || 0)); }); };
  const lossless = JSON.stringify(srt(a.k.concat(grown))) === JSON.stringify(srt(b.k));
  const coarse = function (k) { return Fid && Fid.nextRefineAt(k) ? +Fid.nextRefineAt(k).gap.toFixed(2) : null; };
  return { framesAdded: grown.length, frames: grown.map(function (f) { return { at: f.at, u: f.u }; }),
    finestBefore: Fid ? +Fid.finestResolution(a.k).toFixed(2) : null, finestAfter: Fid ? +Fid.finestResolution(b.k).toFixed(2) : null,
    coarsestBefore: coarse(a.k), coarsestAfter: coarse(b.k),
    drift: drift, genesisMutated: d.genesisMutated, corruptFrames: corrupt.length,
    genFrom: d.genFrom, genTo: d.genTo, stressFrom: d.stressFrom, stressTo: d.stressTo, lossless: lossless };
}

function main() {
  const pk = process.argv[2], file = "hologram/drops.json", clone = G.CLONE;
  if (!pk) { console.error("usage: zoo_grew <pk> [utcA] [utcB]"); process.exit(2); }
  let recA, recB, fromCt, toCt;
  if (process.argv[3] && process.argv[4]) {
    const shaA = G.revAtOrBefore(parseInt(process.argv[3], 10), file, clone), shaB = G.revAtOrBefore(parseInt(process.argv[4], 10), file, clone);
    recA = shaA && G.extract(shaA, pk, file, clone); recB = shaB && G.extract(shaB, pk, file, clone);
  } else {
    const revs = G.revs(file, clone).filter(function (r) { return G.extract(r.sha, pk, file, clone); });
    if (revs.length < 2) { console.error("need >=2 revisions carrying pk " + pk); process.exit(1); }
    const a = revs[revs.length - 2], b = revs[revs.length - 1];
    recA = G.extract(a.sha, pk, file, clone); recB = G.extract(b.sha, pk, file, clone); fromCt = a.ct; toCt = b.ct;
  }
  if (!recA || !recB) { console.error("could not extract pk at both instants"); process.exit(1); }
  const rep = growthReport(recA, recB); rep.pk = pk; rep.fromCt = fromCt || null; rep.toCt = toCt || null;
  const dir = path.join(clone, "hologram/lineage"); fs.mkdirSync(dir, { recursive: true });
  fs.writeFileSync(path.join(dir, pk.replace(/[^\w·.-]/g, "_") + ".grew.json"), JSON.stringify(rep));
  console.log("grew " + pk + ": +" + rep.framesAdded + " frames (finest " + rep.finestBefore + "→" + rep.finestAfter + "), lossless=" + rep.lossless + ", corrupt=" + rep.corruptFrames + ", genesis-intact=" + (!rep.genesisMutated));
}

module.exports = { growthReport: growthReport };
if (require.main === module) main();
