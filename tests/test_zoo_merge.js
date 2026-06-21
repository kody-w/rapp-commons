const O = require("../hologram/organism.js"), H = require("../hologram/homeostasis.js"), F = require("../hologram/fingerprint.js");
const Merge = require("../hologram/merge_homeostasis.js");
let pass = 0, fail = 0; const ok = (n, c, e) => { if (c) pass++; else { fail++; console.log("FAIL:", n, e || ""); } };

const ms = 1750000000000;
const base = O.organismFromStamp(ms); base._gen = base.k.length; base._stress = 0;
// a frame that bends the curve a little (within the weave tolerance 0.12) so growth is visible yet valid
const bent = (at, u, ds) => Object.assign({}, H.valueAt(base.k, at), { at: at, u: u, s: Math.max(0.05, Math.min(0.95, (H.valueAt(base.k, at).s || 0.4) + (ds || 0.08))) });
const withFrames = (frames, gen) => Object.assign({}, base, { k: base.k.concat(frames).sort((x, y) => x.at - y.at), _gen: (gen != null ? gen : base.k.length + frames.length), _stress: 0 });

// (1) COMPATIBLE — two branches grow in DIFFERENT gaps, both weave-valid -> viable hybrid = union
const A = withFrames([bent(30, ms + 100)]), B = withFrames([bent(70, ms + 200)]);
const m = Merge.mergeOrganism(base, A, B);
ok("compatible cross is VIABLE", m.viable === true, m.reason);
ok("inherits theirs' non-overlapping frame", m.inherited.length === 1 && m.rejected.length === 0, JSON.stringify(m.inherited) + "/" + JSON.stringify(m.rejected));
ok("hybrid is the union of both growths", m.merged.k.filter(f => f.u != null).length === 2);
ok("clean cross — zero stress", m.stress === 0);
ok("hybrid still verifies (birth-proof intact)", O.verifyCoordinate(m.merged) === true);
ok("speciation is measurable (fingerprints diverge)", JSON.stringify(F.fingerprint(A)) !== JSON.stringify(F.fingerprint(B)));

// (1b) a single web-TEARING frame is dropped, not merged
const wild = Object.assign({}, H.valueAt(base.k, 45), { at: 45, u: ms + 300, s: (H.valueAt(base.k, 45).s || 0.4) + 0.7, g: 1 });
const Bt = withFrames([bent(70, ms + 200), wild], base.k.length + 2);
const mt = Merge.mergeOrganism(base, A, Bt);
ok("a web-tearing frame is rejected", mt.rejected.some(r => r.at === 45));
ok("the torn frame is absent from the hybrid", !mt.merged.k.some(f => f.at === 45 && f.u === ms + 300));
ok("the good frame still merged", mt.viable === true && mt.inherited.indexOf(70) >= 0);

// (2) CONTRADICTORY — 13 frames settle at a genesis `at` far off value -> stress crosses LIMIT -> STERILE
const g99 = base.k.find(f => f.at === 99);
const contra = []; for (let i = 0; i < 13; i++) contra.push(Object.assign({}, g99, { at: 99, u: ms + 1000 + i, h: (g99.h + 90) % 360 }));   // hue 90° off the settled frame => always contradicts
const Bx = withFrames(contra, base.k.length);
const mx = Merge.mergeOrganism(base, A, Bx);
ok("over-stressed cross is STERILE (not viable)", mx.viable === false, mx.reason);
ok("sterility is reported as unsurvivable", /unsurvivable/.test(mx.reason || ""), mx.reason);

// (3) CROSS-SPECIES — different genesis -> rejected outright
const Bs = Object.assign({}, base, { k: base.k.map((f, i) => i === 0 ? Object.assign({}, f, { h: (f.h + 100) % 360 }) : f) });
const msp = Merge.mergeOrganism(base, A, Bs);
ok("cross-species is REJECTED (genesis mismatch)", msp.viable === false && /cross-species/.test(msp.reason), msp.reason);

// --- OVERLAY: lay N dimensions of the same moment over each other (dream-catcher composite) ---
(function () {
  const bent2 = (at, u, ds) => Object.assign({}, H.valueAt(base.k, at), { at: at, u: u, s: Math.max(0.05, Math.min(0.95, (H.valueAt(base.k, at).s || 0.4) + ds)) });
  const D0 = Object.assign({}, base, { k: base.k.concat([bent2(20, 1, 0.06)]).sort((x, y) => x.at - y.at), _gen: base.k.length + 1, _stress: 0 });
  const D1 = Object.assign({}, base, { k: base.k.concat([bent2(50, 2, 0.07)]).sort((x, y) => x.at - y.at), _gen: base.k.length + 1, _stress: 0 });
  const D2 = Object.assign({}, base, { k: base.k.concat([bent2(80, 3, 0.06)]).sort((x, y) => x.at - y.at), _gen: base.k.length + 1, _stress: 0 });
  const ov = Merge.overlay([D0, D1, D2]);
  ok2("overlay of 3 dimensions is viable", ov.viable === true, ov.reason);
  ok2("overlay composites all consistent layers (union of grown frames)", ov.composite.k.filter(f => f.u != null).length === 3, ov.frames);
  ok2("overlay records a layer per dimension", ov.layers.length === 3 && ov.layers[1].inherited === 1);
  ok2("a different moment cannot overlay (genesis mismatch)", Merge.overlay([D0, Object.assign({}, D1, { k: D1.k.map((f, i) => i === 0 ? Object.assign({}, f, { h: (f.h + 90) % 360 }) : f) })]).viable === false);
  function ok2(n, c, e) { if (c) pass++; else { fail++; console.log("FAIL:", n, e || ""); } }
})();
console.log(`\nzoo_merge: ${pass}/${pass + fail} passed` + (fail ? "  *** RED ***" : "  ALL GREEN"));
process.exit(fail ? 1 : 0);
