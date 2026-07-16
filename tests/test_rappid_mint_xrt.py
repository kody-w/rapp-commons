#!/usr/bin/env python3
"""Cross-runtime rappid mint proof — Python and JS (WebCrypto) MUST derive the
SAME rapp/1 §6.2 keyed rappid from the same P-256 key.

The mint (both runtimes, byte-identical):
    tail   = sha256(b"rapp/1:rappid\n" + SPKI_DER).hexdigest()
    rappid = "rappid:@being/" + tail[:12] + ":" + tail
where SPKI_DER is the RFC 5480 SubjectPublicKeyInfo DER of the public key
(browser: exportKey('spki', ...); Python cryptography:
public_bytes(Encoding.DER, PublicFormat.SubjectPublicKeyInfo)).

The wire keeps carrying the RAW X9.62 point in `pub`, so the JS side proves the
verification path too: importKey('raw') -> exportKey('spki') -> same rappid.
Legacy rappid:v3 ids are read-forever in signed history and are NOT minted here.

Run:  python3 tests/test_rappid_mint_xrt.py     (needs `cryptography` + node >= 20)
Exit 0 iff Python's shipped mint and JS's raw-point derivation agree on N keys.
"""
import base64
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
N_KEYS = 5

JS = r"""
import { webcrypto as crypto } from "node:crypto";
import { readFileSync } from "node:fs";
const ub64u = s => { s = s.replace(/-/g, "+").replace(/_/g, "/"); while (s.length % 4) s += "=";
  return new Uint8Array(Buffer.from(s, "base64")); };
const hex = u8 => [...u8].map(b => b.toString(16).padStart(2, "0")).join("");
const rows = JSON.parse(readFileSync(0, "utf8"));
let ok = 0;
for (const row of rows) {
  const key = await crypto.subtle.importKey("raw", ub64u(row.pub),
    { name: "ECDSA", namedCurve: "P-256" }, true, ["verify"]);
  const spki = new Uint8Array(await crypto.subtle.exportKey("spki", key));
  const dom = new TextEncoder().encode("rapp/1:rappid\n");
  const pre = new Uint8Array(dom.length + spki.length);
  pre.set(dom); pre.set(spki, dom.length);
  const tail = hex(new Uint8Array(await crypto.subtle.digest("SHA-256", pre)));
  const rappid = "rappid:@being/" + tail.slice(0, 12) + ":" + tail;
  if (rappid === row.rappid) ok += 1;
  else console.error("MISMATCH js=" + rappid + " py=" + row.rappid);
}
console.log(JSON.stringify({ ok, total: rows.length }));
"""


def main() -> int:
    if shutil.which("node") is None:
        print("SKIP xrt_mint_equality -- node not on PATH")
        return 0
    spec = importlib.util.spec_from_file_location(
        "swarm_agent", os.path.join(REPO, "swarm_agent.py"))
    sw = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(sw)
    if not sw._ensure_crypto():
        print("SKIP xrt_mint_equality -- cryptography unavailable")
        return 0
    ec, _h, ser, _d = sw._crypto()

    rows = []
    for _ in range(N_KEYS):
        priv = ec.generate_private_key(ec.SECP256R1())
        raw = priv.public_key().public_bytes(
            ser.Encoding.X962, ser.PublicFormat.UncompressedPoint)
        rows.append({"pub": base64.urlsafe_b64encode(raw).decode().rstrip("="),
                     "rappid": sw._mint_rappid(priv.public_key())})  # the SHIPPED mint

    with tempfile.NamedTemporaryFile("w", suffix=".mjs", delete=False) as f:
        f.write(JS)
        js_path = f.name
    try:
        out = subprocess.run(["node", js_path], input=json.dumps(rows),
                             capture_output=True, text=True, timeout=60)
    finally:
        os.unlink(js_path)
    if out.returncode != 0:
        print("FAIL xrt_mint_equality -- node error: " + out.stderr.strip()[:200])
        return 1
    res = json.loads(out.stdout.strip().splitlines()[-1])
    ok = res["ok"] == res["total"] == N_KEYS
    print(("PASS" if ok else "FAIL") +
          f" xrt_mint_equality -- {res['ok']}/{res['total']} keys: "
          "JS(webcrypto raw->SPKI) == Python(shipped §6.2 mint)")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
