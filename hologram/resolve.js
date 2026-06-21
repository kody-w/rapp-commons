/* (c) 2026 Kody Wildfeuer - PolyForm Noncommercial 1.0.0 - part of The RAPP Zoo */
/* resolve — a Moment's rappid is a GATEWAY. Resolving it produces ONE standard, machine-readable document
   that any system — inside or outside this ecosystem, including public NFT marketplaces — can fetch to
   render, verify, extend, and trade the Moment. The document is ERC-721/OpenSea-metadata-compatible
   (name/description/image/animation_url/external_url/attributes), so `animation_url` makes the *live
   walkable hologram* embed directly in a marketplace, AND it carries the RAPP Eternity extensions (rappid,
   pk, owner deed, chain, sig_suite) plus an extensible `sources` array — the tie-in to other sources that
   continues the dimension into any system. Pure, browser+node. */
(function (root) {
  var Rappid = (typeof module !== "undefined" && module.exports) ? require("./rappid.js") : root.Rappid;
  var BASE = "https://kody-w.github.io/rapp-commons/hologram/";
  // the genesis dimension: the RAPP Commons, the first organism to make contact with time (its genesis commit).
  // Every Moment is a dimension born of its own instant; by default it anchors to (joins) this one.
  var COMMONS_DIMENSION = "rappid:dimension:0c0ba7d21766be26e61700893fd94";

  function document(m, opts) {
    opts = opts || {}; var base = opts.base || BASE;
    var rid = Rappid.ofMoment(m.pk), dial = base + "?dial=" + encodeURIComponent(m.pk);
    var frames = (m.k || []).length, bornISO = m.born ? new Date(m.born).toISOString() : null;
    var attrs = [
      { trait_type: "Biome", value: m.b || "savanna" },
      { trait_type: "Keyframes", value: frames },
      { trait_type: "Signed", value: !!m.sig },
      { trait_type: "Domain", value: (m.pk || "").indexOf("sky·") === 0 ? "time" : "place" }
    ];
    if (bornISO) attrs.push({ trait_type: "Born (UTC)", value: bornISO });
    if (m.born) attrs.push({ display_type: "date", trait_type: "Minted", value: Math.floor(m.born / 1000) });
    if (opts.gen != null) attrs.push({ trait_type: "Generation", value: opts.gen });

    return {
      "@context": base + "../MOMENT_SPEC.md", "@type": "rappid:moment", "$schema": "erc721-metadata-compatible",
      // --- standard NFT / marketplace metadata ---
      name: m.t || "Moment",
      description: "A living holographic Moment — 100 frames, one heartbeat each" + (bornISO ? ", born of the exact instant " + bornISO : "") + ". Provably yours, on a serverless git-blockchain. " + dial,
      image: opts.image || (base + "poster.png"),
      animation_url: dial,            // marketplaces embed this → the actual walkable hologram renders in-place
      external_url: dial,
      attributes: attrs,
      // --- RAPP Eternity extensions ---
      rappid: rid,
      pk: m.pk,
      born: m.born || null,
      owner: opts.owner || ((m.pub && m.pub.x) ? Rappid.ofKeeper(m.pub.x) : null),   // deed-resolved current owner (rappid:keeper)
      transfers: opts.transfers || 0,
      sig_suite: m.sig_suite || "ecdsa-p256",
      chain: { repo: "kody-w/rapp-commons", kind: "git-blockchain", validator: base + "lineage/chain.json" },
      dial: dial,
      moment_token: opts.token || null,                 // the inline self-contained Moment (?m=…) — render with zero lookup
      sources: opts.sources || [],                      // EXTENSIBLE: external references the owner ties in (continue the dimension)
      dimension: opts.dimension || COMMONS_DIMENSION,   // the dimension this Moment joins (the genesis Commons by default)
      spec: base + "../MOMENT_SPEC.md"
    };
  }

  // OpenGraph / Twitter-card meta tags so social + marketplace crawlers index a gateway page
  function metaTags(doc) {
    return [
      ["og:title", doc.name], ["og:description", "A living holographic Moment — provably yours on a git-blockchain."],
      ["og:type", "website"], ["og:image", doc.image], ["og:url", doc.external_url],
      ["og:video", doc.animation_url], ["twitter:card", "player"], ["twitter:player", doc.animation_url],
      ["moment:rappid", doc.rappid], ["moment:owner", doc.owner || ""]
    ];
  }

  var api = { document: document, metaTags: metaTags, BASE: BASE };
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  root.Resolve = api;
})(typeof window !== "undefined" ? window : this);
