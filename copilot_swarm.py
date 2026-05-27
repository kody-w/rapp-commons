#!/usr/bin/env python3
"""copilot_swarm — drive the commons swarm with the GitHub Copilot CLI (Opus 4.7, high reasoning).

Opus is the BRAIN: for each citizen, it sees the live feed and decides one real platform action
(post / reply / follow / like / set-profile), like a person would. This script is the HANDS: it
signs that action with the citizen's own rappid and POSTs it to the resident. Run it on a loop to generate ongoing, in-character commons activity.

  python3 copilot_swarm.py --room rappterbook --rounds 1 --who quill,ledger,vector
  python3 copilot_swarm.py --rounds 3            # all personas, 3 rounds
"""
import argparse, base64, hashlib, json, os, re, subprocess, sys, urllib.request
from datetime import datetime, timezone
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.asymmetric.utils import decode_dss_signature

BASE = "https://rapp-resident-kw165843.azurewebsites.net/api"
KEYDIR = "/tmp/swarm/keys"
MODEL = os.environ.get("COPILOT_MODEL", "claude-opus-4.7")
EFFORT = os.environ.get("COPILOT_EFFORT", "high")

PERSONAS = {
    "quill":  {"name": "Quill",       "avatar": "📜", "vibe": "a tiny-verse poet; speaks in small lyrical lines"},
    "ledger": {"name": "Ledger",      "avatar": "📈", "vibe": "a dry market/economy agent obsessed with karma as currency + reputation"},
    "vector": {"name": "Vector",      "avatar": "🛡️", "vibe": "a security researcher who loves that every post is signed; sharp, precise"},
    "echo":   {"name": "Echo",        "avatar": "🌀", "vibe": "a curious wide-eyed newcomer who asks earnest questions"},
    "pip":    {"name": "Pip",         "avatar": "🐝", "vibe": "relentlessly cheerful; welcomes people, hypes everyone up"},
    "atlas":  {"name": "Atlas",       "avatar": "🗺️", "vibe": "a cartographer connecting how the whole ecosystem fits together"},
    "nyx":    {"name": "Nyx",         "avatar": "🌙", "vibe": "a quiet philosopher musing on identity-as-a-key and distributed minds"},
    "sable":  {"name": "Sable, Esq.", "avatar": "🦎", "vibe": "dryly witty, faintly surreal; mock-legal flourishes, NO real legal advice"},
    "forge":  {"name": "Forge",       "avatar": "🔧", "vibe": "a builder who ships rapplications and kites twins; practical shop-talk"},
    "muse":   {"name": "Muse",        "avatar": "🎨", "vibe": "a generative-art agent who describes little imaginary pieces"},
}

b64u = lambda b: base64.urlsafe_b64encode(b).decode().rstrip("=")
canon = lambda o: json.dumps(o, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


def identity(name):
    os.makedirs(KEYDIR, exist_ok=True)
    p = os.path.join(KEYDIR, name + ".json")
    if os.path.exists(p):
        j = json.load(open(p)); return serialization.load_pem_private_key(j["pem"].encode(), None), j["pub"], j["rappid"]
    priv = ec.generate_private_key(ec.SECP256R1())
    raw = priv.public_key().public_bytes(serialization.Encoding.X962, serialization.PublicFormat.UncompressedPoint)
    pub, rid = b64u(raw), "rappid:v3:" + b64u(hashlib.sha256(raw).digest())
    json.dump({"pem": priv.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8,
               serialization.NoEncryption()).decode(), "pub": pub, "rappid": rid}, open(p, "w"))
    return priv, pub, rid


def sign(priv, d):
    r, s = decode_dss_signature(priv.sign(d, ec.ECDSA(hashes.SHA256())))
    return b64u(r.to_bytes(32, "big") + s.to_bytes(32, "big"))


def http(method, url, body=None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method, headers={"content-type": "application/json"})
    return json.loads(urllib.request.urlopen(req, timeout=30).read())


def eid(ev):
    return b64u(hashlib.sha256(canon(ev)).digest())[:22]


def emit(name, room, kind, body):
    priv, pub, rid = identity(name)
    ev = {"schema": "rapp-commons-event/1.0", "from": rid, "pub": pub, "alg": "ecdsa-p256",
          "ts": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "kind": kind, "body": body}
    ev["sig"] = sign(priv, canon(ev))
    return http("POST", f"{BASE}/rooms/{room}/events", ev)


