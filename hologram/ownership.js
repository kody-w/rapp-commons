/* (c) 2026 Kody Wildfeuer - PolyForm Noncommercial 1.0.0 - part of The RAPP Zoo */
/* ownership — a Moment's rappid is a transferable DEED. Ownership is the tip of a per-rappid, hash-linked
   chain of TRANSFERS: the current owner signs over the rights to the next owner. Anyone (a human OR an
   agent — any keypair is an identity) can own a Moment and send its rights to another rappid. Resolution
   is deterministic and verifiable from the public ledger; the standard underneath doesn't matter, only the
   globally-unique rappid being pointed at. Pure, sync, browser+node. The signature check is injected so
   this stays testable everywhere (the browser injects Web Crypto verify; node a stub or node-crypto). */
(function (root) {
  var Rappid = (typeof module !== "undefined" && module.exports) ? require("./rappid.js") : root.Rappid;

  // the canonical body a transfer is signed over + hashed by (deterministic, field-ordered)
  function transferBody(t) { return ["rappid-transfer/1", t.rappid, t.from, t.to, t.prev, "" + t.ts].join("\n"); }
  function transferHash(t) { return Rappid.sha256(transferBody(t)); }

  // resolve the current owner by walking the owner-authorized, hash-linked transfer chain from the minter.
  // `transfers` MUST already be signature-verified by the caller (verifyTransfer); this enforces the
  // OWNERSHIP rules: each transfer's `from` must equal the then-current owner, and `prev` must hash-link.
  function deedChain(rappid, mintOwner, transfers) {
    var byPrev = {}; (transfers || []).forEach(function (t) { if (t.rappid === rappid && byPrev[t.prev] == null) byPrev[t.prev] = t; });
    var owner = mintOwner, prevH = rappid, history = [{ event: "mint", owner: mintOwner }], guard = 0, t;
    while ((t = byPrev[prevH]) && guard++ < 100000) {
      if (t.from !== owner) break;                       // not authorized by the current owner — chain ends
      if (transferHash(t) !== t.hash) break;             // tampered body — chain ends
      owner = t.to; history.push({ event: "transfer", from: t.from, to: t.to, ts: t.ts, hash: (t.hash || "").slice(0, 12) });
      prevH = t.hash;
    }
    return { owner: owner, ownerRappid: Rappid.ofKeeper(owner), transfers: history.length - 1, history: history, tip: prevH };
  }

  // build (unsigned) a transfer from the current owner to a new owner; caller signs transferBody(t) and
  // attaches sig+pub (pub.x MUST equal `from`).
  function newTransfer(rappid, from, to, prevHash, ts) {
    var t = { v: 1, rappid: rappid, from: from, to: to, prev: prevHash || rappid, ts: ts };
    t.hash = transferHash(t); return t;
  }

  var api = { transferBody: transferBody, transferHash: transferHash, deedChain: deedChain, newTransfer: newTransfer };
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  root.Ownership = api;
})(typeof window !== "undefined" ? window : this);
