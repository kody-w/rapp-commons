const { execSync } = require("child_process"), fs = require("fs"), os = require("os"), path = require("path");
const O = require("../hologram/organism.js"), Fid = require("../hologram/fidelity.js");
let pass = 0, fail = 0; const ok = (n, c, e) => { if (c) pass++; else { fail++; console.log("FAIL:", n, e || ""); } };

const tmp = fs.mkdtempSync(path.join(os.tmpdir(), "zoo-"));
const HG = path.join(tmp, "hologram"); fs.mkdirSync(HG, { recursive: true });
execSync(`git init -q "${tmp}"`); execSync(`git -C "${tmp}" config user.email t@t.io`); execSync(`git -C "${tmp}" config user.name tester`);
const ZBIO = path.join(__dirname, "../hologram/zoo_bio.js");
function commit(arr, ct, msg) {
  fs.writeFileSync(path.join(HG, "drops.json"), JSON.stringify({ drops: arr }));
  execSync(`git -C "${tmp}" add hologram/drops.json`);
  execSync(`git -C "${tmp}" commit -q -m "${msg}"`, { env: Object.assign({}, process.env, { GIT_AUTHOR_DATE: ct + " +0000", GIT_COMMITTER_DATE: ct + " +0000" }) });
}
function runBio(pk) { execSync(`node "${ZBIO}" "${pk}"`, { env: Object.assign({}, process.env, { ZOO_CLONE: tmp }) });
  return JSON.parse(fs.readFileSync(path.join(HG, "lineage", pk.replace(/[^\w·.-]/g, "_") + ".bio.json"), "utf8")); }
function bioText(pk) { return fs.readFileSync(path.join(HG, "lineage", pk.replace(/[^\w·.-]/g, "_") + ".bio.json"), "utf8"); }

const ms = 1750000000000;
let org = O.organismFromStamp(ms); org._gen = org.k.length; org._stress = 0;
const pk = org.pk, other = O.organismFromStamp(ms + 9999999); other._gen = other.k.length;
const expectAt = Fid.nextRefineAt(O.organismFromStamp(ms).k).at;

commit([org, other], 1750000001, "C1 birth");
org = Fid.refineOverTime(org, ms + 5000).organism;
commit([org, other], 1750000002, "C2 grow");
const signed = Object.assign({}, org, { sig: "deadbeef", pub: { x: "PUBKEY0000000000", y: "y" } });
commit([signed, other], 1750000003, "C3 resign");
commit([signed, Object.assign({}, other, { _gen: other._gen + 1 })], 1750000004, "C4 churn-other");

const bio = runBio(pk), kinds = bio.chapters.map(c => c.kind);
ok("birth chapter first", kinds[0] === "birth", kinds);
ok("exactly birth+grow+resign (unrelated C4 contributes nothing)", JSON.stringify(kinds) === JSON.stringify(["birth", "grow", "resign"]), kinds);
ok("grow chapter at == nextRefineAt", Math.abs(bio.chapters.find(c => c.kind === "grow").at - expectAt) < 0.01, bio.chapters.find(c => c.kind === "grow").at + " vs " + expectAt);
ok("grow frame carries its u stamp", bio.chapters.find(c => c.kind === "grow").u === ms + 5000);
ok("resign records the signer", (bio.chapters.find(c => c.kind === "resign").signer || "").length >= 8);
ok("birth-proof holds everywhere (no anomaly)", bio.breakAt === null && bio.anomalies === 0, bio.breakAt);
ok("repoBorn is an 8-char sha", typeof bio.repoBorn === "string" && bio.repoBorn.length === 8);
ok("born parsed from pk", bio.born === ms);

const t1 = bioText(pk); runBio(pk); ok("bio is deterministic / idempotent (byte-identical)", t1 === bioText(pk));

// adversarial: hand-edit a genesis frame's hue beyond EPS, no u-stamp -> ANOMALY + birth-proof breaks
const forged = Object.assign({}, signed, { k: signed.k.map((f, i) => i === 0 ? Object.assign({}, f, { h: (f.h + 120) % 360 }) : f) });
commit([forged, other], 1750000005, "C5 forge-genesis");
const bioF = runBio(pk);
ok("forged genesis flips birth-proof to ANOMALY", bioF.breakAt !== null && bioF.anomalies > 0, bioF.breakAt + " anomalies=" + bioF.anomalies);

console.log(`\nzoo_git/bio: ${pass}/${pass + fail} passed` + (fail ? "  *** RED ***" : "  ALL GREEN"));
process.exit(fail ? 1 : 0);
