/* (c) 2026 Kody Wildfeuer - PolyForm Noncommercial 1.0.0 - part of The RAPP Zoo */
/* FINGERPRINT — score a whole hologram into one fixed vector by sampling its entire 100-frame trajectory
   (every field of every frame — the generative equivalent of scoring every pixel). Then rank a static,
   ever-growing warehouse of these vectors entirely client-side (the Simon Willison free-data-warehouse
   pattern: data is static files on a CDN, the query runs in the browser). Pure, deterministic, no deps. */
(function (root) {
  var LIN = ["s", "l", "p", "g", "x", "z"];          // linear fields; hue (h) handled circularly

  function sortK(k) { return (k || []).slice().sort(function (a, b) { return a.at - b.at; }); }
  function sampleAt(s, at) {
    if (!s.length) return {};
    if (at <= s[0].at) return s[0];
    if (at >= s[s.length - 1].at) return s[s.length - 1];
    for (var i = 0; i < s.length - 1; i++) {
      if (at >= s[i].at && at <= s[i + 1].at) {
        var t = (at - s[i].at) / ((s[i + 1].at - s[i].at) || 1), o = {};
        LIN.forEach(function (f) { var a = s[i][f] || 0, b = s[i + 1][f] || 0; o[f] = a + (b - a) * t; });
        var ha = s[i].h || 0, hb = s[i + 1].h || 0, dd = ((hb - ha + 540) % 360) - 180; o.h = (ha + dd * t + 360) % 360;
        return o;
      }
    }
    return s[s.length - 1];
  }
  function expand(moment, N) { var s = sortK(moment.k), o = []; for (var i = 0; i < N; i++) o.push(sampleAt(s, i / (N - 1) * 99)); return o; }
  function mean(a) { var s = 0; for (var i = 0; i < a.length; i++) s += a[i]; return s / (a.length || 1); }
  function std(a, m) { return Math.sqrt(mean(a.map(function (x) { return (x - m) * (x - m); }))); }

  // per-field [mean,std,range] scales so every dimension lands in a comparable unit (portable across the warehouse).
  var SC = { s: [1, 0.5, 1], l: [1, 0.5, 1], p: [1, 0.5, 1], g: [1, 0.5, 1], x: [1, 0.7, 2], z: [1, 0.7, 2] };

  // a ~40-dim descriptor: per-field {mean,std,range}, an 8-bin hue histogram + circular mean, and motion energy.
  function fingerprint(moment) {
    var N = 100, fr = expand(moment, N), v = [];
    LIN.forEach(function (f) { var xs = fr.map(function (x) { return x[f] || 0; }); var m = mean(xs), sc = SC[f];
      v.push(m / sc[0], std(xs, m) / sc[1], (Math.max.apply(null, xs) - Math.min.apply(null, xs)) / sc[2]); });
    var hb = [0, 0, 0, 0, 0, 0, 0, 0];
    fr.forEach(function (x) { hb[Math.floor(((x.h || 0) % 360) / 45) % 8] += 1 / N; });
    v.push.apply(v, hb);
    v.push(mean(fr.map(function (x) { return Math.sin((x.h || 0) * Math.PI / 180); })), mean(fr.map(function (x) { return Math.cos((x.h || 0) * Math.PI / 180); })));
    var path = 0, jerk = 0;
    for (var i = 1; i < N; i++) path += Math.hypot(fr[i].x - fr[i - 1].x, fr[i].z - fr[i - 1].z);
    for (var j = 2; j < N; j++) jerk += Math.abs(fr[j].s - 2 * fr[j - 1].s + fr[j - 2].s);
    v.push(path / 5, jerk / 2, mean(fr.map(function (x) { return x.g || 0; })), mean(fr.map(function (x) { return x.p || 0; })));
    return v.map(function (x) { return +x.toFixed(4); });
  }

  function fpOf(it) { return it.fp || fingerprint(it); }

  // rank `items` by similarity to `target` via Euclidean distance over the scaled fingerprints. score = 1/(1+dist).
  // Each fingerprint is absolute (fixed scales), so this works pairwise AND across the whole ever-growing warehouse.
  function rank(target, items) {
    var tf = fpOf(target);
    return items.map(function (it) {
      var f = fpOf(it), s = 0; for (var d = 0; d < tf.length; d++) { var dd = (f[d] || 0) - (tf[d] || 0); s += dd * dd; }
      var dist = Math.sqrt(s);
      return Object.assign({}, it, { score: +(1 / (1 + dist)).toFixed(4), dist: +dist.toFixed(4) });
    }).sort(function (a, b) { return a.dist - b.dist; });
  }

  function similar(a, b) { return rank({ fp: fpOf(a) }, [{ fp: fpOf(b) }])[0].score; }

  var api = { fingerprint: fingerprint, rank: rank, similar: similar, expand: expand };
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  root.Fingerprint = api;
})(typeof window !== "undefined" ? window : this);
