const R = require("../hologram/rappid.js");
let pass = 0, fail = 0; const ok = (n, c, e) => { if (c) pass++; else { fail++; console.log("FAIL:", n, e || ""); } };

// the SHA-256 must be correct (known vectors) or the whole eternity binding is wrong
ok("sha256('') vector", R.sha256("") === "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855");
ok("sha256('abc') vector", R.sha256("abc") === "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad");
ok("utf-8 mid-dot hashes (no ascii bail)", typeof R.sha256("sky·123") === "string" && R.sha256("sky·123").length === 64);

const pk = "sky·1782078749409";
const rid = R.ofMoment(pk);
ok("rappid form is rappid:<slug>:<64hex>", /^rappid:moment:[0-9a-f]{64}$/.test(rid), rid);
ok("deterministic + eternal (same pk -> same rappid)", R.ofMoment(pk) === rid);
ok("distinct pks -> distinct rappids", R.ofMoment("sky·1") !== R.ofMoment("sky·2"));
const p = R.parse(rid);
ok("parse round-trips", p && p.slug === "moment" && p.hex.length === 64);
ok("the 64-hex IS the join key", p.hex === R.sha256("moment:" + pk));

// keeper identity from a signing key
const kr = R.ofKeeper("J3nh-TBoudm4Irdd");
ok("keeper rappid", /^rappid:keeper:[0-9a-f]{64}$/.test(kr));
ok("moment and keeper namespaces are domain-separated", R.ofMoment("x") !== R.ofKeeper("x"));

// COMPATIBILITY: read every legacy form -> emit canonical
ok("canonicalize a pk", R.canonicalize("sky·1782078749409") === rid);
ok("canonicalize a bare UTC ms", R.canonicalize("1782078749409") === R.ofMoment("sky·1782078749409"));
ok("canonicalize a '|' legacy separator", R.canonicalize("sky|1782078749409") === rid);
ok("canonicalize a rappid is idempotent", R.canonicalize(rid) === rid);
ok("canonicalize rejects garbage", R.canonicalize("not-an-id") === null);

console.log(`\nrappid: ${pass}/${pass + fail} passed` + (fail ? "  *** RED ***" : "  ALL GREEN"));
process.exit(fail ? 1 : 0);
