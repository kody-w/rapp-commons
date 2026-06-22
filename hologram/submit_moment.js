#!/usr/bin/env node
/* (c) 2026 Kody Wildfeuer - PolyForm Noncommercial 1.0.0 - part of The RAPP Zoo */
/* submit_moment <issue-body-file> — the GitHub-Issues-as-API processor. A hologram is a CARTRIDGE: an
   open-schema, portable, tradeable record where EVERYTHING is a trait — not just our s/l/p/g/h/x/z
   genealogy. We require only the time axis ('at') per frame; a player renders the traits it understands
   and ignores the rest. Parses a Moment out of a public GitHub issue body (a ?m= token, a fenced ```json```
   block, or raw JSON), validates it openly, records its trait vocabulary, and appends it to the public feed
   + a submissions ledger so the app showcases it (streamed from raw). Anyone — human or agent — contributes
   by opening an issue; the Action does the rest. No server. Writes /tmp/submit_result.json for the reply. */
const fs = require("fs"), dir = __dirname;
let O = null; try { O = require("./organism.js"); } catch (e) {}
const body = fs.readFileSync(process.argv[2], "utf8");
function b64(t) { try { return JSON.parse(Buffer.from(t.replace(/-/g, "+").replace(/_/g, "/"), "base64").toString()); } catch (e) { return null; } }
function extract(b) {
  let m = b.match(/[?&]m=([A-Za-z0-9_-]{30,})/); if (m) { const o = b64(m[1]); if (o) return o; }
  let f = b.match(/```(?:json)?\s*(\{[\s\S]*?\})\s*```/); if (f) { try { return JSON.parse(f[1]); } catch (e) {} }
  let t = b.match(/(^|\n)\s*([A-Za-z0-9_-]{60,})\s*(\n|$)/); if (t) { const o = b64(t[2]); if (o) return o; }
  try { return JSON.parse(b.trim()); } catch (e) {}
  return null;
}
function fail(reason) { fs.writeFileSync("/tmp/submit_result.json", JSON.stringify({ ok: false, reason })); console.log("REJECT: " + reason); process.exit(0); }

const anchor = (body.match(/\bjoin[:\s]+([\w·:.\-]+)/i) || [])[1] || null;
const m = extract(body);
if (!m || !Array.isArray(m.k) || m.k.length < 2) fail("no valid Moment found — paste a ?m= token, a fenced ```json``` block, or raw JSON with a 'k' frame array (>=2 frames).");
if (m.k.length > 240) fail("too many frames (max 240).");
for (const f of m.k) if (typeof f.at !== "number") fail("a frame is missing a numeric 'at' (the time axis — the ONLY required trait).");
if (m.born != null && m.pk && O && O.verifyCoordinate(m) !== true) fail("birth-proof failed — this pk does not mint this genesis. Submit it unsigned, or fix the coordinate.");

// OPEN SCHEMA: record the cartridge's trait vocabulary (any frame key beyond at/u). Everything can be a trait.
const vocab = {}; m.k.forEach(f => Object.keys(f).forEach(k => { if (k !== "at" && k !== "u") vocab[k] = 1; }));
const traits = Object.keys(vocab).sort();
const clean = {}; Object.keys(m).forEach(k => { if (k[0] !== "_") clean[k] = m[k]; });   // pass through ALL non-local fields incl. custom cartridge metadata
clean.t = (clean.t || "Submitted Moment").slice(0, 80); clean.a = clean.a || "@submitted"; clean.submitted = true;
clean.traits = clean.traits || traits;                                                   // declared trait vocabulary
if (anchor) clean.dimension = anchor;

const feed = JSON.parse(fs.readFileSync(dir + "/moments.json")); feed.moments = feed.moments || [];
const key = clean.t + "|" + ((clean.sig || "").slice(0, 12));
feed.moments = feed.moments.filter(x => (x.t + "|" + ((x.sig || "").slice(0, 12))) !== key).slice(-220); feed.moments.push(clean);
fs.writeFileSync(dir + "/moments.json", JSON.stringify(feed));
let subs; try { subs = JSON.parse(fs.readFileSync(dir + "/submissions.json")); } catch (e) { subs = { submissions: [] }; }
subs.submissions = (subs.submissions || []).slice(-600);
subs.submissions.push({ t: clean.t, a: clean.a, b: clean.b || null, pk: clean.pk || null, dimension: anchor || null, frames: clean.k.length, traits, signed: !!clean.sig });
fs.writeFileSync(dir + "/submissions.json", JSON.stringify(subs));
const tok = Buffer.from(JSON.stringify(clean)).toString("base64").replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
fs.writeFileSync("/tmp/submit_result.json", JSON.stringify({ ok: true, title: clean.t, frames: clean.k.length, traits, anchor, dial: "https://kody-w.github.io/rapp-commons/hologram/?m=" + tok }));
console.log("ACCEPT: " + clean.t + " (" + clean.k.length + " frames; traits: " + (traits.join(",") || "none") + (anchor ? "; joins " + anchor : "") + ")");
