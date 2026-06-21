#!/usr/bin/env node
/* (c) 2026 Kody Wildfeuer - PolyForm Noncommercial 1.0.0 - part of The RAPP Zoo */
/* merge_homeostasis — git-as-harness capability 4: a CUSTOM GIT MERGE DRIVER that makes git's hardest
   operation the organism's reproductive system. A branch is a species fork; a merge is hybridization.
   Git's textual 3-way merge would corrupt a minified JSON line into garbage, so per (at,u) FRAME resolution
   is delegated to the project's own survival law: fidelity.weaveFrame (weaveCheck + homeostasis.reconcile).
   Genesis frames must be byte-identical across ancestor/ours/theirs or the cross is rejected (you cannot
   hybridize two species). Foreign grown frames are woven in one by one; tearing/contradicting frames are
   resisted; if combined stress crosses STRESS_LIMIT the hybrid is sterile (merge aborts). The result can
   NEVER fail homeostasis or verifyCoordinate. Invoked by git as: merge_homeostasis %O %A %B %P  */
const fs = require("fs"), G = require("./zoo_git.js");
const Fid = require("./fidelity.js"), H = require("./homeostasis.js"), O = require("./organism.js");

// PURE: hybridize one organism record from ancestor(o)/ours(a)/theirs(b). Returns the verdict + merged record.
function mergeOrganism(o, a, b) {
  if (G.canonGenesis(a.k) !== G.canonGenesis(b.k) || G.canonGenesis(a.k) !== G.canonGenesis(o.k))
    return { viable: false, reason: "cross-species (genesis mismatch)", merged: null, inherited: [], rejected: [] };
  let merged = Object.assign({}, a, { k: a.k.slice(), _gen: a._gen != null ? a._gen : a.k.length, _stress: a._stress || 0 });
  const have = {}; merged.k.forEach(function (f) { if (f.u != null) have[f.at + "|" + f.u] = 1; });
  const foreign = b.k.filter(function (f) { return f.u != null && !have[f.at + "|" + f.u]; }).sort(function (x, y) { return x.at - y.at; });
  const inherited = [], rejected = [];
  foreign.forEach(function (f) { const w = Fid.weaveFrame(merged, f); merged = w.organism; if (w.woven) inherited.push(f.at); else rejected.push({ at: f.at, reason: w.reason || w.kind || "resisted" }); });
  const hs = H.homeostasis({ k: merged.k, gen: merged._gen, stress: merged._stress });   // map _-prefixed local metadata to the physics fields
  if (!hs.alive) return { viable: false, reason: "unsurvivable (stress " + hs.stress + ")", merged: merged, inherited: inherited, rejected: rejected, stress: hs.stress };
  if (O.verifyCoordinate(merged) !== true) return { viable: false, reason: "birth-proof broke", merged: null, inherited: inherited, rejected: rejected };
  return { viable: true, merged: merged, inherited: inherited, rejected: rejected, stress: hs.stress, gen: hs.generation };
}

// merge two whole drop files (every pk present in both); returns {drops, perPk, aborted}
function mergeDrops(oData, aData, bData) {
  const A = {}, B = {}, Om = {};
  (oData.drops || []).forEach(function (r) { if (r.pk) Om[r.pk] = r; });
  (aData.drops || []).forEach(function (r) { if (r.pk) A[r.pk] = r; });
  (bData.drops || []).forEach(function (r) { if (r.pk) B[r.pk] = r; });
  const out = (aData.drops || []).slice(), idx = {}; out.forEach(function (r, i) { if (r.pk) idx[r.pk] = i; });
  const perPk = []; let aborted = null;
  Object.keys(B).forEach(function (pk) {
    if (!A[pk]) { if (idx[pk] == null) { out.push(B[pk]); } return; }     // theirs-only organism: adopt it
    const v = mergeOrganism(Om[pk] || A[pk], A[pk], B[pk]); perPk.push({ pk: pk, viable: v.viable, inherited: (v.inherited || []).length, rejected: (v.rejected || []).length, reason: v.reason });
    if (v.viable) out[idx[pk]] = v.merged; else aborted = aborted || { pk: pk, reason: v.reason };
  });
  return { drops: out, perPk: perPk, aborted: aborted };
}

module.exports = { mergeOrganism: mergeOrganism, mergeDrops: mergeDrops };

// GIT DRIVER ENTRY: argv = %O %A %B %P  (ancestor, ours-and-output, theirs, path). Exit nonzero => conflict.
if (require.main === module) {
  const [oF, aF, bF] = process.argv.slice(2);
  const rd = function (f) { try { return JSON.parse(fs.readFileSync(f, "utf8")); } catch (e) { return { drops: [] }; } };
  const res = mergeDrops(rd(oF), rd(aF), rd(bF));
  if (res.aborted) { console.error("merge aborted: " + res.aborted.pk + " — " + res.aborted.reason); process.exit(1); }
  fs.writeFileSync(aF, JSON.stringify({ drops: res.drops }));
  console.error("hybridized " + res.perPk.length + " organism(s): " + res.perPk.map(function (p) { return p.pk + "(+" + p.inherited + "/-" + p.rejected + ")"; }).join(", "));
  process.exit(0);
}