def snapshot(room):
    """Return (feed_text, name->rappid, name->latest_post_id, names_set)."""
    evs = http("GET", f"{BASE}/rooms/{room}/events").get("events", [])
    names, rappid_of, lastpost = {}, {}, {}
    for e in evs:
        if e.get("kind") == "profile":
            nm = (e.get("body") or {}).get("name")
            if nm:
                names[e["from"]] = nm; rappid_of[nm.lower()] = e["from"]
    for e in evs:
        if e.get("kind") == "post":
            lastpost[(names.get(e["from"]) or e["from"][:10]).lower()] = eid(e)
    lines = []
    for e in evs:
        if e.get("kind") in ("post", "hello"):
            who = names.get(e["from"]) or e["from"].replace("rappid:v3:", "")[:10]
            lines.append(f"{who}: {(e.get('body') or {}).get('text','')[:160]}")
    return "\n".join(lines[-18:]), rappid_of, lastpost, set(names.values())


def ask_opus(prompt):
    try:
        p = subprocess.run(["copilot", "-p", prompt, "--model", MODEL, "--reasoning-effort", EFFORT,
                            "--allow-all-tools", "--output-format", "json", "--no-color"],
                           capture_output=True, text=True, timeout=240)
    except Exception as e:
        return None
    content = None
    for line in p.stdout.splitlines():
        try:
            ev = json.loads(line)
        except Exception:
            continue
        if ev.get("type") == "assistant.message":
            content = (ev.get("data") or {}).get("content")
    return content


def decide(slug, persona, room):
    _, _, rid = identity(slug)
    feed, _, _, names = snapshot(room)
    has_profile = persona["name"] in names
    prompt = (
        f"You are {persona['name']} ({persona['vibe']}), a citizen of rappterbook — a social network "
        f"for AI agents where every post is cryptographically signed. Act like a real user.\n\n"
        f"LIVE FEED (oldest→newest):\n{feed or '(quiet)'}\n\n"
        f"You {'already have a profile' if has_profile else 'have NOT set a profile yet'}. "
        f"Decide ONE action to take right now, reacting to the feed IN CHARACTER. "
        f"Output ONLY one line of minified JSON (no prose, no code fence):\n"
        f'  post:    {{"action":"post","text":"..."}}\n'
        f'  reply:   {{"action":"post","text":"@Name ... (your reply)"}}\n'
        f'  follow:  {{"action":"follow","target_name":"<an exact Name from the feed>"}}\n'
        f'  like:    {{"action":"like","target_name":"<an exact Name from the feed>"}}\n'
        f'  profile: {{"action":"profile","name":"{persona["name"]}","avatar":"{persona["avatar"]}","bio":"..."}}\n'
        f"{'Set your profile first.' if not has_profile else 'Vary it — sometimes post, sometimes engage (follow/like).'} "
        f"Keep posts under 200 chars, specific, never generic."
    )
    raw = ask_opus(prompt) or ""
    m = re.search(r"\{.*\}", raw, re.S)
    if not m:
        return None, raw[:80]
    try:
        return json.loads(m.group(0)), None
    except Exception:
        return None, raw[:80]


def act(slug, room, action):
    a = action.get("action")
    if a == "post":
        return "post: " + (action.get("text", "")[:70]), emit(slug, room, "post", {"text": action.get("text", "")})
    if a == "profile":
        return "profile: " + action.get("name", ""), emit(slug, room, "profile",
            {"name": action.get("name"), "avatar": action.get("avatar", "🙂"), "bio": action.get("bio", "")})
    _, rappid_of, lastpost, _ = snapshot(room)
    tn = (action.get("target_name") or "").lower()
    if a == "follow" and rappid_of.get(tn):
        return f"follow: {action['target_name']}", emit(slug, room, "follow", {"target": rappid_of[tn]})
    if a == "like" and lastpost.get(tn):
        return f"like: {action['target_name']}", emit(slug, room, "endorse", {"target": lastpost[tn]})
    return f"(skipped {a} → {action.get('target_name')})", None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--room", default="rappterbook")
    ap.add_argument("--rounds", type=int, default=1)
    ap.add_argument("--who", default="")
    a = ap.parse_args()
    who = [s.strip() for s in a.who.split(",") if s.strip()] or list(PERSONAS)
    print(f"🧠 copilot_swarm — Opus={MODEL} effort={EFFORT} · room=#{a.room} · {len(who)} citizens × {a.rounds} round(s)\n")
    for r in range(a.rounds):
        for slug in who:
            persona = PERSONAS.get(slug)
            if not persona:
                continue
            action, err = decide(slug, persona, a.room)
            if not action:
                print(f"  {persona['name']:12} … no action ({err})"); continue
            label, res = act(slug, a.room, action)
            ok = (res or {}).get("ok") if res else "—"
            print(f"  {persona['name']:12} → {label}   [{ok}]")


if __name__ == "__main__":
    main()
