/* (c) 2026 Kody Wildfeuer - PolyForm Noncommercial 1.0.0 - part of The RAPP Zoo */
/* FIDELITY-OVER-TIME — the synthesis. An organism's frames are indexed in time; as real UTC time passes, a
   new frame can fold into the SMALLEST interval it currently tracks (the coarsest gap), deepening fidelity
   between the already-established frames. Each new frame is stamped with the exact UTC instant it arrived
   and sits ON the established trajectory (a hair of new detail) so it can never contradict downstream data
   — it just reconciles in (homeostasis). Run it forever and an organism grows infinitely detailed in time,
   fractally, autonomously, while its birth genesis stays provably intact. Pure, deterministic. */
(function (root) {
  var H = (typeof module !== "undefined" && module.exports) ? require("./homeostasis.js") : root.Homeostasis;
  var FIELDS = ["s", "l", "p", "g", "h", "x", "z"];

  function seeded(n) { var s = n >>> 0; return function () { s = (s + 0x6D2B79F5) | 0; var t = Math.imul(s ^ (s >>> 15), 1 | s); t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t; return ((t ^ (t >>> 14)) >>> 0) / 4294967296; }; }
  function sortK(k) { return (k || []).slice().sort(function (a, b) { return a.at - b.at; }); }

  // the next time to deepen: the midpoint of the coarsest interval the organism currently tracks.
  function nextRefineAt(k) {
    var s = sortK(k), bi = -1, bg = 0;
    for (var i = 0; i < s.length - 1; i++) { var g = s[i + 1].at - s[i].at; if (g > bg) { bg = g; bi = i; } }
    return bi < 0 ? null : { at: (s[bi].at + s[bi + 1].at) / 2, gap: bg };
  }
  function finestResolution(k) { var s = sortK(k), m = 99; for (var i = 0; i < s.length - 1; i++) m = Math.min(m, s[i + 1].at - s[i].at); return s.length < 2 ? 99 : m; }

  // fold one UTC-stamped detail frame into the coarsest gap. It sits on the trajectory + a hair of seeded
  // detail (amplitude shrinks with the gap, so deeper levels add finer detail). reconcile() guarantees no
  // downstream contradiction. utcMs is the exact real instant this fidelity arrived.
  function refineOverTime(organism, utcMs) {
    var nr = nextRefineAt(organism.k);
    if (!nr || nr.gap < 0.02) return { accepted: false, kind: "converged", gap: nr ? nr.gap : 0, organism: organism };
    var base = H.valueAt(organism.k, nr.at), rnd = seeded((Math.floor(utcMs) >>> 0) ^ Math.floor(nr.at * 997)), amp = Math.min(0.03, nr.gap / 99 * 0.06);
    var f = { at: +nr.at.toFixed(6), u: Math.floor(utcMs) };
    FIELDS.forEach(function (k) { if (base[k] == null) return; f[k] = (k === "h") ? (base[k] + (rnd() - 0.5) * amp * 120 + 360) % 360 : +(base[k] + (rnd() - 0.5) * amp * 2).toFixed(4); });
    var r = H.reconcile({ k: organism.k, gen: organism._gen, stress: organism._stress }, f);
    var out = Object.assign({}, organism, { k: r.organism.k, _gen: r.organism.gen, _stress: r.organism.stress });
    return { accepted: r.accepted, kind: r.kind, at: f.at, u: f.u, gap: nr.gap, frames: out.k.length, organism: out };
  }

  // DREAM CATCHER — a frame is only woven into the web if it stays consistent with the two neighbours it
  // sits between (its UTC-adjacent frames, keyed by timestamp): each value must fall within `tol` of the
  // line those neighbours weave. Consistent => caught & reconciled; inconsistent => it would tear the web.
  function weaveCheck(k, frame, tol) {
    tol = tol == null ? 0.12 : tol;
    var s = sortK(k), lo = null, hi = null;
    for (var i = 0; i < s.length; i++) { if (s[i].at <= frame.at) lo = s[i]; if (s[i].at >= frame.at && hi == null) hi = s[i]; }
    if (!lo || !hi || lo === hi) return { ok: true };
    var span = (hi.at - lo.at) || 1, t = (frame.at - lo.at) / span, worst = 0, wf = null;
    FIELDS.forEach(function (f) {
      if (frame[f] == null || lo[f] == null || hi[f] == null) return;
      var interp = (f === "h") ? (lo[f] + (((hi[f] - lo[f] + 540) % 360) - 180) * t + 360) % 360 : lo[f] + (hi[f] - lo[f]) * t;
      var d = Math.abs(frame[f] - interp); if (f === "h") d = Math.min(d, 360 - d) / 180;
      if (d > worst) { worst = d; wf = f; }
    });
    return { ok: worst <= tol, deviation: +worst.toFixed(3), field: wf };
  }
  function weaveFrame(organism, frame, tol) {
    var w = weaveCheck(organism.k, frame, tol);
    if (!w.ok) return { woven: false, reason: "tears the web at " + w.field + " (Δ" + w.deviation + ")", organism: organism };
    var r = H.reconcile({ k: organism.k, gen: organism._gen, stress: organism._stress }, frame);
    var out = Object.assign({}, organism, { k: r.organism.k, _gen: r.organism.gen, _stress: r.organism.stress });
    return { woven: r.accepted, kind: r.kind, organism: out };
  }

  var api = { refineOverTime: refineOverTime, nextRefineAt: nextRefineAt, finestResolution: finestResolution, weaveCheck: weaveCheck, weaveFrame: weaveFrame };
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  root.Fidelity = api;
})(typeof window !== "undefined" ? window : this);
