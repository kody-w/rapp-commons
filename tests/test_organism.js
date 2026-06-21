const O = require("../hologram/organism.js");
let pass = 0, fail = 0;
const ok = (n, c, e) => { if (c) pass++; else { fail++; console.log("FAIL:", n, e || ""); } };

const t = 1750526625123;  // a fixed UTC ms
const a = O.organismFromStamp(t), a2 = O.organismFromStamp(t);
ok("deterministic from a stamp", JSON.stringify(a) === JSON.stringify(a2));
ok("pk is sky·<ms> for pure time", a.pk === "sky·" + t, a.pk);
ok("carries born = the exact ms", a.born === t);
ok("valid structure", a.k.length >= 3 && a.k[0].at === 0 && a.k[a.k.length-1].at === 99 && O.BIOMES.includes(a.b));
ok("has a deterministic name", typeof a.t === "string" && a.t.length >= 6);

// globally unique per UTC ms: 2000 consecutive ms -> 2000 distinct organisms
const seen = new Set();
for (let i = 0; i < 2000; i++) { const o = O.organismFromStamp(t + i); seen.add(JSON.stringify(o.k) + o.b); }
ok("globally unique across 2000 consecutive ms", seen.size === 2000, seen.size);

// location binds traits (Pokémon-GO): same instant, a place -> a different organism + a geohash pk
const here = O.organismFromStamp(t, { lat: 47.6062, lng: -122.3321, place: "Seattle" });
ok("place pk is geohash·ms", /·\d+$/.test(here.pk) && here.pk.indexOf("sky") === -1, here.pk);
ok("place changes the organism", JSON.stringify(here.k) !== JSON.stringify(a.k));
ok("carries its location", here.loc && here.loc.place === "Seattle");
const there = O.organismFromStamp(t, { lat: 35.6895, lng: 139.6917, place: "Tokyo" });
ok("a different place -> a different creature at the same instant", JSON.stringify(here.k) !== JSON.stringify(there.k));

// verifiable: regenerate from the coordinate to prove the binding (ownership of a moment)
ok("verifyCoordinate accepts a true mint", O.verifyCoordinate(a) === true);
ok("verifyCoordinate accepts a place mint", O.verifyCoordinate(here) === true);
const forged = JSON.parse(JSON.stringify(a)); forged.k[1].h = (forged.k[1].h + 90) % 360;
ok("verifyCoordinate rejects a forgery", O.verifyCoordinate(forged) === false);

// DIAL — an address regenerates its organism anywhere (no fetch)
ok("dial sky·ms round-trips the organism", JSON.stringify(O.fromPk(a.pk).k) === JSON.stringify(a.k) && O.fromPk(a.pk).pk === a.pk, a.pk);
ok("dial a place pk round-trips", JSON.stringify(O.fromPk(here.pk).k) === JSON.stringify(here.k) && O.fromPk(here.pk).pk === here.pk, here.pk);
ok("dial a bare UTC ms works", O.fromPk(String(t)).pk === "sky·" + t);
ok("dial rejects garbage", O.fromPk("not-an-address") === null);

console.log(`\norganism: ${pass}/${pass+fail} passed` + (fail ? "  *** RED ***" : "  ALL GREEN"));
process.exit(fail ? 1 : 0);
