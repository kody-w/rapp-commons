const F = require("../hologram/fingerprint.js");
let pass = 0, fail = 0;
const ok = (n, c, e) => { if (c) pass++; else { fail++; console.log("FAIL:", n, e || ""); } };

// a base organism, a near-twin (tiny tweaks), and a wildly different one
const mine   = {t:"Mine",   k:[{at:0,s:.3,l:.3,p:.1,g:.4,h:150,x:0,z:0},{at:99,s:.6,l:.4,p:.5,g:.9,h:200,x:.1,z:.1}]};
const twin   = {t:"Twin",   k:[{at:0,s:.32,l:.28,p:.12,g:.42,h:152,x:0,z:0},{at:99,s:.58,l:.42,p:.5,g:.88,h:205,x:.1,z:.12}]};
const cousin = {t:"Cousin", k:[{at:0,s:.3,l:.5,p:.3,g:.5,h:170,x:0,z:0},{at:99,s:.7,l:.5,p:.6,g:.95,h:240,x:.2,z:0}]};
const alien  = {t:"Alien",  k:[{at:0,s:.9,l:.05,p:.95,g:.05,h:20,x:-.8,z:.8},{at:50,s:.1,l:.9,p:.0,g:1.0,h:300,x:.9,z:-.9},{at:99,s:.5,l:.5,p:.5,g:.0,h:90,x:0,z:0}]};

ok("fingerprint is fixed-length", F.fingerprint(mine).length === F.fingerprint(alien).length, F.fingerprint(mine).length);
ok("fingerprint is deterministic", JSON.stringify(F.fingerprint(mine)) === JSON.stringify(F.fingerprint(mine)));

const ranked = F.rank(mine, [alien, cousin, twin].map(m => ({t:m.t, fp:F.fingerprint(m)})));
ok("nearest is the twin", ranked[0].t === "Twin", ranked.map(r=>r.t+":"+r.dist));
ok("farthest is the alien", ranked[ranked.length-1].t === "Alien", ranked.map(r=>r.t));
ok("ordering twin < cousin < alien", ranked[0].dist < ranked[1].dist && ranked[1].dist < ranked[2].dist, ranked.map(r=>r.dist));
ok("twin similarity high", F.similar(mine, twin) > 0.5, F.similar(mine, twin));
ok("alien similarity lower than twin", F.similar(mine, alien) < F.similar(mine, twin));
ok("score in (0,1]", ranked.every(r => r.score > 0 && r.score <= 1));

// identity: an organism is most similar to itself
const selfRanked = F.rank(mine, [mine, alien].map(m=>({t:m.t,fp:F.fingerprint(m)})));
ok("self ranks first", selfRanked[0].t === "Mine" && selfRanked[0].dist < 1e-9, selfRanked[0].dist);

console.log(`\nfingerprint: ${pass}/${pass+fail} passed` + (fail ? "  *** RED ***" : "  ALL GREEN"));
process.exit(fail ? 1 : 0);
