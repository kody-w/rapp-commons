const { execSync } = require("child_process"), fs = require("fs"), os = require("os"), path = require("path");
const O = require("../hologram/organism.js"), Fid = require("../hologram/fidelity.js"), H = require("../hologram/homeostasis.js");
let pass = 0, fail = 0; const ok = (n, c, e) => { if (c) pass++; else { fail++; console.log("FAIL:", n, e || ""); } };

const tmp = fs.mkdtempSync(path.join(os.tmpdir(), "ckt-")); const HG = path.join(tmp, "hologram"); fs.mkdirSync(HG, { recursive: true });
execSync(`git init -q "${tmp}"`); execSync(`git -C "${tmp}" config user.email t@t.io`); execSync(`git -C "${tmp}" config user.name t`);
const DROPS = path.join(HG, "drops.json"), CKT = path.join(__dirname, "../hologram/zoo_checkout.js");
const ENV = Object.assign({}, process.env, { ZOO_CLONE: tmp, ZOO_NOW: "1750000000000" });
function commit(arr, ctSec, msg) { fs.writeFileSync(DROPS, JSON.stringify({ drops: arr })); execSync(`git -C "${tmp}" add hologram/drops.json`);
  execSync(`git -C "${tmp}" commit -q -m "${msg}"`, { env: Object.assign({}, ENV, { GIT_AUTHOR_DATE: ctSec + " +0000", GIT_COMMITTER_DATE: ctSec + " +0000" }) }); return execSync(`git -C "${tmp}" rev-parse HEAD`, { encoding: "utf8" }).trim(); }
function run(args) { try { execSync(`node "${CKT}" ${args}`, { env: ENV, stdio: "pipe" }); return 0; } catch (e) { return e.status || 1; } }
function headRec(pk) { return JSON.parse(fs.readFileSync(DROPS, "utf8")).drops.find(o => o.pk === pk); }
function histLen() { return parseInt(execSync(`git -C "${tmp}" rev-list --count HEAD`, { encoding: "utf8" }).trim(), 10); }

const ms = 1750000000000;
let g = O.organismFromStamp(ms + 7); g._gen = g.k.length; g._stress = 0; const pk = g.pk;
commit([g], 1750000001, "C1-birth");
g = Fid.refineOverTime(g, ms + 2000).organism; const c2 = commit([g], 1750000002, "C2-grow");
g = Fid.refineOverTime(g, ms + 3000).organism; const healthy = JSON.parse(JSON.stringify(g)); commit([g], 1750000003, "C3-healthy");
commit([Object.assign({}, g, { _stress: 12 })], 1750000004, "C4-dead");           // catastrophic injury -> dead

ok("HEAD organism is dead (stress >= LIMIT)", H.homeostasis({ k: headRec(pk).k, gen: headRec(pk)._gen, stress: headRec(pk)._stress }).alive === false);
const lenBefore = histLen();
ok("restore exits 0", run(`restore "${pk}"`) === 0);
ok("restored == last-healthy (C3) record byte-for-byte", JSON.stringify(headRec(pk)) === JSON.stringify(healthy));
ok("restored is alive again", H.homeostasis({ k: headRec(pk).k, gen: headRec(pk)._gen, stress: headRec(pk)._stress }).alive === true);
ok("restored still verifies (birth-proof intact)", O.verifyCoordinate(headRec(pk)) === true);
ok("APPEND-only — history grew, not rewritten", histLen() === lenBefore + 1);
ok("events.jsonl witnessed the restore", /"op":"restore"/.test(fs.readFileSync(path.join(HG, "lineage/events.jsonl"), "utf8")));

// checkout to an explicit earlier sha
ok("checkout @C2 exits 0", run(`checkout "${pk}" --at ${c2}`) === 0);
const c2rec = JSON.parse(execSync(`git -C "${tmp}" show ${c2}:hologram/drops.json`, { encoding: "utf8" })).drops.find(o => o.pk === pk);
ok("checkout reproduced the C2 record", JSON.stringify(headRec(pk)) === JSON.stringify(c2rec));

// ADVERSARIAL: a revision whose genesis was forged -> checkout must REFUSE and write nothing
const forge = Object.assign({}, healthy, { k: healthy.k.map((f, i) => i === 0 ? Object.assign({}, f, { h: (f.h + 100) % 360 }) : f) });
const cForge = commit([forge], 1750000010, "C10-forge-genesis");
const before = fs.readFileSync(DROPS, "utf8");
ok("checkout REFUSES a forged-genesis ref (nonzero exit)", run(`checkout "${pk}" --at ${cForge}`) !== 0);
ok("a refused checkout wrote NO change", fs.readFileSync(DROPS, "utf8") === before);

console.log(`\nzoo_checkout: ${pass}/${pass + fail} passed` + (fail ? "  *** RED ***" : "  ALL GREEN"));
process.exit(fail ? 1 : 0);
