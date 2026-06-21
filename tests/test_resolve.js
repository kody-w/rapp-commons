const Rz = require("../hologram/resolve.js"), O = require("../hologram/organism.js"), R = require("../hologram/rappid.js");
let pass = 0, fail = 0; const ok = (n, c, e) => { if (c) pass++; else { fail++; console.log("FAIL:", n, e || ""); } };
const m = O.organismFromStamp(1782078749409); m.t = "Gate Test"; m.sig = "ab"; m.pub = { x: "OWNERkeyXXXX" };
const d = Rz.document(m, { token: "TOK", owner: R.ofKeeper("OWNERkeyXXXX"), transfers: 1, gen: 7 });
// standard NFT / marketplace metadata
ok("has NFT name/description", !!d.name && !!d.description);
ok("animation_url is the LIVE hologram (?dial=)", /\?dial=/.test(d.animation_url), d.animation_url);
ok("external_url present", !!d.external_url);
ok("attributes are trait objects", Array.isArray(d.attributes) && d.attributes.every(a => a.trait_type));
ok("biome + keyframes are traits", d.attributes.some(a => a.trait_type === "Biome") && d.attributes.some(a => a.trait_type === "Keyframes"));
// RAPP Eternity extensions
ok("carries the rappid", /^rappid:moment:[0-9a-f]{64}$/.test(d.rappid));
ok("carries pk + born", d.pk === m.pk && d.born === 1782078749409);
ok("owner is a keeper rappid", /^rappid:keeper:/.test(d.owner));
ok("sig_suite present", d.sig_suite === "ecdsa-p256");
ok("chain reference present", d.chain && /git-blockchain/.test(d.chain.kind));
// the dimension anchor — others join the genesis Commons
ok("anchors to the genesis Commons dimension by default", /^rappid:dimension:/.test(d.dimension), d.dimension);
ok("an explicit dimension overrides", Rz.document(m, { dimension: "rappid:dimension:other" }).dimension === "rappid:dimension:other");
// extensible sources
ok("sources is extensible", Array.isArray(d.sources));
ok("custom sources flow through", Rz.document(m, { sources: [{ rel: "x", href: "y" }] }).sources.length === 1);
// crawler meta for the public marketplace
ok("emits OpenGraph/Twitter player meta", Rz.metaTags(d).some(t => t[0] === "twitter:player"));
console.log(`\nresolve: ${pass}/${pass + fail} passed` + (fail ? "  *** RED ***" : "  ALL GREEN"));
process.exit(fail ? 1 : 0);
