#!/usr/bin/env node
/* build_warehouse - the Simon Willison free-data-warehouse build step. Fingerprints every organism in the
   feed + daily drops into ONE static file (hologram/warehouse.json) the browser queries client-side for
   "organisms more similar to mine." Append-only in spirit: re-run as the zoo grows. No server, no DB. */
const fs = require("fs"), F = require("./fingerprint.js"), dir = __dirname;
function load(p) { try { return JSON.parse(fs.readFileSync(p)); } catch (e) { return null; } }
function tokenOf(m) { return Buffer.from(JSON.stringify(m)).toString("base64").replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, ""); }
function stripLocal(m) { const o = {}; Object.keys(m).forEach(k => { if (k[0] !== "_") o[k] = m[k]; }); return o; }

const orgs = [], seen = new Set();
function add(m) {
  if (!m || !Array.isArray(m.k)) return;
  const key = (m.t || "") + "|" + (m.sig || "").slice(0, 12);
  if (seen.has(key)) return; seen.add(key);
  const clean = stripLocal(m);
  orgs.push({ t: m.t || "untitled", a: m.a || "@anon", b: m.b || "savanna",
    drop: m.drop ? { date: m.drop.date, hour: m.drop.hour, won_by: m.drop.won_by, gap_ms: m.drop.gap_ms } : undefined,
    born: (m.born != null ? m.born : undefined), frames: (m.k || []).length,
    signer: (m.pub && m.pub.x) ? m.pub.x.slice(0, 16) : undefined,
    signed: !!m.sig, token: tokenOf(clean), fp: F.fingerprint(m) });
}
(((load(dir + "/moments.json") || {}).moments) || []).forEach(add);
(((load(dir + "/drops.json") || {}).drops) || []).forEach(add);

const out = { v: 1, pattern: "static-data-warehouse", count: orgs.length, dims: orgs[0] ? orgs[0].fp.length : 0, organisms: orgs };
fs.writeFileSync(dir + "/warehouse.json", JSON.stringify(out));
console.log("warehouse:", orgs.length, "organisms ×", out.dims, "dims ->", (JSON.stringify(out).length / 1024).toFixed(1) + "KB");
