/* (c) 2026 Kody Wildfeuer - PolyForm Noncommercial 1.0.0 - part of The RAPP Zoo */
/* zoo_git — the shared primitive of GIT-AS-HARNESS. An organism is not a file; it is a record by `pk`
   inside shared minified JSON arrays committed to the repo. So git becomes the organism's control plane by
   REVISION-WALK + EXTRACT-BY-PK + structural k[] diff — no sharding, no rewriting the client surface.
   Dep-free node. (The browser can't run git; CLIs built on this deposit static lineage/ artifacts.) */
const { execSync } = require("child_process");
const path = require("path"), os = require("os");
const CLONE = process.env.ZOO_CLONE || path.join(os.homedir(), ".brainstem/neighborhoods/rapp-commons/clone");
const FIELDS = ["s", "l", "p", "g", "h", "x", "z"];

function git(args, clone) { return execSync(`git -C "${clone || CLONE}" ${args}`, { maxBuffer: 1 << 28, encoding: "utf8" }); }

// every revision that touched `file`, OLDEST-FIRST: [{sha, ct (committer UTC secs), subject}]
function revs(file, clone) {
  let out; try { out = git(`log --reverse --format=%H%x09%ct%x09%s -- ${file}`, clone).trim(); } catch (e) { return []; }
  if (!out) return [];
  return out.split("\n").map(function (l) { const p = l.split("\t"); return { sha: p[0], ct: parseInt(p[1], 10), subject: p.slice(2).join("\t") }; });
}

// extract one organism's record by pk from `file` at commit `sha` (null if not present / culled at that rev)
function extract(sha, pk, file, clone) {
  file = file || "hologram/drops.json";
  let blob; try { blob = git(`show ${sha}:${file}`, clone); } catch (e) { return null; }
  let data; try { data = JSON.parse(blob); } catch (e) { return null; }
  const arr = data.drops || data.moments || data.organisms || [];
  for (let i = 0; i < arr.length; i++) if (arr[i].pk === pk) return arr[i];
  return null;
}

// canonical signature of the immutable genesis frames (no u), order-independent + duplicate-at safe
function canonGenesis(k) {
  return ((k || []).filter(function (f) { return f.u == null; })
    .map(function (f) { return f.at + ":" + FIELDS.map(function (x) { return f[x]; }).join(","); }).sort().join("|"));
}
// structural diff of two records: grown frames ADDED (keyed on at,u) + whether the genesis genome MUTATED
// (a real anomaly — genesis is immutable) + sig/gen/stress moves. Duplicate-at safe (no by-at last-wins).
function diffOrganism(a, b) {
  const ka = (a && a.k) || [], kb = (b && b.k) || [], key = function (f) { return f.at + "|" + (f.u == null ? "" : f.u); };
  const ma = {}; ka.forEach(function (f) { ma[key(f)] = (ma[key(f)] || 0) + 1; });
  const seen = {}, added = [];
  kb.forEach(function (f) { const k = key(f); seen[k] = (seen[k] || 0) + 1; if (seen[k] > (ma[k] || 0)) added.push(f); });
  return { added: added, genesisMutated: canonGenesis(ka) !== canonGenesis(kb), sigChanged: (a && a.sig) !== (b && b.sig),
    genFrom: a && a._gen, genTo: b && b._gen, stressFrom: (a && a._stress) || 0, stressTo: (b && b._stress) || 0 };
}

// the commit at-or-before a UTC instant that touched `file` (for time-addressed extraction)
function revAtOrBefore(utcMs, file, clone) {
  const iso = new Date(utcMs).toISOString();
  try { const sha = git(`log -1 --format=%H --before="${iso}" -- ${file}`, clone).trim(); return sha || null; } catch (e) { return null; }
}

module.exports = { revs: revs, extract: extract, diffOrganism: diffOrganism, canonGenesis: canonGenesis, revAtOrBefore: revAtOrBefore, git: git, CLONE: CLONE, FIELDS: FIELDS };
