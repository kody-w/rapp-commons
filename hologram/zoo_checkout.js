#!/usr/bin/env node
/* (c) 2026 Kody Wildfeuer - PolyForm Noncommercial 1.0.0 - part of The RAPP Zoo */
/* zoo checkout / restore / revert — git-as-harness capability 3 (write side): time-travel ONE organism to
   an earlier/healthier self, APPEND-ONLY (never rewrites public main), gated by the birth-proof.
     zoo_checkout restore <pk>            — resurrect the most recent revision still in homeostasis (self-heal)
     zoo_checkout checkout <pk> --at <ref> — summon it as it was at a sha or UTC ms
     zoo_checkout revert <pk> <bad-sha>    — surgically prune the web-tearing frame a bad tick introduced
   Refuses signed (owner-only, a browser act) records and refuses any state whose genesis would not verify.
   Every op appends a witness line to hologram/lineage/events.jsonl. */
const fs = require("fs"), path = require("path"), { execSync } = require("child_process");
const G = require("./zoo_git.js"); let O = require("./organism.js"), H = require("./homeostasis.js");
const file = "hologram/drops.json", clone = G.CLONE, FP = path.join(clone, file);
function headDrops() { return JSON.parse(fs.readFileSync(FP, "utf8")); }
function writeRec(rec) { const d = headDrops(), i = d.drops.findIndex(function (o) { return o.pk === rec.pk; }); if (i < 0) d.drops.push(rec); else d.drops[i] = rec; fs.writeFileSync(FP, JSON.stringify(d)); }
function gate(rec) { if (rec.sig) { console.error("refuse: " + rec.pk + " is signed — time-travel is owner-only (browser)"); process.exit(3); } if (O.verifyCoordinate(rec) !== true) { console.error("refuse: birth-proof would not hold for " + rec.pk); process.exit(4); } }
function event(ev) { fs.mkdirSync(path.join(clone, "hologram/lineage"), { recursive: true }); fs.appendFileSync(path.join(clone, "hologram/lineage/events.jsonl"), JSON.stringify(ev) + "\n"); }
function commit(msg) { execSync(`git -C "${clone}" add hologram/drops.json hologram/lineage/events.jsonl`); execSync(`git -C "${clone}" commit -q -m "${msg}"`); }
function nowMs() { return parseInt(process.env.ZOO_NOW || String(Date.now()), 10); }
function alive(rec) { return H.homeostasis({ k: rec.k, gen: rec._gen, stress: rec._stress }); }

const cmd = process.argv[2], pk = process.argv[3];
if (!cmd || !pk) { console.error("usage: zoo_checkout <restore|checkout|revert> <pk> [...]"); process.exit(2); }

if (cmd === "restore") {
  const revs = G.revs(file, clone).slice().reverse();   // newest-first
  for (const r of revs) {
    const rec = G.extract(r.sha, pk, file, clone); if (!rec) continue;
    const hs = alive(rec);
    if (hs.alive) { gate(rec); writeRec(rec); event({ op: "restore", pk: pk, toSha: r.sha.slice(0, 8), utc: nowMs(), gen: hs.generation });
      commit(`chore(harness): restore(${pk}) -> ${r.sha.slice(0, 8)} (last-alive gen ${hs.generation})`);
      console.log("restored " + pk + " to " + r.sha.slice(0, 8) + " · gen " + hs.generation + " · alive"); process.exit(0); }
  }
  console.error("no alive revision found for " + pk); process.exit(1);
}
if (cmd === "checkout") {
  const i = process.argv.indexOf("--at"), ref = process.argv[i + 1];
  if (i < 0 || !ref) { console.error("usage: zoo_checkout checkout <pk> --at <sha|utcMs>"); process.exit(2); }
  const sha = /^\d{10,}$/.test(ref) ? G.revAtOrBefore(parseInt(ref, 10), file, clone) : ref;
  const rec = sha && G.extract(sha, pk, file, clone); if (!rec) { console.error("pk not present at " + ref); process.exit(1); }
  gate(rec); writeRec(rec); event({ op: "checkout", pk: pk, toSha: String(sha).slice(0, 8), utc: nowMs() });
  commit(`chore(harness): checkout(${pk}) @ ${String(sha).slice(0, 8)}`);
  console.log("checked out " + pk + " as of " + String(sha).slice(0, 8)); process.exit(0);
}
if (cmd === "revert") {
  const badSha = process.argv[4]; if (!badSha) { console.error("usage: zoo_checkout revert <pk> <bad-sha>"); process.exit(2); }
  const parent = execSync(`git -C "${clone}" rev-parse ${badSha}~1`, { encoding: "utf8" }).trim();
  const before = G.extract(parent, pk, file, clone), at = G.extract(badSha, pk, file, clone);
  if (!at) { console.error("pk not at " + badSha); process.exit(1); }
  const introduced = G.diffOrganism(before || { k: [] }, at).added.filter(function (f) { return f.u != null; });
  if (!introduced.length) { console.error("no grown frame introduced by " + badSha); process.exit(1); }
  const head = headDrops(), rec = head.drops.find(function (o) { return o.pk === pk; }); if (!rec) { console.error("pk not at HEAD"); process.exit(1); }
  const bad = {}; introduced.forEach(function (f) { bad[f.at + "|" + f.u] = 1; });
  const pruned = Object.assign({}, rec, { k: rec.k.filter(function (f) { return !bad[f.at + "|" + (f.u == null ? "" : f.u)]; }) });
  if (!alive(pruned).alive) { console.error("pruning would still leave " + pk + " dead"); process.exit(5); }
  gate(pruned); writeRec(pruned); event({ op: "revert", pk: pk, badSha: badSha.slice(0, 8), removed: introduced.length, utc: nowMs() });
  commit(`chore(harness): revert(${pk}) prune ${introduced.length} frame(s) from ${badSha.slice(0, 8)}`);
  console.log("reverted " + pk + ": pruned " + introduced.length + " frame(s) from " + badSha.slice(0, 8)); process.exit(0);
}
console.error("unknown command " + cmd); process.exit(2);
