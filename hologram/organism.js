/* (c) 2026 Kody Wildfeuer - PolyForm Noncommercial 1.0.0 - part of The RAPP Zoo */
/* ORGANISM-FROM-SPACETIME — an organism's PRIMARY KEY is a point in spacetime: an exact UTC millisecond,
   optionally bound to a real-world location (geohash, Pokémon-GO style). That coordinate IS its DNA — it
   deterministically mints one globally-unique organism, and anyone can regenerate it from the key to verify.
   One coordinate => one global master record (a snapshot in time hosted as static data). You OWN that moment
   by signing it. Pure, deterministic, no deps. */
(function (root) {
  var BIOMES = ["savanna", "canyon", "forest", "volcanic", "void"];
  var B32 = "0123456789bcdefghjkmnpqrstuvwxyz";

  function seeded(n) { var s = n >>> 0; return function () { s = (s + 0x6D2B79F5) | 0; var t = Math.imul(s ^ (s >>> 15), 1 | s); t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t; return ((t ^ (t >>> 14)) >>> 0) / 4294967296; }; }
  function hashStr(str) { var h = 0x811c9dc5; for (var i = 0; i < str.length; i++) { h ^= str.charCodeAt(i); h = Math.imul(h, 0x01000193); } return h >>> 0; }

  // standard base32 geohash — nearby points share a prefix, so a "place" is a stable cell (Pokémon-GO style)
  function geohash(lat, lng, prec) {
    var idx = 0, bit = 0, even = true, hash = "", latR = [-90, 90], lngR = [-180, 180];
    while (hash.length < prec) {
      var mid;
      if (even) { mid = (lngR[0] + lngR[1]) / 2; if (lng >= mid) { idx = idx * 2 + 1; lngR[0] = mid; } else { idx = idx * 2; lngR[1] = mid; } }
      else { mid = (latR[0] + latR[1]) / 2; if (lat >= mid) { idx = idx * 2 + 1; latR[0] = mid; } else { idx = idx * 2; latR[1] = mid; } }
      even = !even; if (++bit === 5) { hash += B32[idx]; bit = 0; idx = 0; }
    }
    return hash;
  }

  // the spacetime primary key: a place+time cell, or "sky·<ms>" for a pure-time drop.
  function pkFor(ms, loc) { ms = Math.floor(ms); return (loc && loc.lat != null) ? geohash(loc.lat, loc.lng, 9) + "·" + ms : "sky·" + ms; }

  function build(pk) {
    var rnd = seeded(hashStr(pk)), rng = function (a, b) { return a + rnd() * (b - a); }, r3 = function (a, b) { return +rng(a, b).toFixed(3); };
    var b = BIOMES[Math.floor(rnd() * BIOMES.length)], nK = 3 + Math.floor(rnd() * 3), k = [];
    for (var i = 0; i < nK; i++) k.push({ at: (i === 0 ? 0 : i === nK - 1 ? 99 : Math.round(rng(14, 86))),
      s: r3(0.12, 0.92), l: r3(0.10, 0.85), p: r3(0, 1), g: r3(0.12, 1), h: Math.round(rng(0, 360)), x: r3(-0.6, 0.6), z: r3(-0.6, 0.6) });
    k.sort(function (a, c) { return a.at - c.at; }); k[0].at = 0; k[k.length - 1].at = 99;
    return { v: 1, b: b, k: k };
  }

  // mint the one organism that this spacetime coordinate produces.
  function organismFromStamp(ms, loc) {
    ms = Math.floor(ms); var pk = pkFor(ms, loc), o = build(pk);
    o.pk = pk; o.born = ms; o.t = nameFromPk(pk);
    if (loc && loc.lat != null) { o.a = "@place"; o.loc = { lat: +(+loc.lat).toFixed(5), lng: +(+loc.lng).toFixed(5), place: loc.place || "" }; }
    else o.a = "@time";
    return o;
  }

  function nameFromPk(pk) {
    var rnd = seeded(hashStr(pk) ^ 0x5bd1e995), C = "BCDFGHJKLMNPQRSTVWXZ", V = "AEIOU", S = "0123456789ACDEFHJKMNPRTVWXY";
    var p = function (set) { return set[Math.floor(rnd() * set.length)]; };
    return p(C) + p(V) + p(C) + p(V) + p(C) + "-" + p(S) + p(S) + p(S);
  }

  // regenerate from a record and confirm the organism truly is the one its coordinate mints. The genesis
  // frames (no `u` stamp) must match the mint exactly; fidelity frames grown in over time (UTC-stamped `u`)
  // are additive detail and are excluded — so an organism can grow forever without breaking its birth proof.
  function verifyCoordinate(org) {
    if (!org || org.born == null) return false;
    var re = organismFromStamp(org.born, org.loc);
    var genesis = (org.k || []).filter(function (f) { return f.u == null; });
    return re.pk === org.pk && re.b === org.b && JSON.stringify(genesis) === JSON.stringify(re.k);
  }

  function geohashDecode(hash) {
    var even = true, latR = [-90, 90], lngR = [-180, 180];
    for (var i = 0; i < hash.length; i++) { var c = B32.indexOf(hash[i]); if (c < 0) return null;
      for (var b = 4; b >= 0; b--) { var bit = (c >> b) & 1;
        if (even) { var m1 = (lngR[0] + lngR[1]) / 2; if (bit) lngR[0] = m1; else lngR[1] = m1; }
        else { var m2 = (latR[0] + latR[1]) / 2; if (bit) latR[0] = m2; else latR[1] = m2; }
        even = !even; } }
    return { lat: (latR[0] + latR[1]) / 2, lng: (lngR[0] + lngR[1]) / 2 };
  }

  // DIAL — resolve an address (pk) back into its organism. Because the organism is deterministic from its
  // coordinate, dialing regenerates it anywhere it is requested from — the address summons the hologram.
  function fromPk(pk) {
    if (!pk || typeof pk !== "string") return null;
    pk = pk.trim();
    var dot = pk.indexOf("·") >= 0 ? "·" : (pk.indexOf("|") >= 0 ? "|" : null);   // tolerate · or | as the separator
    if (!dot) { var n = parseInt(pk, 10); return (n && ("" + n).length >= 10) ? organismFromStamp(n) : null; }  // bare UTC ms
    var parts = pk.split(dot), ms = parseInt(parts[1], 10); if (!ms) return null;
    if (parts[0] === "sky") return organismFromStamp(ms);
    var loc = geohashDecode(parts[0]); return loc ? organismFromStamp(ms, loc) : null;
  }

  var api = { organismFromStamp: organismFromStamp, fromPk: fromPk, pkFor: pkFor, geohash: geohash, geohashDecode: geohashDecode, nameFromPk: nameFromPk, verifyCoordinate: verifyCoordinate, BIOMES: BIOMES };
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  root.Organism = api;
})(typeof window !== "undefined" ? window : this);
