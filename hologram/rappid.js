/* (c) 2026 Kody Wildfeuer - PolyForm Noncommercial 1.0.0 - part of The RAPP Zoo */
/* rappid — bridge a Moment into the RAPP Eternity Standard: the canonical id is rappid:<slug>:<64hex>,
   256-bit, keypair-bound. A Moment's eternal address is its spacetime pk; its rappid is the ecosystem-
   canonical form: rappid:moment:<sha256("moment:"+pk)>. Deterministic + eternal (the pk is eternal).
   COMPATIBILITY CONTRACT: read ALL legacy forms forever (pk, bare UTC ms, '|' separator), emit ONLY
   canonical; the 64-hex hash is the join key; NEVER version the string — add record fields instead.
   Pure, sync, browser+node. */
(function (root) {
  // compact, self-contained SHA-256 (ascii input; callers UTF-8 encode first)
  function sha256(ascii) {
    function rr(v, a) { return (v >>> a) | (v << (32 - a)); }
    var mp = Math.pow, mw = mp(2, 32), out = "", words = [], bits = ascii.length * 8;
    var h = sha256.h = sha256.h || [], k = sha256.k = sha256.k || [], pc = k.length, comp = {};
    for (var cand = 2; pc < 64;) {
      if (!comp[cand]) { for (var i = 0; i < 313; i += cand) comp[i] = cand; h[pc] = (mp(cand, .5) * mw) | 0; k[pc++] = (mp(cand, 1 / 3) * mw) | 0; }
      cand++;
    }
    ascii += "\x80"; while (ascii.length % 64 - 56) ascii += "\x00";
    for (i = 0; i < ascii.length; i++) { var j = ascii.charCodeAt(i); if (j >> 8) return null; words[i >> 2] |= j << ((3 - i) % 4) * 8; }
    words[words.length] = (bits / mw) | 0; words[words.length] = bits | 0;
    var hash = h.slice(0);
    for (j = 0; j < words.length;) {
      var w = words.slice(j, j += 16), oh = hash.slice(0);
      for (i = 0; i < 64; i++) {
        var w15 = w[i - 15], w2 = w[i - 2], a = hash[0], e = hash[4];
        var t1 = (hash[7] + (rr(e, 6) ^ rr(e, 11) ^ rr(e, 25)) + ((e & hash[5]) ^ ((~e) & hash[6])) + k[i] +
          (w[i] = i < 16 ? (w[i] | 0) : (w[i - 16] + (rr(w15, 7) ^ rr(w15, 18) ^ (w15 >>> 3)) + w[i - 7] + (rr(w2, 17) ^ rr(w2, 19) ^ (w2 >>> 10))) | 0)) | 0;
        var t2 = ((rr(a, 2) ^ rr(a, 13) ^ rr(a, 22)) + ((a & hash[1]) ^ (a & hash[2]) ^ (hash[1] & hash[2]))) | 0;
        hash = [(t1 + t2) | 0].concat(hash); hash[4] = (hash[4] + t1) | 0;
      }
      for (i = 0; i < 8; i++) hash[i] = (hash[i] + oh[i]) | 0;
    }
    for (i = 0; i < 8; i++) for (j = 3; j + 1; j--) { var b = (hash[i] >> (j * 8)) & 255; out += ((b < 16) ? 0 : "") + b.toString(16); }
    return out;
  }
  function hex(s) { return sha256(unescape(encodeURIComponent(s))); }   // sha256 of the UTF-8 bytes

  function ofMoment(pk) { return pk ? "rappid:moment:" + hex("moment:" + pk) : null; }
  function ofKeeper(pubx) { return pubx ? "rappid:keeper:" + hex("keeper:" + pubx) : null; }
  function parse(s) { var m = /^rappid:([a-z0-9-]+):([0-9a-f]{64})$/.exec((s || "").trim()); return m ? { scheme: "rappid", slug: m[1], hex: m[2] } : null; }

  // read any legacy identity form -> the canonical rappid (the eternity compatibility contract)
  function canonicalize(any) {
    if (typeof any !== "string") return null; any = any.trim();
    if (parse(any)) return any;                                   // already canonical
    if (/·\d+$/.test(any) || /\|\d+$/.test(any)) return ofMoment(any.replace("|", "·"));   // a spacetime pk
    if (/^\d{10,}$/.test(any)) return ofMoment("sky·" + any);     // a bare UTC ms
    return null;
  }

  var api = { ofMoment: ofMoment, ofKeeper: ofKeeper, parse: parse, canonicalize: canonicalize, sha256: hex, SIG_SUITE: "ecdsa-p256" };
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  root.Rappid = api;
})(typeof window !== "undefined" ? window : this);
