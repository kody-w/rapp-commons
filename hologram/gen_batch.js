#!/usr/bin/env node
/* gen_batch <now_ms> <count> <gap_ms> -> JSON array of the organisms minted at now, now-gap, now-2gap … */
const O = require("./organism.js");
const now = parseInt(process.argv[2] || "0", 10), count = parseInt(process.argv[3] || "60", 10), gap = parseInt(process.argv[4] || "1000", 10);
const out = []; for (let i = 0; i < count; i++) out.push(O.organismFromStamp(now - i * gap));
process.stdout.write(JSON.stringify(out));
