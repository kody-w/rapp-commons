#!/usr/bin/env node
/* gen_organism <utc_ms> [lat] [lng] [place] -> prints the one organism that spacetime coordinate mints. */
const O = require("./organism.js");
const ms = parseInt(process.argv[2] || "0", 10);
const lat = process.argv[3], lng = process.argv[4], place = process.argv[5];
const loc = (lat !== undefined && lat !== "") ? { lat: parseFloat(lat), lng: parseFloat(lng), place: place || "" } : null;
process.stdout.write(JSON.stringify(O.organismFromStamp(ms, loc)));
