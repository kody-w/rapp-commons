const H = require("../hologram/homeostasis.js");
let pass = 0, fail = 0;
function ok(name, cond, extra) { if (cond) { pass++; } else { fail++; console.log("FAIL:", name, extra || ""); } }

// an organism: born with two settled frames (a life-trajectory from at=0 to at=99)
let org = { t: "Mossling", k: [{at:0,s:.3,l:.3,p:.1,g:.4,h:150,x:0,z:0}, {at:99,s:.6,l:.4,p:.6,g:.9,h:260,x:0,z:0}], gen: 2, stress: 0 };

// 1) REFINE: fold fractal detail in at at=50 — downstream (at=99) is untouched -> absorbed, it grows
let r1 = H.reconcile(org, {at:50, s:.45, l:.35, p:.4, g:.7, h:205, x:.1, z:.1});
ok("refine accepted", r1.accepted && r1.kind === "refined", r1.kind);
ok("refine grows generation", r1.organism.gen === 3, r1.organism.gen);
ok("refine survives", r1.survives === true);
let dn = r1.organism.k.find(k => k.at === 99);
ok("downstream preserved", dn && dn.h === 260 && dn.g === 0.9);
org = r1.organism;

// 2) FRACTAL UNLIMITED: keep refining between frames forever — homeostasis holds
for (let i = 0; i < 30; i++) org = H.reconcile(org, {at: 25 + i*0.5, s:.4, g:.6, h:200}).organism;
ok("unlimited fractal refinement", org.k.length >= 32, org.k.length);
ok("still alive after 30 refinements", H.homeostasis(org).alive === true);
ok("no stress from refinement", H.homeostasis(org).stress === 0);

// 3) REDUNDANT: re-feed an existing frame with the SAME data -> "nothing changed", absorbed
let r3 = H.reconcile(org, {at:0, s:.3, l:.3, p:.1, g:.4, h:150, x:0, z:0});
ok("redundant absorbed (nothing changed)", r3.kind === "redundant" && r3.survives, r3.kind);
ok("redundant adds no stress", (r3.organism.stress||0) === 0);

// 4) CONTRADICTION: try to REWRITE the settled downstream frame at=99 -> RESISTED, stress rises
let r4 = H.reconcile(org, {at:99, s:.6, l:.4, p:.6, g:.9, h:30, x:0, z:0}); // h 260 -> 30 contradicts
ok("contradiction resisted", r4.kind === "resisted" && !r4.accepted, r4.kind);
ok("contradiction raises stress", r4.organism.stress === 1, r4.organism.stress);
ok("downstream NOT overwritten", r4.organism.k.find(k=>k.at===99).h === 260);
ok("still survives one contradiction", r4.survives === true);

// 5) HOMEOSTASIS BREAKS: keep hammering contradictions past what it can resist -> it dies
let dying = r4.organism;
for (let i = 0; i < H.STRESS_LIMIT + 2; i++) dying = H.reconcile(dying, {at:99, h: (i*40)%360, s:.6}).organism;
ok("homeostasis breaks under sustained contradiction", H.homeostasis(dying).alive === false, H.homeostasis(dying).stress);

console.log(`\nhomeostasis: ${pass}/${pass+fail} passed` + (fail ? "  *** RED ***" : "  ALL GREEN"));
process.exit(fail ? 1 : 0);
