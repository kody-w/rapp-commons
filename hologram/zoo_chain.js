#!/usr/bin/env node
/* (c) 2026 Kody Wildfeuer - PolyForm Noncommercial 1.0.0 - part of The RAPP Zoo */
/* zoo chain — the FULL NODE. Treats the git history of the data file as a blockchain (blocks = commits,
   hash-linked to their parents) and validates the chain's laws across ALL of history:
     (2) birth-proof permanence — verifyCoordinate holds for every organism at every block,
     (2b) append-only identity   — a genesis genome is never rewritten between blocks.
   (Rule 1, hash-linkage, is inherent to git; rule 4, signatures, is checked in the browser.) Emits a static
   hologram/lineage/chain.json {height, blocks, organisms, genesisBlock, headBlock, valid, anomalies} that
   anyone can verify from the public, globally-served, can-never-die ledger. Usage: zoo_chain.js [file] */
const fs = require("fs"), path = require("path"), G = require("./zoo_git.js");
let O = null; try { O = require("./organism.js"); } catch (e) {}

const file = process.argv[2] || "hologram/drops.json", clone = G.CLONE;
const revs = G.revs(file, clone);
const anomalies = [], genesis = {}, organisms = new Set();
let checked = 0;
for (const r of revs) {
  let blob; try { blob = G.git(`show ${r.sha}:${file}`, clone); } catch (e) { continue; }
  let data; try { data = JSON.parse(blob); } catch (e) { anomalies.push({ block: r.sha.slice(0, 8), reason: "unparseable block" }); continue; }
  for (const o of (data.drops || data.moments || [])) {
    if (!o.pk || o.born == null) continue;
    organisms.add(o.pk);
    if (O && O.verifyCoordinate(o) !== true) { anomalies.push({ block: r.sha.slice(0, 8), ct: r.ct, pk: o.pk, reason: "birth-proof violation" }); continue; }
    const gen = G.canonGenesis(o.k);
    if (genesis[o.pk] != null && genesis[o.pk] !== gen) anomalies.push({ block: r.sha.slice(0, 8), ct: r.ct, pk: o.pk, reason: "genesis rewritten — append-only violation" });
    else genesis[o.pk] = gen;
    checked++;
  }
}

const report = {
  chain: "kody-w/rapp-commons", file: file, height: revs.length, blocks: revs.length, organisms: organisms.size, organismRecordsChecked: checked,
  genesisBlock: revs[0] && revs[0].sha.slice(0, 8), genesisCt: revs[0] && revs[0].ct,
  headBlock: revs[revs.length - 1] && revs[revs.length - 1].sha.slice(0, 8), headCt: revs[revs.length - 1] && revs[revs.length - 1].ct,
  valid: anomalies.length === 0, anomalies: anomalies.slice(0, 50)
};
const dir = path.join(clone, "hologram/lineage"); fs.mkdirSync(dir, { recursive: true });
fs.writeFileSync(path.join(dir, "chain.json"), JSON.stringify(report));
console.log("chain: " + report.height + " blocks · " + report.organisms + " organisms · " + checked + " records checked · valid=" + report.valid + (anomalies.length ? " (" + anomalies.length + " anomalies)" : " ✓"));
