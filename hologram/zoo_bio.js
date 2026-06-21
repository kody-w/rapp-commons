#!/usr/bin/env node
/* (c) 2026 Kody Wildfeuer - PolyForm Noncommercial 1.0.0 - part of The RAPP Zoo */
/* zoo bio <pk> — the dated LIFE-STORY of one organism, recovered from git history (the file where it was
   never stored as its own object). Walks every commit that touched the drop stream, extracts the record by
   pk at each, diffs consecutive k[] arrays, and emits ordered chapters: repo-birth, each grown UTC frame
   (with the `at` it deepened, its self-reported `u`, and the committer date that witnessed it), re-signings
   (ownership re-asserted), and homeostasis injuries. The birth-proof is re-verified at every revision; any
   rev where verifyCoordinate flips false is flagged ANOMALY — the public repo audits itself. Writes the
   static hologram/lineage/<pk>.bio.json the player's lifeline reads. Usage: zoo_bio.js <pk> [file] */
const fs = require("fs"), path = require("path"), G = require("./zoo_git.js");
let O = null; try { O = require("./organism.js"); } catch (e) {}

const pk = process.argv[2], file = process.argv[3] || "hologram/drops.json", clone = G.CLONE;
if (!pk) { console.error("usage: zoo_bio <pk>"); process.exit(2); }

const revs = G.revs(file, clone);
let prev = null, repoBorn = null, ownedBy = null, breakAt = null;
const chapters = [];
for (const r of revs) {
  const rec = G.extract(r.sha, pk, file, clone);
  if (!rec) continue;
  const coordOk = O ? O.verifyCoordinate(rec) : null;
  if (coordOk === false && !breakAt) breakAt = r.sha;
  if (!prev) {
    repoBorn = r.sha;
    chapters.push({ kind: "birth", sha: r.sha.slice(0, 8), ct: r.ct, frames: rec.k.length,
      genesis: rec.k.filter(function (f) { return f.u == null; }).length, anomaly: coordOk === false });
  } else {
    const d = G.diffOrganism(prev, rec);
    d.added.forEach(function (f) {
      chapters.push({ kind: (f.u == null ? "genesis-add" : "grow"), sha: r.sha.slice(0, 8), ct: r.ct,
        at: f.at, u: (f.u != null ? f.u : null), anomaly: (f.u == null) || coordOk === false });
    });
    if (d.genesisMutated) chapters.push({ kind: "injury", sha: r.sha.slice(0, 8), ct: r.ct, anomaly: true });   // genesis is immutable — a mutation is an anomaly
    if (d.sigChanged && rec.sig) chapters.push({ kind: "resign", sha: r.sha.slice(0, 8), ct: r.ct, signer: ((rec.pub && rec.pub.x) || "").slice(0, 16) });
    if (d.stressTo > d.stressFrom) chapters.push({ kind: "stress", sha: r.sha.slice(0, 8), ct: r.ct, stress: d.stressTo });
  }
  if (rec.pub && rec.pub.x) ownedBy = rec.pub.x.slice(0, 16);
  prev = rec;
}
if (!prev) { console.error("pk not found in any revision: " + pk); process.exit(1); }

const bornMs = parseInt((pk.split("·")[1] || pk.split("|")[1] || "0"), 10) || null;
const bio = { pk: pk, born: bornMs, repoBorn: repoBorn && repoBorn.slice(0, 8), ownedBy: ownedBy,
  breakAt: breakAt && breakAt.slice(0, 8), anomalies: chapters.filter(function (c) { return c.anomaly; }).length,
  frames: prev.k.length, grownFrames: prev.k.filter(function (f) { return f.u != null; }).length,
  revisions: revs.length, chapters: chapters };

const dir = path.join(clone, "hologram/lineage"); fs.mkdirSync(dir, { recursive: true });
const safe = pk.replace(/[^\w·.-]/g, "_");
fs.writeFileSync(path.join(dir, safe + ".bio.json"), JSON.stringify(bio));
console.log("bio " + pk + ": " + chapters.length + " chapters across " + revs.length + " revs · born-repo " + bio.repoBorn + " · " + (breakAt ? "ANOMALY@" + bio.breakAt : "birth-proof ✓ everywhere"));
