const { execSync } = require("child_process"), fs = require("fs"), os = require("os"), path = require("path");
const O = require("../hologram/organism.js"), Fid = require("../hologram/fidelity.js"), Grew = require("../hologram/zoo_grew.js");
let pass = 0, fail = 0; const ok = (n, c, e) => { if (c) pass++; else { fail++; console.log("FAIL:", n, e || ""); } };

// ---- PURE leg: physics-classified diff, no git ----
const ms = 1750000000000, utc = ms + 5000;
let orgA = O.organismFromStamp(ms); orgA._gen = orgA.k.length; orgA._stress = 0;
const orgB = Fid.refineOverTime(orgA, utc).organism;
const r = Grew.growthReport(orgA, orgB);
ok("reports exactly one grown frame", r.framesAdded === 1, r.framesAdded);
ok("grown frame carries the utc stamp", r.frames[0] && r.frames[0].u === utc);
ok("coarsest gap deepened", r.coarsestAfter < r.coarsestBefore, r.coarsestBefore + "->" + r.coarsestAfter);
ok("LOSSLESS — A + added reproduces B", r.lossless === true);
ok("no corrupt frames (all weave-valid)", r.corruptFrames === 0);
ok("genesis intact", r.genesisMutated === false);

const orgC = Object.assign({}, orgA, { k: orgA.k.map((f, i) => i === 0 ? Object.assign({}, f, { h: (f.h + 30) % 360 }) : f) });
const rc = Grew.growthReport(orgA, orgC);
ok("a pure genesis mutation is detected", rc.genesisMutated === true);
ok("a pure mutation reports zero growth", rc.framesAdded === 0);

// ---- GIT leg: grow across commits, then zoo_grew between the endpoints ----
const tmp = fs.mkdtempSync(path.join(os.tmpdir(), "grew-")); const HG = path.join(tmp, "hologram"); fs.mkdirSync(HG, { recursive: true });
execSync(`git init -q "${tmp}"`); execSync(`git -C "${tmp}" config user.email t@t.io`); execSync(`git -C "${tmp}" config user.name t`);
function commit(arr, ctSec, msg) {
  fs.writeFileSync(path.join(HG, "drops.json"), JSON.stringify({ drops: arr }));
  execSync(`git -C "${tmp}" add hologram/drops.json`);
  execSync(`git -C "${tmp}" commit -q -m "${msg}"`, { env: Object.assign({}, process.env, { GIT_AUTHOR_DATE: ctSec + " +0000", GIT_COMMITTER_DATE: ctSec + " +0000" }) });
}
let g = O.organismFromStamp(ms + 111); g._gen = g.k.length; g._stress = 0; const pk = g.pk;
const t0 = 1750000000; commit([g], t0, "t0 birth");
let framesAtT0 = g.k.filter(f => f.u != null).length;
for (let i = 1; i <= 4; i++) { g = Fid.refineOverTime(g, ms + 1000 + i * 1000).organism; commit([g], t0 + i, "grow " + i); }
const t5 = t0 + 4, framesAtT5 = g.k.filter(f => f.u != null).length;
execSync(`node "${path.join(__dirname, "../hologram/zoo_grew.js")}" "${pk}" ${t0 * 1000} ${t5 * 1000}`, { env: Object.assign({}, process.env, { ZOO_CLONE: tmp }) });
const rep = JSON.parse(fs.readFileSync(path.join(HG, "lineage", pk.replace(/[^\w·.-]/g, "_") + ".grew.json"), "utf8"));
ok("git: framesAdded == frames(t5) − frames(t0)", rep.framesAdded === (framesAtT5 - framesAtT0), rep.framesAdded + " vs " + (framesAtT5 - framesAtT0));
ok("git: lossless across the window", rep.lossless === true);
ok("git: genesis intact across growth", rep.genesisMutated === false);

console.log(`\nzoo_grew: ${pass}/${pass + fail} passed` + (fail ? "  *** RED ***" : "  ALL GREEN"));
process.exit(fail ? 1 : 0);
