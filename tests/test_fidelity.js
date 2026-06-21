const F = require("../hologram/fidelity.js"), O = require("../hologram/organism.js"), H = require("../hologram/homeostasis.js");
let pass = 0, fail = 0;
const ok = (n, c, e) => { if (c) pass++; else { fail++; console.log("FAIL:", n, e || ""); } };

// a genesis organism born at an exact UTC instant
let org = O.organismFromStamp(1750526625123);
org._gen = org.k.length; org._stress = 0;
const genesisFrames = org.k.length, genesisRes = F.finestResolution(org.k);

// grow fidelity over simulated UTC time
let t = 1750526625123, lastRes = genesisRes, monotone = true;
for (let i = 0; i < 40; i++) { t += 1000 + i; const r = F.refineOverTime(org, t);
  if (r.accepted) { org = r.organism; if (F.finestResolution(org.k) > lastRes + 1e-9) monotone = false; lastRes = F.finestResolution(org.k); } }
ok("frames grew over time", org.k.length > genesisFrames + 20, org.k.length);
ok("finest resolution got finer", F.finestResolution(org.k) < genesisRes, F.finestResolution(org.k).toFixed(3) + " < " + genesisRes.toFixed(3));
ok("resolution never coarsens (monotone deepening)", monotone);
ok("grown frames carry their UTC arrival stamp", org.k.filter(f => f.u != null).length >= 20, org.k.filter(f => f.u != null).length);
ok("no homeostasis stress from growth", (org._stress || 0) === 0, org._stress);
ok("genesis still verifies after growth", O.verifyCoordinate(org) === true);
ok("genesis frames untouched", JSON.stringify(org.k.filter(f => f.u == null)) === JSON.stringify(O.organismFromStamp(1750526625123).k));

// deterministic growth
let a = O.organismFromStamp(42); a._gen = a.k.length;
let b = O.organismFromStamp(42); b._gen = b.k.length;
for (let i = 0; i < 10; i++) { a = F.refineOverTime(a, 100 + i).organism; b = F.refineOverTime(b, 100 + i).organism; }
ok("growth is deterministic", JSON.stringify(a.k) === JSON.stringify(b.k));

// --- DREAM CATCHER weave: a frame is only woven if consistent with the neighbours it sits between ---
let g = O.organismFromStamp(1750526625123); g._gen = g.k.length; g._stress = 0;
const mid = F.nextRefineAt(g.k), base = H.valueAt(g.k, mid.at);
ok("dreamcatcher weaves a consistent frame", F.weaveFrame(g, Object.assign({}, base, { at: mid.at, u: 999 })).woven === true);
const w2 = F.weaveFrame(g, Object.assign({}, base, { at: mid.at + 0.001, s: (base.s || 0.4) + 0.6, g: 1, u: 1000 }));
ok("dreamcatcher rejects an inconsistent frame", w2.woven === false, JSON.stringify(w2.reason));
ok("rejection names the torn field", /tears the web/.test(w2.reason || ""), w2.reason);
ok("endpoint frame has no web to tear", F.weaveCheck(g.k, { at: 0, s: 0.9 }).ok === true);

console.log(`\nfidelity: ${pass}/${pass + fail} passed` + (fail ? "  *** RED ***" : "  ALL GREEN"));
process.exit(fail ? 1 : 0);
