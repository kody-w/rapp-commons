const O = require("../hologram/ownership.js"), R = require("../hologram/rappid.js");
let pass = 0, fail = 0; const ok = (n, c, e) => { if (c) pass++; else { fail++; console.log("FAIL:", n, e || ""); } };

const rid = R.ofMoment("sky·1782078749409");
const A = "keyAAA", B = "keyBBB", C = "keyCCC", X = "keyXXX";   // pubkey fingerprints (humans or agents)

// mint owner = A, no transfers -> A owns it
ok("a fresh deed is owned by the minter", O.deedChain(rid, A, []).owner === A);
ok("owner is expressed as a keeper rappid", /^rappid:keeper:[0-9a-f]{64}$/.test(O.deedChain(rid, A, []).ownerRappid));

// A -> B -> C : a valid hash-linked deed chain
const t1 = O.newTransfer(rid, A, B, rid, 1000);
const t2 = O.newTransfer(rid, B, C, t1.hash, 2000);
const d = O.deedChain(rid, A, [t1, t2]);
ok("rights flow A->B->C, current owner is C", d.owner === C, d.owner);
ok("the deed records 2 transfers + a mint", d.transfers === 2 && d.history.length === 3);
ok("history is mint, then A->B, then B->C", d.history[1].to === B && d.history[2].to === C);

// order independence (resolved by hash-linkage, not array order)
ok("resolves regardless of array order", O.deedChain(rid, A, [t2, t1]).owner === C);

// a transfer NOT authorized by the current owner is ignored (X tries to give away B's Moment)
const forged = O.newTransfer(rid, X, C, t1.hash, 1500);
ok("an unauthorized transfer (wrong `from`) is rejected", O.deedChain(rid, A, [t1, forged]).owner === B);

// a tampered transfer body (hash mismatch) breaks the chain at that point
const tampered = Object.assign({}, t2, { to: X });   // changed `to` but kept t2.hash
ok("a tampered transfer is rejected (hash mismatch)", O.deedChain(rid, A, [t1, tampered]).owner === B);

// transfers for a DIFFERENT rappid don't affect this deed
const other = O.newTransfer(R.ofMoment("sky·1"), A, X, R.ofMoment("sky·1"), 999);
ok("foreign-rappid transfers are ignored", O.deedChain(rid, A, [t1, t2, other]).owner === C);

// the transfer hash is the join key / chain link
ok("each transfer hash-links to the previous", t2.prev === t1.hash);
ok("transfer hash is deterministic sha256 of the body", t1.hash === R.sha256(O.transferBody(t1)));

console.log(`\nownership: ${pass}/${pass + fail} passed` + (fail ? "  *** RED ***" : "  ALL GREEN"));
process.exit(fail ? 1 : 0);
