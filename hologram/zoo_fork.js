#!/usr/bin/env node
/* (c) 2026 Kody Wildfeuer - PolyForm Noncommercial 1.0.0 - part of The RAPP Zoo */
/* zoo fork / merge / lineage-tree — git-as-harness capability 4: a branch is a species fork, a merge is
   hybridization. fork stamps the organism's _id (first real use) and branches from its birth coordinate
   (the merge-base IS the genesis, so both forks provably descend from the same birth-proof). Each branch
   grows independently; merge reconciles them via the homeostasis merge driver (merge_homeostasis.js), NOT
   a textual 3-way. Writes hologram/lineage/<pk>.lineage.json for the static family-tree view.
   One-time per clone:  git config merge.homeostasis.driver "node hologram/merge_homeostasis.js %O %A %B %P"
   (.gitattributes already routes hologram/drops.json to it.) */
const fs = require("fs"), path = require("path"), { execSync } = require("child_process"), G = require("./zoo_git.js");
const file = "hologram/drops.json", clone = G.CLONE;
function git(a) { return execSync(`git -C "${clone}" ${a}`, { encoding: "utf8" }); }
function safe(pk) { return pk.replace(/[^\w·.-]/g, "_"); }
function lnPath(pk) { return path.join(clone, "hologram/lineage", safe(pk) + ".lineage.json"); }
function loadLn(pk) { try { return JSON.parse(fs.readFileSync(lnPath(pk), "utf8")); } catch (e) { return { pk: pk, _id: null, ancestor: null, branches: [], merges: [] }; } }
function saveLn(pk, o) { fs.mkdirSync(path.dirname(lnPath(pk)), { recursive: true }); fs.writeFileSync(lnPath(pk), JSON.stringify(o)); }

const cmd = process.argv[2], pk = process.argv[3];
if (cmd === "fork") {
  const variant = process.argv[4] || "v", branch = "lineage/" + safe(pk) + "-" + variant;
  const fp = path.join(clone, file), d = JSON.parse(fs.readFileSync(fp, "utf8")), rec = (d.drops || []).find(function (o) { return o.pk === pk; });
  if (!rec) { console.error("pk not in current " + file); process.exit(1); }
  if (!rec._id) { rec._id = "lin-" + safe(pk); fs.writeFileSync(fp, JSON.stringify(d)); git("add " + file); git(`commit -q -m "chore(harness): fork(${pk}) stamp _id"`); }
  git(`branch ${branch}`);
  const anc = git("rev-parse HEAD").trim().slice(0, 8), ln = loadLn(pk);
  ln._id = rec._id; ln.ancestor = anc; ln.branches = (ln.branches || []).filter(function (b) { return b.name !== branch; }).concat([{ name: branch, tip: anc, born: anc }]);
  saveLn(pk, ln); git("add hologram/lineage"); git(`commit -q -m "chore(harness): lineage(${pk}) forked -> ${branch}"`);
  console.log("forked " + pk + " -> " + branch + " (merge-base " + anc + " = its birth coordinate)");
}
else if (cmd === "merge") {
  const branch = process.argv[3]; if (!branch) { console.error("usage: zoo_fork merge <branch>"); process.exit(2); }
  try { git(`merge --no-edit ${branch}`); console.log("hybridized " + branch + " (homeostasis driver reconciled the frames)"); }
  catch (e) { console.error("merge aborted — the hybrid could not survive (sterile cross or cross-species)"); process.exit(1); }
}
else if (cmd === "lineage-tree") {
  if (!pk) { console.error("usage: zoo_fork lineage-tree <pk>"); process.exit(2); }
  console.log(git(`log --graph --oneline --all -- ${file}`).split("\n").slice(0, 30).join("\n"));
}
else { console.error("usage: zoo_fork <fork|merge|lineage-tree> ..."); process.exit(2); }
