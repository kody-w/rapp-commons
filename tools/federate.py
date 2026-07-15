#!/usr/bin/env python3
"""federate.py — pull commons members' outbound lanes, verify, union into events/.

Runs in the rapp-commons repo's GitHub Action on a 10-minute cron (and on
manual dispatch). The flow:

  1. Read members.json → list of {rappid, added_at, via}.
  2. For each member, derive their public-estate URL from their rappid.
     Convention (Article XLVIII):
         operator rappid: rappid:@<owner>/<slug>:<64-hex>  (canonical §6.1)
         public estate:   https://raw.githubusercontent.com/<owner>/<owner>-estate/main/outbound/<commons-rappid-slug>/
     (Operators without a `<owner>-estate` repo simply produce no posts;
      no error, just nothing to pull.)
  3. List that directory via the GitHub contents API.
  4. For each .json file, fetch + verify signature against the embedded
     pub JWK + fingerprint match against from.rappid.
  5. Enforce (from, ts) monotonic per the rapp-commons-event/1.0 protocol
     (operators can't backdate against their own latest already-accepted
     event).
  6. Write valid events to events/<fp(pub)[:16]>-<ts safe>.json.

The action commits + pushes any new files, [skip ci] in the message so
the federate job doesn't trigger itself.

Stdlib-only (cryptography is via PyNaCl for ed25519 OR via openssl-cli for
ECDSA P-256, since stdlib doesn't include P-256 verify). Actually
ECDSA P-256 verify in pure stdlib is non-trivial — we shell out to
`openssl dgst -sha256 -verify` on the runner.

For v1 this script implements the structural skeleton; the per-member
HTTP fetch + signature verify path is best-effort and logs misses
rather than failing the workflow.
"""

from __future__ import annotations

import base64
import json
import os
import pathlib
import re
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request
from typing import Any

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
MEMBERS_FILE = REPO_ROOT / "members.json"
NEIGHBORHOOD_FILE = REPO_ROOT / "neighborhood.json"
EVENTS_DIR = REPO_ROOT / "events"
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")
USER_AGENT = "rapp-commons-federation/1.0"


# ───────────────────────── helpers ────────────────────────────────────────

