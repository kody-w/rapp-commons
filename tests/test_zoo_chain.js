const { execSync } = require("child_process"), fs = require("fs"), os = require("os"), path = require("path");
const O = require("../hologram/organism.js"), Fid = require("../hologram/fidelity.js");
let pass = 0, fail = 0; const ok = (n, c, e) => { if (c) pass++; else { fail++; console.log("FAIL:", n, e || ""); } };
const tmp = fs.mkdtempSync(path.join(os.tmpdir(), "chain-")); const HG = path.join(tmp, "hologram"); fs.mkdirSync(HG, { recursive: true });
execSync(`git init -q "${tmp}"`); execSync(`git -C "${tmp}" config user.email t@t`); execSync(`git -C "${tmp}" config user.name t`);
const CH = path.join(__dirname, "../hologram/zoo_chain.js");
function commit(arr, ct, msg) { fs.writeFileSync(path.join(HG, "drops.json"), JSON.stringify({ drops: arr })); execSync(`git -C "${tmp}" add hologram/drops.json`);
  execSync(`git -C "${tmp}" commit -q -m "${msg}"`, { env: Object.assign({}, process.env, { GIT_AUTHOR_DATE: ct + " +0000", GIT_COMMITTER_DATE: ct + " +0000" }) }); }
function runChain() { execSync(`node "${CH}"`, { env: Object.assign({}, process.env, { ZOO_CLONE: tmp }) }); return JSON.parse(fs.readFileSync(path.join(HG, "lineage/chain.json"), "utf8")); }

const ms = 1750000000000; let g = O.organismFromStamp(ms + 5); g._gen = g.k.length; g._stress = 0;
commit([g], 1750000001, "block1-genesis");
g = Fid.refineOverTime(g, ms + 1000).organism; commit([g], 1750000002, "block2-grow");
let c = runChain();
ok("clean history is a VALID chain", c.valid === true, JSON.stringify(c.anomalies));
ok("height counts blocks", c.height === 2, c.height);
ok("genesis + head blocks recorded", !!c.genesisBlock && !!c.headBlock);
ok("organism counted", c.organisms === 1);

const forged = Object.assign({}, g, { k: g.k.map((f, i) => i === 0 ? Object.assign({}, f, { h: (f.h + 100) % 360 }) : f) });
commit([forged], 1750000003, "block3-forge");
c = runChain();
ok("a forged genesis block INVALIDATES the chain", c.valid === false);
ok("the anomaly names the violation", c.anomalies.some(a => /birth-proof|append-only/.test(a.reason)), JSON.stringify(c.anomalies));

console.log(`\nzoo_chain: ${pass}/${pass + fail} passed` + (fail ? "  *** RED ***" : "  ALL GREEN"));
process.exit(fail ? 1 : 0);
