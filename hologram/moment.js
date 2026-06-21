/* (c) 2026 Kody Wildfeuer - PolyForm Noncommercial 1.0.0, see /LICENSE - noncommercial use only - "Holographic Moments" is a trademark. */
/* Holographic Moments — one engine, three modes (feed / create / play). A MOMENT is a deterministic
   100-frame sequence: a few keyframes of a FORM {size,legs,spikes,glow,hue,x,z} interpolated to 100
   frames and played as a walkable hologram. Serverless: a Moment encodes to base64 in the URL and
   streams nowhere — it IS the link. Shareable by URL + QR. THREE r128 + qrcodejs from CDN. */
(function () {
  "use strict";
  var W = window, D = document;
  var THREE = W.THREE;

  // ---- 3D world ----
  var canvas = D.getElementById("c");
  var renderer = new THREE.WebGLRenderer({ canvas: canvas, antialias: true });
  renderer.setPixelRatio(Math.min(W.devicePixelRatio, 2)); renderer.setSize(W.innerWidth, W.innerHeight);
  var scene = new THREE.Scene();
  var camera = new THREE.PerspectiveCamera(58, W.innerWidth / W.innerHeight, 0.1, 600);
  scene.add(new THREE.AmbientLight(0xffffff, 0.8));
  var sun = new THREE.DirectionalLight(0xfff2d6, 1.1); sun.position.set(10, 20, 8); scene.add(sun);
  var ground = new THREE.Mesh(new THREE.CircleGeometry(80, 64), new THREE.MeshStandardMaterial({ color: 0x35562a, roughness: 1 }));
  ground.rotateX(-Math.PI / 2); scene.add(ground);
  var flora = new THREE.Group(); scene.add(flora);

  var BIOMES = {
    savanna: { g: 0x35562a, sky: 0x9fc6e8, fog: 0x9fc6e8, fl: 0x6fae4a },
    canyon: { g: 0x6b4a26, sky: 0xe6c089, fog: 0xd8b27a, fl: 0x8a6a3a },
    forest: { g: 0x142436, sky: 0x123244, fog: 0x1f5f6e, fl: 0x35e0c0 },
    volcanic: { g: 0x2a1414, sky: 0x3a1414, fog: 0x6a1f1f, fl: 0x7f1d1d },
    void: { g: 0x0a0a12, sky: 0x05060a, fog: 0x0a0a16, fl: 0x222a3a }
  };
  function setBiome(b) {
    var P = BIOMES[b] || BIOMES.savanna;
    scene.background = new THREE.Color(P.sky); scene.fog = new THREE.Fog(P.fog, 30, 120); ground.material.color.setHex(P.g);
    scene.remove(flora); flora = new THREE.Group(); scene.add(flora);
    for (var i = 0; i < 46; i++) {
      var a = (i * 137.5) * Math.PI / 180, r = 6 + (i % 9) * 5;
      var m = new THREE.Mesh(new THREE.ConeGeometry(0.35, 1.4 + (i % 3) * 0.5, 6),
        new THREE.MeshStandardMaterial({ color: P.fl, roughness: 0.9, emissive: b === "forest" ? P.fl : 0, emissiveIntensity: b === "forest" ? 0.5 : 0 }));
      m.position.set(Math.cos(a) * r, 0.8, Math.sin(a) * r); flora.add(m);
    }
  }

  var FORM = null, FORM_T = 0;
  function hsl(h) { var c = new THREE.Color(); c.setHSL(((h % 360) + 360) % 360 / 360, 0.72, 0.56); return c; }
  function buildForm(f) {
    var keepP = FORM ? FORM.position.clone() : null, keepR = FORM ? FORM.rotation.y : 0;
    if (FORM) scene.remove(FORM);
    var col = hsl(f.h), size = 0.8 + f.s * 1.9, legLen = 0.35 + f.l * 1.9, bodyY = legLen + size * 0.5;
    var g = new THREE.Group();
    var mat = new THREE.MeshStandardMaterial({ color: col, roughness: 0.5, metalness: 0.1, emissive: col, emissiveIntensity: 0.25 + f.g * 0.7 });
    var body = new THREE.Mesh(new THREE.BoxGeometry(size * 1.7, size, size * 1.1), mat); body.position.y = bodyY; g.add(body);
    var lt = new THREE.PointLight(col, 0.6 + f.g * 2.2, 22); lt.position.set(0, bodyY + 1.2, 0); g.add(lt);
    var head = new THREE.Mesh(new THREE.BoxGeometry(size * 0.75, size * 0.75, size * 0.75), mat); head.position.set(size * 1.05, bodyY + size * 0.25, 0); g.add(head);
    [-0.22, 0.22].forEach(function (dz) { var e = new THREE.Mesh(new THREE.SphereGeometry(0.1, 8, 8), new THREE.MeshStandardMaterial({ color: 0xffffff, emissive: 0xffe08a, emissiveIntensity: 1.3 })); e.position.set(size * 1.45, bodyY + size * 0.35, dz * size); g.add(e); });
    [[-0.55, -0.42], [-0.55, 0.42], [0.55, -0.42], [0.55, 0.42]].forEach(function (p) { var leg = new THREE.Mesh(new THREE.CylinderGeometry(0.12, 0.14, legLen, 6), mat); leg.position.set(p[0] * size, legLen / 2, p[1] * size); g.add(leg); });
    var ns = Math.round(f.p * 8);
    for (var i = 0; i < ns; i++) { var sp = new THREE.Mesh(new THREE.ConeGeometry(0.14, 0.4 + f.p * 0.6, 5), new THREE.MeshStandardMaterial({ color: col, emissive: col, emissiveIntensity: 0.5 })); sp.position.set(((i + 0.5) / ns - 0.5) * size * 1.2, bodyY + size * 0.55, 0); g.add(sp); }
    g.position.set(f.x * 12, 0, f.z * 12);
    if (keepP) { g.position.y = keepP.y; g.rotation.y = keepR; }
    scene.add(g); FORM = g; FORM.bodyY = bodyY; FORM.cur = f;
  }

  // ---- Moment format ----
  function clampF(f) { return { at: f.at | 0, s: +f.s, l: +f.l, p: +f.p, g: +f.g, h: +f.h, x: +f.x, z: +f.z }; }
  function lerp(a, b, t) { return a + (b - a) * t; }
  function lerpF(a, b, t) { return { s: lerp(a.s, b.s, t), l: lerp(a.l, b.l, t), p: lerp(a.p, b.p, t), g: lerp(a.g, b.g, t), h: lerp(a.h, b.h, t), x: lerp(a.x, b.x, t), z: lerp(a.z, b.z, t) }; }
  function expand(moment) {
    var k = (moment.k || []).map(clampF).sort(function (a, b) { return a.at - b.at; });
    if (!k.length) k = [{ at: 0, s: .35, l: .4, p: 0, g: .45, h: 140, x: 0, z: 0 }];
    if (k.length === 1) k = [Object.assign({}, k[0], { at: 0 }), Object.assign({}, k[0], { at: 99 })];
    var out = [];
    for (var i = 0; i < 100; i++) {
      var lo = k[0], hi = k[k.length - 1];
      for (var j = 0; j < k.length; j++) { if (k[j].at <= i) lo = k[j]; if (k[j].at >= i) { hi = k[j]; break; } }
      var t = hi.at === lo.at ? 0 : (i - lo.at) / (hi.at - lo.at);
      out.push(lerpF(lo, hi, t));
    }
    return out;
  }
  function encode(m) { return btoa(unescape(encodeURIComponent(JSON.stringify(m)))).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, ""); }
  function decode(s) { try { s = s.replace(/-/g, "+").replace(/_/g, "/"); return JSON.parse(decodeURIComponent(escape(atob(s)))); } catch (e) { return null; } }

  // ---- playback state ----
  var S = { mode: "feed", moment: null, frames: null, pf: 0, playing: true, dur: 14, lastBuild: 0, t0: perf() };
  function perf() { return W.performance.now() / 1000; }
  function applyFrame(pf, force) {
    if (!S.frames) return;
    var i = Math.max(0, Math.min(99, Math.floor(pf))), f = pf - i;
    var fr = lerpF(S.frames[i], S.frames[Math.min(99, i + 1)], f);
    if (force || (S.t - S.lastBuild > 0.09)) { buildForm(fr); S.lastBuild = S.t; }
  }
  function loadMoment(m) { S.moment = m; S.frames = expand(m); setBiome(m.b || "savanna"); S.pf = 0; S.lastBuild = -9; applyFrame(0, true); cur.set(FORM.position.x, 8, FORM.position.z + 15); }

  // ---- camera ----
  var cur = new THREE.Vector3(14, 8, 14), look = new THREE.Vector3(0, 1.5, 0);
  function camTick(dt) {
    var c = FORM ? FORM.position : new THREE.Vector3(), by = FORM ? FORM.bodyY : 1.5;
    var ang = S.t * 0.32, r = 6.6 + Math.sin(S.t * 0.5) * 1.8;
    var pos = new THREE.Vector3(c.x + Math.cos(ang) * r, by * 0.6 + 2 + Math.sin(S.t * 0.4) * 1.1, c.z + Math.sin(ang) * r);
    var k = 1 - Math.pow(0.02, dt);
    cur.lerp(pos, k); look.lerp(new THREE.Vector3(c.x, by * 0.6, c.z), k);
    camera.position.copy(cur); camera.lookAt(look);
  }

  // ---- main loop ----
  var last = perf();
  function tick() {
    var now = perf(), dt = Math.min(now - last, 0.05); last = now; S.t = now;
    if ((S.mode === "play" || S.mode === "create") && S.frames) {
      if (S.mode === "play" && S.playing) { S.pf += dt * (99 / S.dur); if (S.pf >= 99) S.pf = 0; }
      if (FORM) FORM.position.y = Math.abs(Math.sin(now * 5)) * 0.1;
      applyFrame(S.pf, false);
      camTick(dt);
      if (S.mode === "play") updatePC();
    } else { camera.position.set(0, 6, 16); camera.lookAt(0, 1, 0); }
    renderer.render(scene, camera); requestAnimationFrame(tick);
  }

  // ---- UI helpers ----
  function $(id) { return D.getElementById(id); }
  function show(id) { $(id).classList.remove("hide"); } function hide(id) { $(id).classList.add("hide"); }
  W.hide = hide;
  function toast(msg) { var t = D.createElement("div"); t.className = "toast"; t.textContent = msg; D.body.appendChild(t); setTimeout(function () { t.remove(); }, 1800); }

  function go(mode) {
    S.mode = mode;
    ["feed", "create", "pc", "ptitle", "share"].forEach(hide);
    $("navRemix").style.display = "none"; $("navShare").style.display = "none";
    if (mode === "feed") { history.replaceState(0, 0, location.pathname); show("feed"); renderFeed(); }
    if (mode === "create") { show("create"); initCreate(); }
    if (mode === "play") { show("pc"); show("ptitle"); $("navShare").style.display = ""; $("navRemix").style.display = ""; }
  }
  W.go = go;

  // ---- FEED ----
  var SEED = [
    { v: 1, t: "Birth of a Star", a: "@nova", b: "void", k: [{ at: 0, s: .1, l: 0, p: 0, g: 0, h: 50, x: 0, z: 0 }, { at: 60, s: .5, l: 0, p: 0, g: 1, h: 45, x: 0, z: 0 }, { at: 99, s: .9, l: 0, p: .3, g: 1, h: 30, x: 0, z: 0 }] },
    { v: 1, t: "The Bloom", a: "@flora", b: "forest", k: [{ at: 0, s: .2, l: .1, p: 0, g: .3, h: 300, x: 0, z: 0 }, { at: 50, s: .6, l: .2, p: .9, g: .7, h: 320, x: 0, z: 0 }, { at: 99, s: .5, l: .2, p: .5, g: .9, h: 180, x: 0, z: 0 }] },
    { v: 1, t: "Wanderer", a: "@roam", b: "savanna", k: [{ at: 0, s: .4, l: .9, p: .1, g: .4, h: 130, x: -.8, z: -.6 }, { at: 50, s: .45, l: 1, p: .1, g: .5, h: 140, x: .7, z: .3 }, { at: 99, s: .4, l: .9, p: .1, g: .4, h: 150, x: -.5, z: .8 }] },
    { v: 1, t: "Rage", a: "@ferox", b: "volcanic", k: [{ at: 0, s: .5, l: .4, p: 0, g: .3, h: 0, x: 0, z: 0 }, { at: 99, s: .8, l: .5, p: 1, g: 1, h: 10, x: 0, z: 0 }] },
    { v: 1, t: "Tides", a: "@blue", b: "forest", k: [{ at: 0, s: .6, l: .3, p: .2, g: .5, h: 200, x: 0, z: -.5 }, { at: 33, s: .4, l: .3, p: .2, g: .8, h: 190, x: 0, z: .5 }, { at: 66, s: .6, l: .3, p: .2, g: .5, h: 210, x: 0, z: -.5 }, { at: 99, s: .4, l: .3, p: .2, g: .8, h: 190, x: 0, z: .5 }] }
  ];
  function thumbStyle(m) {
    var h0 = m.k[0].h, h1 = m.k[m.k.length - 1].h;
    return "background:linear-gradient(135deg,hsl(" + h0 + ",65%,45%),hsl(" + h1 + ",70%,32%))";
  }
  function renderFeed() {
    var g = $("grid"); g.innerHTML = "";
    var all = SEED.concat(W.__EXTRA_MOMENTS__ || []);
    all.forEach(function (m) {
      var card = D.createElement("div"); card.className = "card";
      card.innerHTML = '<div class="thumb" style="' + thumbStyle(m) + '"><span class="tag">100 frames</span><span class="play">▶</span></div>' +
        '<div class="meta"><div class="ti">' + esc(m.t) + '</div><div class="au">' + esc(m.a || "@anon") + ' · ' + (m.b || "savanna") + '</div></div>';
      card.onclick = function () { openPlay(m); };
      g.appendChild(card);
    });
  }
  function esc(s) { return (s || "").replace(/[<>&"]/g, function (c) { return { "<": "&lt;", ">": "&gt;", "&": "&amp;", '"': "&quot;" }[c]; }); }

  // ---- PLAY ----
  function openPlay(m, push) {
    go("play"); loadMoment(m); S.playing = true; $("ppBtn").textContent = "❚❚";
    $("ptitle").innerHTML = esc(m.t) + ' <span class="au">' + esc(m.a || "@anon") + "</span>";
    if (push !== false) history.replaceState(0, 0, location.pathname + "?m=" + encode(m));
  }
  W.togglePlay = function () { S.playing = !S.playing; $("ppBtn").textContent = S.playing ? "❚❚" : "▶"; };
  W.restart = function () { S.pf = 0; S.playing = true; $("ppBtn").textContent = "❚❚"; };
  W.scrubAt = function (e) { var r = $("track").getBoundingClientRect(); S.pf = Math.max(0, Math.min(99, (e.clientX - r.left) / r.width * 99)); S.playing = false; $("ppBtn").textContent = "▶"; applyFrame(S.pf, true); };
  function updatePC() { $("fl").textContent = "FRAME " + Math.round(S.pf) + " / 99"; $("fill").style.width = (S.pf / 99 * 100) + "%"; }
  W.remix = function () { if (S.moment) { go("create"); loadIntoCreate(S.moment); } };

  // ---- CREATE ----
  var draft = null, selKey = 0;
  var SL = ["S", "L", "P", "G", "H", "X", "Z"];
  function readSliders() {
    return { s: $("rS").value / 100, l: $("rL").value / 100, p: $("rP").value / 100, g: $("rG").value / 100, h: +$("rH").value, x: $("rX").value / 100, z: $("rZ").value / 100 };
  }
  function writeSliders(f) { $("rS").value = f.s * 100; $("rL").value = f.l * 100; $("rP").value = f.p * 100; $("rG").value = f.g * 100; $("rH").value = f.h; $("rX").value = f.x * 100; $("rZ").value = f.z * 100; updateSliderLabels(); }
  function updateSliderLabels() { $("vS").textContent = Math.round($("rS").value); $("vL").textContent = Math.round($("rL").value); $("vP").textContent = Math.round($("rP").value); $("vG").textContent = Math.round($("rG").value); $("vH").textContent = Math.round($("rH").value) + "°"; $("vX").textContent = Math.round($("rX").value); $("vZ").textContent = Math.round($("rZ").value); }
  function previewDraft() { draft.k.sort(function (a, b) { return a.at - b.at; }); S.frames = expand(draft); setBiome($("cBiome").value); }
  function curFrameFromSlider() {
    var f = readSliders(); f.at = draft.k[selKey].at; draft.k[selKey] = clampF(f); previewDraft();
    // live-apply at the selected keyframe's frame
    S.pf = f.at; applyFrame(f.at, true);
  }
  function renderKeys() {
    var el = $("keys"); el.innerHTML = "";
    draft.k.forEach(function (k, i) {
      var b = D.createElement("div"); b.className = "kf" + (i === selKey ? " on" : ""); b.textContent = "f" + k.at;
      b.onclick = function () { selKey = i; writeSliders(draft.k[i]); S.pf = draft.k[i].at; applyFrame(draft.k[i].at, true); renderKeys(); };
      el.appendChild(b);
    });
  }
  function initCreate() {
    if (!draft) draft = { v: 1, t: "untitled", a: "@anon", b: "savanna", k: [{ at: 0, s: .35, l: .4, p: 0, g: .45, h: 140, x: 0, z: 0 }, { at: 99, s: .7, l: .6, p: .4, g: .8, h: 40, x: 0, z: 0 }] };
    selKey = 0; S.mode = "create"; writeSliders(draft.k[0]); previewDraft(); renderKeys();
  }
  function loadIntoCreate(m) { draft = JSON.parse(JSON.stringify(m)); $("cTitle").value = m.t || "untitled"; $("cAuthor").value = m.a || "@anon"; $("cBiome").value = m.b || "savanna"; selKey = 0; writeSliders(draft.k[0]); previewDraft(); renderKeys(); }
  W.addKey = function () {
    var at = Math.round(S.pf); if (draft.k.some(function (k) { return k.at === at; })) at = Math.min(99, at + 5);
    var f = readSliders(); f.at = at; draft.k.push(clampF(f)); draft.k.sort(function (a, b) { return a.at - b.at; });
    selKey = draft.k.findIndex(function (k) { return k.at === at; }); previewDraft(); renderKeys(); toast("keyframe at f" + at);
  };
  W.finishMoment = function () {
    draft.t = $("cTitle").value || "untitled"; draft.a = $("cAuthor").value || "@anon"; draft.b = $("cBiome").value;
    openShare(draft);
  };
  ["rS", "rL", "rP", "rG", "rH", "rX", "rZ"].forEach(function (id) { D.addEventListener("input", function (e) { if (e.target.id === id && S.mode === "create") curFrameFromSlider(); }); });
  $("cBiome").addEventListener("change", function () { if (S.mode === "create") { draft.b = $("cBiome").value; setBiome(draft.b); } });

  // ---- SHARE ----
  var shareMoment = null;
  function openShare(m) {
    shareMoment = m || S.moment; if (!shareMoment) return;
    var url = location.origin + location.pathname + "?m=" + encode(shareMoment);
    $("surl").value = url;
    var box = $("qrbox"); box.innerHTML = "";
    try { new QRCode(box, { text: url, width: 168, height: 168, correctLevel: QRCode.CorrectLevel.H }); }
    catch (e) { box.textContent = "(scan via the link below)"; }
    show("share");
  }
  W.openShare = function () { openShare(S.moment); };
  W.copyUrl = function () { $("surl").select(); try { D.execCommand("copy"); } catch (e) {} navigator.clipboard && navigator.clipboard.writeText($("surl").value); toast("link copied"); };
  W.playShared = function () { hide("share"); openPlay(shareMoment); };

  // ---- boot ----
  W.addEventListener("resize", function () { camera.aspect = W.innerWidth / W.innerHeight; camera.updateProjectionMatrix(); renderer.setSize(W.innerWidth, W.innerHeight); });
  function boot() {
    var q = new URLSearchParams(location.search);
    setBiome("savanna");
    // optionally augment the feed from a committed manifest
    fetch("moments.json").then(function (r) { return r.json(); }).then(function (j) { W.__EXTRA_MOMENTS__ = j.moments || j; if (S.mode === "feed") renderFeed(); }).catch(function () {});
    if (q.get("m")) { var m = decode(q.get("m")); if (m) { openPlay(m, false); requestAnimationFrame(tick); return; } }
    if (q.has("create")) { go("create"); requestAnimationFrame(tick); return; }
    go("feed"); requestAnimationFrame(tick);
  }
  boot();
})();