def _canonical_json(d: dict) -> str:
    return json.dumps(d, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _fingerprint(pub_jwk: dict) -> str:
    import hashlib
    return hashlib.sha256(_canonical_json(pub_jwk).encode("utf-8")).hexdigest()


def _sanitize_rappid(rappid: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "_", rappid)[:200]


def _gh_fetch(url: str) -> tuple[int, bytes]:
    req = urllib.request.Request(url, headers={
        "Accept": "application/vnd.github+json" if "api.github.com" in url else "application/json,text/plain,*/*",
        "User-Agent": USER_AGENT,
    })
    if GITHUB_TOKEN and "api.github.com" in url:
        req.add_header("Authorization", f"Bearer {GITHUB_TOKEN}")
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            return r.status, r.read()
    except urllib.error.HTTPError as e:
        return e.code, b""
    except Exception as e:
        print(f"  fetch failed: {url} — {e}", file=sys.stderr)
        return 0, b""


def _parse_rappid(rappid: str) -> dict | None:
    """Parse a member rappid into at least {owner, repo}. Accepts BOTH the
    canonical RAPP form (spec §6.1); legacy v2 is not tolerated:

      canonical (§6.1):  rappid:@<owner>/<slug>:<64-hex>

    Canonical only (spec §6.1) — legacy v2 is not tolerated.
    """
    m = re.match(
        r"^rappid:@(?P<owner>[a-z0-9]+(?:-[a-z0-9]+)*)/(?P<repo>[a-z0-9]+(?:-[a-z0-9]+)*):(?P<hash>[0-9a-f]{64})$",
        rappid,
    )
    if not m:
        return None
    d = m.groupdict()
    d.update(kind=None, ns=f"@{d['owner']}/{d['repo']}", host="github.com")
    return d


def _outbound_url(member_rappid: str, commons_rappid_slug: str) -> str | None:
    """Compose the GitHub contents-API URL for the member's outbound lane.

    Convention: <owner>/<owner>-estate, branch main, path
    outbound/<sanitized commons rappid>/
    """
    parsed = _parse_rappid(member_rappid)
    if not parsed:
        return None
    owner = parsed["owner"]
    return (
        f"https://api.github.com/repos/{owner}/{owner}-estate/contents/"
        f"outbound/{commons_rappid_slug}"
    )


# ───────────────────────── verification ───────────────────────────────────

def _jwk_to_pem(pub_jwk: dict) -> str:
    """ECDSA P-256 JWK → PEM (uncompressed point → SEC1 → SPKI). Stdlib only."""
    if pub_jwk.get("kty") != "EC" or pub_jwk.get("crv") != "P-256":
        raise ValueError("not an EC P-256 JWK")
    x = base64.urlsafe_b64decode(pub_jwk["x"] + "==")
    y = base64.urlsafe_b64decode(pub_jwk["y"] + "==")
    if len(x) != 32 or len(y) != 32:
        raise ValueError("invalid x/y coordinate length")
    # SEC1 uncompressed point: 0x04 || X || Y
    uncompressed = b"\x04" + x + y
    # SPKI prefix for ECDSA P-256 public key
    spki_prefix = bytes.fromhex(
        "3059301306072a8648ce3d020106082a8648ce3d030107034200"
    )
    spki = spki_prefix + uncompressed
    b64 = base64.b64encode(spki).decode("ascii")
    pem = "-----BEGIN PUBLIC KEY-----\n"
    for i in range(0, len(b64), 64):
        pem += b64[i:i+64] + "\n"
    pem += "-----END PUBLIC KEY-----\n"
    return pem


def _verify_ecdsa_p256(canonical_payload: bytes, sig_hex: str, pub_jwk: dict) -> bool:
    """Verify ECDSA P-256 signature via openssl. The signature format is
    IEEE P1363 (r || s, each 32 bytes — i.e. what WebCrypto subtle.sign
    produces). openssl-cli wants DER, so we convert.
    """
    try:
        sig_bytes = bytes.fromhex(sig_hex)
        if len(sig_bytes) != 64:
            return False
        r, s = sig_bytes[:32], sig_bytes[32:]
        # Encode as DER: SEQUENCE { INTEGER r, INTEGER s }
        def _der_int(b: bytes) -> bytes:
            b = b.lstrip(b"\x00") or b"\x00"
            if b[0] & 0x80:
                b = b"\x00" + b
            return b"\x02" + bytes([len(b)]) + b
        der_r = _der_int(r)
        der_s = _der_int(s)
        body = der_r + der_s
        der = b"\x30" + bytes([len(body)]) + body

        pem = _jwk_to_pem(pub_jwk)

        with tempfile.TemporaryDirectory() as td:
            tdp = pathlib.Path(td)
            (tdp / "pub.pem").write_text(pem)
            (tdp / "msg.bin").write_bytes(canonical_payload)
            (tdp / "sig.der").write_bytes(der)
            r = subprocess.run(
                ["openssl", "dgst", "-sha256",
                 "-verify", str(tdp / "pub.pem"),
                 "-signature", str(tdp / "sig.der"),
                 str(tdp / "msg.bin")],
                capture_output=True, text=True, timeout=10,
            )
            return r.returncode == 0 and "Verified OK" in r.stdout
    except Exception as e:
        print(f"  verify error: {e}", file=sys.stderr)
        return False


# ───────────────────────── roll-up ────────────────────────────────────────

def _ts_safe(ts: str) -> str:
    return ts.replace(":", "-")


def _is_valid_event(ev: dict, expected_from: str, latest_ts_per_from: dict) -> tuple[bool, str]:
    for required in ("schema", "kind", "from", "ts", "sig", "pub"):
        if required not in ev:
            return False, f"missing field {required}"
    if ev.get("schema") != "rapp-commons-event/1.0":
        return False, f"wrong schema: {ev.get('schema')}"
    if ev["from"] != expected_from:
        return False, f"from mismatch: claimed {ev['from']!r} but outbound is for {expected_from!r}"
    # Fingerprint check
    fp = _fingerprint(ev["pub"])
    parsed = _parse_rappid(ev["from"])
    if not parsed:
        return False, "from is not a valid rappid"
    # (We don't enforce fp-vs-rappid binding here because the rappid format
    # carries an opaque hash, not the key fingerprint. The signing identity
    # is the public key in `pub`; provenance is established by verifying
    # signature, which we do below. A future Article binds rappid-hash to
    # key fingerprint; until then, key-bound provenance is the floor.)
    # Monotonic ts per from
    prev = latest_ts_per_from.get(ev["from"])
    if prev is not None and ev["ts"] < prev:
        return False, f"non-monotonic ts: {ev['ts']} < previously-accepted {prev}"
    # Body length
    if len(ev.get("body") or "") > 2048:
        return False, "body exceeds 2048 chars"
    # Verify signature
    payload = {k: v for k, v in ev.items() if k not in ("sig", "pub")}
    canonical = _canonical_json(payload).encode("utf-8")
    if not _verify_ecdsa_p256(canonical, ev["sig"], ev["pub"]):
        return False, "signature verification failed"
    return True, "ok"


def _existing_events() -> dict:
    """Return {from: latest_ts} from the already-committed events/ dir."""
    latest = {}
    for p in EVENTS_DIR.glob("*.json"):
        try:
            ev = json.loads(p.read_text())
            f = ev.get("from")
            t = ev.get("ts")
            if f and t and (f not in latest or t > latest[f]):
                latest[f] = t
        except Exception:
            pass
    return latest


def main() -> int:
    if not MEMBERS_FILE.exists():
        print("members.json missing — nothing to federate.")
        return 0
    if not NEIGHBORHOOD_FILE.exists():
        print("neighborhood.json missing — cannot derive commons rappid.")
        return 1
    EVENTS_DIR.mkdir(exist_ok=True)

    nbhd = json.loads(NEIGHBORHOOD_FILE.read_text())
    commons_rappid = nbhd.get("rappid")
    if not commons_rappid:
        print("neighborhood.json has no rappid — cannot derive outbound lane path.")
        return 1
    commons_slug = _sanitize_rappid(commons_rappid)

    members = json.loads(MEMBERS_FILE.read_text()).get("members") or []
    print(f"federating {len(members)} member(s); commons slug={commons_slug}")

    latest_ts_per_from = _existing_events()
    added = 0
    skipped = 0

    for m in members:
        rappid = m.get("rappid")
        if not rappid:
            continue
        url = _outbound_url(rappid, commons_slug)
        if not url:
            print(f"  skip {rappid}: not a valid rappid")
            continue

        # GitHub contents API returns either an array (dir listing) or 404.
        status, body = _gh_fetch(url)
        if status == 404:
            # Most members won't have a public-estate repo yet — that's fine.
            print(f"  {rappid}: no outbound dir at <owner>-estate (404)")
            continue
        if status != 200:
            print(f"  {rappid}: outbound fetch returned {status}")
            continue

        try:
            listing = json.loads(body)
        except Exception as e:
            print(f"  {rappid}: outbound listing not JSON: {e}")
            continue

        if not isinstance(listing, list):
            continue

        for entry in listing:
            if not isinstance(entry, dict): continue
            if entry.get("type") != "file": continue
            name = entry.get("name", "")
            if not name.endswith(".json"): continue
            raw_url = entry.get("download_url")
            if not raw_url: continue

            # Already accepted?
            target = EVENTS_DIR / name
            if target.exists():
                continue

            s, b = _gh_fetch(raw_url)
            if s != 200:
                print(f"    {name}: fetch returned {s}")
                continue
            try:
                ev = json.loads(b)
            except Exception as e:
                print(f"    {name}: not JSON: {e}")
                skipped += 1
                continue

            ok, why = _is_valid_event(ev, expected_from=rappid,
                                       latest_ts_per_from=latest_ts_per_from)
            if not ok:
                print(f"    {name}: REJECTED — {why}")
                skipped += 1
                continue

            target.write_text(_canonical_json(ev) + "\n", encoding="utf-8")
            latest_ts_per_from[ev["from"]] = ev["ts"]
            added += 1
            print(f"    {name}: accepted")

    print(f"federation done. added={added} skipped={skipped}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
