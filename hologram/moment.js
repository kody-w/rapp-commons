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
    FORM.heartLight = lt; FORM.baseLI = 0.6 + f.g * 2.2;   // the glow that pulses with the heartbeat
  }
  // HEARTBEAT — each frame is a beat; a sharp lub-dub then rest, so the companion reads as alive.
  function heartbeat(t) {
    var p = (t % 1.05) / 1.05;
    var lub = Math.exp(-Math.pow((p - 0.0) * 13, 2));
    var dub = Math.exp(-Math.pow((p - 0.16) * 15, 2)) * 0.7;
    return lub + dub;
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

  // BROWSER SIGNING — a per-browser ECDSA P-256 key (persisted in localStorage) signs each Moment on
  // Share, so authorship is cryptographically PROVABLE on a public repo and the market's distinct-signer
  // counts can't be gamed (a copy can't forge your key). Sign/verify use the canonical body (all fields
  // except sig/pub, top-level keys sorted) — exactly what market.html verifies.
  var KEY = null;
  function _body(m) { var b = {}; Object.keys(m).sort().forEach(function (k) { if (k !== "sig" && k !== "pub") b[k] = m[k]; }); return new TextEncoder().encode(JSON.stringify(b)); }
  async function getKey() {
    if (KEY) return KEY;
    try {
      var stored = localStorage.getItem("holo:key");
      if (stored) { var j = JSON.parse(stored); KEY = { priv: await crypto.subtle.importKey("jwk", j.priv, { name: "ECDSA", namedCurve: "P-256" }, true, ["sign"]), pub: j.pub }; }
      else {
        var kp = await crypto.subtle.generateKey({ name: "ECDSA", namedCurve: "P-256" }, true, ["sign", "verify"]);
        var priv = await crypto.subtle.exportKey("jwk", kp.privateKey), pub = await crypto.subtle.exportKey("jwk", kp.publicKey);
        localStorage.setItem("holo:key", JSON.stringify({ priv: priv, pub: pub })); KEY = { priv: kp.privateKey, pub: pub };
      }
    } catch (e) { KEY = null; }
    return KEY;
  }
  async function signMoment(m) {
    var k = await getKey(); if (!k) return m;
    var sig = await crypto.subtle.sign({ name: "ECDSA", hash: "SHA-256" }, k.priv, _body(m));
    m.sig = Array.from(new Uint8Array(sig)).map(function (b) { return b.toString(16).padStart(2, "0"); }).join("");
    m.pub = k.pub; return m;
  }
  async function verifyMoment(m) {
    if (!m.sig || !m.pub) return false;
    try {
      var key = await crypto.subtle.importKey("jwk", m.pub, { name: "ECDSA", namedCurve: "P-256" }, false, ["verify"]);
      var sig = Uint8Array.from(m.sig.match(/.{1,2}/g).map(function (h) { return parseInt(h, 16); }));
      return await crypto.subtle.verify({ name: "ECDSA", hash: "SHA-256" }, key, sig, _body(m));
    } catch (e) { return false; }
  }
  W.signMoment = signMoment; W.verifyMoment = verifyMoment;

  // .egg — export a Moment as a portable, re-uploadable file. Lossless: keyframes + title + biome +
  // signature are all preserved, so a re-imported .egg displays exactly as it was, still provably owned.
  function exportEgg(m) {
    m = m || S.moment; if (!m) return;
    var egg = { format: "holographic-moment-egg/1.0", moment: m, exported: new Date().toISOString() };
    var blob = new Blob([JSON.stringify(egg, null, 2)], { type: "application/json" });
    var url = URL.createObjectURL(blob), a = D.createElement("a");
    a.href = url; a.download = (m.t || "moment").replace(/[^a-z0-9]+/gi, "_").replace(/^_+|_+$/g, "").toLowerCase() + ".egg";
    D.body.appendChild(a); a.click(); a.remove(); setTimeout(function () { URL.revokeObjectURL(url); }, 1000);
    toast("exported " + a.download);
  }
  function importEgg(file) {
    if (!file) return;
    var r = new FileReader();
    r.onload = function () {
      try {
        var j = JSON.parse(r.result), m = (j && j.moment) ? j.moment : j;
        if (m && Array.isArray(m.k)) { openPlay(m); toast("imported “" + (m.t || "moment") + "”"); }
        else toast("not a valid .egg");
      } catch (e) { toast("couldn't read that .egg"); }
    };
    r.readAsText(file);
  }
  W.exportEgg = function () { exportEgg(S.moment); };
  (function () { var el = D.getElementById("eggfile"); if (el) el.addEventListener("change", function (e) { importEgg(e.target.files[0]); e.target.value = ""; }); })();

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
    if ((S.mode === "play" || S.mode === "create" || S.pip) && S.frames) {
      // play: honor pause. create: no auto-advance. PiP while navigated away: keep looping.
      var playing = (S.mode === "play") ? S.playing : (S.mode === "create" ? false : true);
      var moving = (S.mode === "create") || playing;     // PAUSE = a true freeze-frame: stop the clock, bob, AND camera
      if (playing) { S.pf += dt * (99 / S.dur); if (S.pf >= 99) S.pf = 0; }
      if (FORM && moving) FORM.position.y = Math.abs(Math.sin(now * 5)) * 0.1;
      applyFrame(S.pf, false);
      if (FORM) { var beat = moving ? heartbeat(now) : 0;   // the companion's heartbeat — pulse the body + glow
        FORM.scale.setScalar(1 + beat * 0.045);
        if (FORM.heartLight) FORM.heartLight.intensity = FORM.baseLI * (1 + beat * 0.65); }
      if (moving) camTick(dt);
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
    ["feed", "create", "pc", "ptitle", "share", "mint"].forEach(hide);
    $("navRemix").style.display = "none"; $("navShare").style.display = "none"; $("navMint").style.display = "none"; $("navEgg").style.display = "none"; $("navPip").style.display = "none";
    if (mode === "feed") { history.replaceState(0, 0, location.pathname); show("feed"); renderFeed(); }
    if (mode === "create") { show("create"); initCreate(); }
    if (mode === "play") { show("pc"); show("ptitle"); $("navShare").style.display = ""; $("navRemix").style.display = ""; $("navMint").style.display = ""; $("navEgg").style.display = ""; $("navPip").style.display = ((D.pictureInPictureEnabled !== false) ? "" : "none"); }
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
    verifyMoment(m).then(function (ok) {   // show a provable-authorship badge when the signature verifies
      if (ok && m.pub) $("ptitle").innerHTML += ' <span class="au" style="color:var(--pa)">✓ signed ' + (m.pub.x || "").slice(0, 10) + '…</span>';
    });
  }
  W.togglePlay = function () { S.playing = !S.playing; $("ppBtn").textContent = S.playing ? "❚❚" : "▶"; };
  W.restart = function () { S.pf = 0; S.playing = true; $("ppBtn").textContent = "❚❚"; };
  W.scrubAt = function (e) { var r = $("track").getBoundingClientRect(); S.pf = Math.max(0, Math.min(99, (e.clientX - r.left) / r.width * 99)); S.playing = false; $("ppBtn").textContent = "▶"; applyFrame(S.pf, true); };
  function updatePC() { $("fl").textContent = "FRAME " + Math.round(S.pf) + " / 99"; $("fill").style.width = (S.pf / 99 * 100) + "%"; }
  W.remix = function () { if (S.moment) { go("create"); loadIntoCreate(S.moment); } };

  // PICTURE-IN-PICTURE — float the live hologram in an always-on-top OS window so it keeps playing
  // while you work in other apps. Captures the WebGL canvas to a stream and PiPs it (no fullscreen).
  async function pipHologram() {
    var vid = $("pipvid");
    try {
      if (D.pictureInPictureElement) { await D.exitPictureInPicture(); S.pip = false; return; }
      if (!S.pipStream) S.pipStream = renderer.domElement.captureStream(30);
      vid.srcObject = S.pipStream; vid.muted = true;
      await vid.play();
      await vid.requestPictureInPicture();
      S.pip = true;
      vid.addEventListener("leavepictureinpicture", function () { S.pip = false; }, { once: true });
      toast("hologram floating — keep working ✦");
    } catch (e) { toast("picture-in-picture isn't available here"); }
  }
  W.pipHologram = pipHologram;

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
  async function openShare(m) {
    shareMoment = m || S.moment; if (!shareMoment) return;
    await signMoment(shareMoment);                          // sign with the browser key — provable authorship
    var url = location.origin + location.pathname + "?m=" + encode(shareMoment);
    $("surl").value = url;
    var box = $("qrbox"); box.innerHTML = "";
    try { new QRCode(box, { text: url, width: 168, height: 168, correctLevel: QRCode.CorrectLevel.H }); }
    catch (e) { box.textContent = "(scan via the link below)"; }
    var fp = (shareMoment.pub && shareMoment.pub.x) ? shareMoment.pub.x.slice(0, 16) : "";
    var h = D.querySelector("#sheet h3"); if (h) h.innerHTML = "Your Holographic Moment" + (fp ? "<span style='display:block;color:var(--pa);font-size:12px;font-weight:600;margin-top:5px'>✓ signed by your key · " + fp + "…</span>" : "");
    show("share");
  }
  W.openShare = function () { openShare(S.moment); };

  // EDITIONS — mint a signed LIMITED RUN of a Moment. Each edition is a distinct signed token
  // (numbered n/N + a unique nonce) with its OWN URL + QR — provable scarcity out of infinite supply.
  function _nonce() { var a = new Uint8Array(8); crypto.getRandomValues(a); return Array.from(a).map(function (b) { return b.toString(16).padStart(2, "0"); }).join(""); }
  async function mintEditions(m, n) {
    var base = { v: m.v || 1, t: m.t, a: m.a, b: m.b, k: m.k }, out = [];
    for (var i = 1; i <= n; i++) {
      var ed = JSON.parse(JSON.stringify(base));
      ed.ed = { n: i, of: n, id: _nonce() }; ed.t = m.t + " · #" + i + "/" + n;
      await signMoment(ed); out.push(ed);
    }
    return out;
  }
  async function openMint(n) {
    if (!S.moment) return; n = n || 50;
    S.editionBase = S.moment;
    $("mintTitle").textContent = (S.moment.t || "Moment");
    $("mintSub").textContent = "running the press · " + n + " editions…";
    show("mint"); S.mode = "mint";
    var eds = await mintEditions(S.moment, n); S.editions = eds;
    $("mintSub").textContent = "press run of " + n + " · each a signed 1-of-1" + (eds[0] && eds[0].pub ? " · printed by key " + eds[0].pub.x.slice(0, 12) + "…" : "");
    var grid = $("mintgrid"); grid.innerHTML = "";
    eds.forEach(function (ed) {
      var url = location.origin + location.pathname + "?m=" + encode(ed);
      var card = D.createElement("div"); card.className = "edcard";
      var qz = D.createElement("div"); qz.className = "qz";
      try { new QRCode(qz, { text: url, width: 110, height: 110, correctLevel: QRCode.CorrectLevel.M }); } catch (e) { qz.textContent = "QR"; }
      card.appendChild(qz);
      var en = D.createElement("div"); en.className = "en"; en.textContent = "EDITION " + ed.ed.n + " / " + ed.ed.of;
      var ev = D.createElement("div"); ev.className = "ev"; ev.textContent = "✓ signed · " + ed.ed.id.slice(0, 8);
      card.appendChild(en); card.appendChild(ev);
      card.onclick = function () { location.href = url; };
      grid.appendChild(card);
    });
    history.replaceState(0, 0, location.pathname + "?mint=" + encode(S.editionBase) + "&n=" + n);
  }
  W.openMint = function () { openMint(50); };
  W.copyMintSheet = function () { var u = location.origin + location.pathname + "?mint=" + encode(S.editionBase || S.moment) + "&n=" + (S.editions ? S.editions.length : 50); try { navigator.clipboard.writeText(u); } catch (e) {} toast("mint sheet link copied"); };
  W.copyUrl = function () { $("surl").select(); try { D.execCommand("copy"); } catch (e) {} navigator.clipboard && navigator.clipboard.writeText($("surl").value); toast("link copied"); };
  W.playShared = function () { hide("share"); openPlay(shareMoment); };

  // ---- boot ----
  W.addEventListener("resize", function () { camera.aspect = W.innerWidth / W.innerHeight; camera.updateProjectionMatrix(); renderer.setSize(W.innerWidth, W.innerHeight); });
  function boot() {
    var q = new URLSearchParams(location.search);
    setBiome("savanna");
    // optionally augment the feed from a committed manifest
    fetch("moments.json").then(function (r) { return r.json(); }).then(function (j) { W.__EXTRA_MOMENTS__ = j.moments || j; if (S.mode === "feed") renderFeed(); }).catch(function () {});
    if (q.get("mint")) { var mm = decode(q.get("mint")); if (mm) { S.moment = mm; S.frames = expand(mm); setBiome(mm.b || "savanna"); requestAnimationFrame(tick); openMint(parseInt(q.get("n"), 10) || 50); return; } }
    if (q.get("m")) { var m = decode(q.get("m")); if (m) { openPlay(m, false); requestAnimationFrame(tick); return; } }
    if (q.has("create")) { go("create"); requestAnimationFrame(tick); return; }
    go("feed"); requestAnimationFrame(tick);
  }
  boot();
})();
