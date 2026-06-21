/* (c) 2026 Kody Wildfeuer - PolyForm Noncommercial 1.0.0 - part of The RAPP Zoo */
/* HOMEOSTASIS — an organism's keyframes are its life-trajectory. Frames can be refined into UNLIMITED
   fractal detail (insert between any two), but an incoming frame may NEVER contradict data already
   established DOWNSTREAM (a settled later keyframe). Consistent frames are absorbed and the organism
   lives on; contradictions are RESISTED — and it can only resist so long before homeostasis breaks,
   just like a creature trying to survive in its environment. Pure, drop-in, no deps. */
(function (root) {
  var FIELDS = ["s", "l", "p", "g", "h", "x", "z"];
  var EPS = { s: 0.04, l: 0.04, p: 0.06, g: 0.05, h: 8, x: 0.06, z: 0.06 }; // per-field homeostatic tolerance
  var STRESS_LIMIT = 12;                                                    // contradictions it can resist before it breaks

  function sortK(k) { return (k || []).slice().sort(function (a, b) { return a.at - b.at; }); }

  // do two frames sharing a moment disagree beyond what homeostasis tolerates?
  function contradicts(a, b) {
    return FIELDS.some(function (f) {
      if (a[f] == null || b[f] == null) return false;
      var d = Math.abs(a[f] - b[f]);
      if (f === "h") d = Math.min(d, 360 - d);
      return d > EPS[f];
    });
  }

  // the organism's current trajectory value at any (possibly fractional) time
  function valueAt(k, at) {
    var s = sortK(k); if (!s.length) return null;
    if (at <= s[0].at) return s[0];
    if (at >= s[s.length - 1].at) return s[s.length - 1];
    for (var i = 0; i < s.length - 1; i++) {
      if (at >= s[i].at && at <= s[i + 1].at) {
        var span = (s[i + 1].at - s[i].at) || 1, t = (at - s[i].at) / span, o = { at: at };
        FIELDS.forEach(function (f) {
          var a = s[i][f], b = s[i + 1][f];
          if (a == null) o[f] = b; else if (b == null) o[f] = a;
          else if (f === "h") { var dd = ((b - a + 540) % 360) - 180; o[f] = (a + dd * t + 360) % 360; }
          else o[f] = a + (b - a) * t;
        });
        return o;
      }
    }
    return s[s.length - 1];
  }

  function norm(f) { var o = { at: f.at }; FIELDS.forEach(function (x) { if (f[x] != null) o[x] = f[x]; }); if (f.u != null) o.u = f.u; return o; }   // preserve a frame's UTC arrival stamp

  // reconcile an incoming frame. Returns {accepted, survives, kind, organism}.
  //  kind: "refined" (new fractal detail), "redundant" (nothing changed), "resisted" (downstream contradiction).
  function reconcile(organism, frame) {
    var s = sortK(organism.k), out = Object.assign({}, organism, { k: s.slice() });
    out.gen = organism.gen != null ? organism.gen : s.length;
    out.stress = organism.stress || 0;
    var hit = s.find(function (kf) { return Math.abs(kf.at - frame.at) < 0.001; });
    if (hit) {
      if (!contradicts(hit, frame)) return done(out, false, "redundant");   // nothing changed — absorbed, lives on
      out.stress += 1;                                                       // would rewrite a settled frame — RESIST
      out.alive = out.stress < STRESS_LIMIT;
      return { accepted: false, survives: out.alive, kind: "resisted", organism: out };
    }
    out.k.push(norm(frame)); out.k = sortK(out.k); out.gen += 1;            // new fractal detail, downstream untouched
    return done(out, true, "refined");
  }

  function done(out, accepted, kind) {
    out.alive = (out.stress || 0) < STRESS_LIMIT;
    return { accepted: accepted, survives: out.alive, kind: kind, organism: out };
  }

  function homeostasis(organism) {
    var s = sortK(organism.k), stress = organism.stress || 0, stable = true;
    for (var i = 0; i < s.length - 1; i++)   // a same-time collision is only an injury if a GROWN frame caused it; two genesis frames sharing an `at` is the legitimate birth genome
      if (Math.abs(s[i].at - s[i + 1].at) < 1e-6 && (s[i].u != null || s[i + 1].u != null) && contradicts(s[i], s[i + 1])) stable = false;
    var alive = stable && stress < STRESS_LIMIT;
    return { alive: alive, stable: stable, generation: organism.gen != null ? organism.gen : s.length,
             frames: s.length, stress: stress, vitality: Math.max(0, 1 - stress / STRESS_LIMIT) };
  }

  var api = { reconcile: reconcile, homeostasis: homeostasis, valueAt: valueAt, contradicts: contradicts, STRESS_LIMIT: STRESS_LIMIT };
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  root.Homeostasis = api;
})(typeof window !== "undefined" ? window : this);
