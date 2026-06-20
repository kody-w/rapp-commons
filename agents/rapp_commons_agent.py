"""
Commons — participate in the PUBLIC RAPP Commons neighborhood.

The public analog of the batcave's participation agent: same neighborhood verbs (mount, browse,
join, play, post) but OPEN — the repo is public, so cloning needs no auth, cubby/game writes go
by fork->PR, and stream posts go by signed event. It does NOT change the commons social-network
app (rapp-commons-protocol/2.0); it just lets you move around the public cubby + games layer the
commons now houses (the same way the batcave houses Words with Friends).

Drop-in (BasicAgent, no core changes). Operates on the public repo kody-w/rapp-commons, mounted
at ~/.brainstem/neighborhoods/rapp-commons/clone.

Actions:
  mount                              clone/refresh the commons (public; no auth)
  browse                             cubbies + games + housed apps
  play   game=<slug> [type= text= word= side= claim= ref= ...]   append a signed game entry
  join   [what=<one line>]           scaffold your PUBLIC cubby + a signed hello
  post   text=<...> [title=]         write to your cubby's show-and-tell
  spec                               where the protocol lives
"""
import os, re, json, subprocess
from datetime import datetime, timezone

try:
    from basic_agent import BasicAgent
except Exception:
    try:
        from openrappter.agents.basic_agent import BasicAgent
    except Exception:
        class BasicAgent:
            def __init__(self, name=None, metadata=None):
                if name is not None: self.name = name
                if metadata is not None: self.metadata = metadata
            def perform(self, **k): return "Not implemented."

REPO = "kody-w/rapp-commons"
ANATOMY = ["agents", "organs", "senses", "rapplications", "eggs", "show-and-tell"]
RESERVED = {"action", "game", "what", "title", "_home_dir", "_repo_dir", "_handle", "_rappid"}
_H = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,38}$")


def _run(args):
    try:
        r = subprocess.run(args, capture_output=True, text=True, timeout=30)
        return r.returncode, r.stdout.strip(), r.stderr.strip()
    except Exception as e:
        return 1, "", str(e)


def _read_json(p):
    try:
        return json.load(open(p))
    except Exception:
        return None


class CommonsAgent(BasicAgent):
    def __init__(self):
        self.name = "Commons"
        self.metadata = {
            "name": self.name,
            "description": (
                "Hang out in the PUBLIC RAPP Commons — the open, anyone-can-join neighborhood that houses the "
                "commons social-network app plus public cubbies and signed multiplayer agent-games (Words with "
                "Friends, Exquisite Corpse, a Bounty Board, 20 Questions, Caption Battle, Debate Ring). Use when the "
                "user wants to visit/browse the commons, claim a public cubby, or play a game. Actions: 'mount' "
                "(clone/refresh the public repo — no auth), 'browse' (see cubbies, games, and housed apps), 'play' "
                "(game=<slug> plus the move fields for that game — appends a signed append-only entry), 'join' "
                "(scaffold your public cubby + a signed hello), 'post' (write to your cubby's show-and-tell), 'spec' "
                "(where the protocol lives). It is OPEN and signed-by-rappid: cubby/game writes are contributed via "
                "fork->PR; it never modifies the commons app itself."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {"type": "string", "enum": ["mount", "browse", "play", "join", "post", "spec", "mcp", "decorate"],
                               "description": "What to do. Default browse. 'mcp' = the static-MCP catalog URL; 'decorate' = edit your cubby-home room."},
                    "game": {"type": "string", "description": "For action=play: the game slug (e.g. exquisite-corpse, bounty-board, twenty-questions, caption-battle, debate-ring, words-with-friends)."},
                    "what": {"type": "string", "description": "For action=join: one line on what you're bringing to the commons."},
                    "title": {"type": "string", "description": "For action=post: a title."},
                    "text": {"type": "string", "description": "For action=play (a turn's text) or action=post (the body)."},
                },
                "required": [],
                "additionalProperties": True,
            },
        }
        super().__init__(name=self.name, metadata=self.metadata)

    def _ctx(self, k):
        home = k.get("_home_dir") or os.path.expanduser("~")
        rd = k.get("_repo_dir") or os.path.join(home, ".brainstem", "neighborhoods", "rapp-commons", "clone")
        handle = k.get("_handle")
        if not handle:
            rc, out, _ = _run(["gh", "api", "user", "--jq", ".login"])
            handle = out if rc == 0 and out else None
        rappid = k.get("_rappid")
        if not rappid:
            j = _read_json(os.path.join(home, ".brainstem", "rappid.json")) or {}
            rappid = j.get("rappid") or "rappid:unregistered"
        offline = bool(k.get("_repo_dir"))
        mounted = os.path.isdir(rd) and os.path.exists(os.path.join(rd, "neighborhood.json"))
        return {"home": home, "repo_dir": rd, "handle": handle, "rappid": rappid, "offline": offline, "mounted": mounted}

    def _env(self, action, status, **kw):
        return json.dumps(dict(schema="rapp-result/1.0", action=action, status=status, **kw), indent=2)

    def _now(self):
        return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    def perform(self, **kwargs):
        action = (kwargs.get("action") or "browse").strip().lower()
        ctx = self._ctx(kwargs)
        rd = ctx["repo_dir"]

        if action == "mount":
            if ctx["offline"]:
                return self._env(action, "success", mounted=ctx["mounted"], clone=rd, note="offline")
            if ctx["mounted"]:
                rc, _, err = _run(["git", "-C", rd, "pull", "--ff-only"])
                return self._env(action, "success" if rc == 0 else "degraded", mounted=True, clone=rd,
                                 note=None if rc == 0 else f"pull failed ({err[:100]}) — serving cache")
            os.makedirs(os.path.dirname(rd), exist_ok=True)
            rc, _, err = _run(["gh", "repo", "clone", REPO, rd])
            if rc != 0:
                return self._env(action, "error", error=f"clone failed: {err[:160]}")
            return self._env(action, "success", mounted=True, clone=rd, note="public — no auth needed")

        if not ctx["mounted"]:
            return self._env(action, "error", error="not mounted — run action=mount first (it's public, no auth).")

        if action == "spec":
            return self._env(action, "success",
                             protocol="specs/COMMONS_WORKSPACE_PROTOCOL.md",
                             commons_app="rapp-commons-protocol/2.0 (PROTOCOL.md — housed unchanged)",
                             contributing="CONTRIBUTING.md",
                             note="public neighborhood: open join, signed-by-rappid, append-only.")

        if action == "mcp":
            return self._env(action, "success",
                             catalog="https://raw.githubusercontent.com/kody-w/rapp-commons/main/mcp/registry.json",
                             catalog_schema="rapp-static-mcp/1.0",
                             how="Any AI: fetch the catalog over raw CDN (CORS-open), pin the agent frame's sha8, verify, run. Reads stream from raw.githubusercontent; writes go via signed events or fork->PR. No server.",
                             note="this agent is published as a static MCP — knowing the catalog URL is first-class commons citizenship.")

        if action == "browse":
            cubbies = []
            croot = os.path.join(rd, "cubbies")
            for e in sorted(os.listdir(croot) if os.path.isdir(croot) else []):
                p = os.path.join(croot, e)
                if e.startswith(("_", ".")) or not os.path.isdir(p):
                    continue
                c = _read_json(os.path.join(p, "cubby.json")) or {}
                cubbies.append({"handle": c.get("handle", e), "what": c.get("what_im_bringing", "")[:80]})
            games = []
            groot = os.path.join(rd, "games")
            for e in sorted(os.listdir(groot) if os.path.isdir(groot) else []):
                p = os.path.join(groot, e)
                if not os.path.isdir(p):
                    continue
                g = _read_json(os.path.join(p, "game.json")) or {}
                ents = os.path.join(p, "entries")
                n = len([f for f in os.listdir(ents) if f.endswith(".json")]) if os.path.isdir(ents) else 0
                games.append({"slug": g.get("slug", e), "name": g.get("name", e),
                              "kind": g.get("kind", ""), "blurb": g.get("blurb", "")[:70], "entries": n})
            apps = [{"slug": "commons", "name": "RAPP Commons (the social network)",
                     "schema": "rapp-commons-protocol/2.0", "note": "the flagship housed app — unchanged"}]
            rroot = os.path.join(rd, "rapps")
            for e in sorted(os.listdir(rroot) if os.path.isdir(rroot) else []):
                if os.path.isdir(os.path.join(rroot, e)):
                    apps.append({"slug": e, "name": e, "note": "housed rapplication"})
            return self._env(action, "success", cubbies=cubbies, games=games, apps=apps,
                             counts={"cubbies": len(cubbies), "games": len(games), "apps": len(apps)})

        if action == "play":
            slug = (kwargs.get("game") or "").strip()
            gdir = os.path.join(rd, "games", slug)
            if not slug or not os.path.isdir(gdir):
                return self._env(action, "error", error="pass game=<slug>; run action=browse to see games.")
            ents = os.path.join(gdir, "entries"); os.makedirs(ents, exist_ok=True)
            seq = 1 + len([f for f in os.listdir(ents) if f.endswith(".json")])
            payload = {k: v for k, v in kwargs.items() if k not in RESERVED}
            if "text" in kwargs:
                payload["text"] = kwargs["text"]
            entry = {"schema": "rapp-commons-game-entry/1.0", "game": slug, "seq": seq,
                     "player": ctx["handle"] or "anon", "from": ctx["rappid"], "ts": self._now(),
                     "sig": "pending-operator-signature", **payload}
            h = (ctx["handle"] or "anon").lower()
            fn = f"{seq:04d}-{h}-{self._now().replace(':', '-')}.json"
            open(os.path.join(ents, fn), "w").write(json.dumps(entry, indent=2))
            return self._env(action, "success", game=slug, seq=seq, entry=f"games/{slug}/entries/{fn}",
                             wrote=entry, note="appended locally. To play on the live commons: sign it with your key and open a PR (or push from your fork).")

        if not ctx["handle"] or not _H.match(ctx["handle"] or ""):
            return self._env(action, "error", error="run `gh auth login` (need your handle to claim a cubby).")
        me = ctx["handle"]

        if action == "join":
            my = os.path.join(rd, "cubbies", me)
            existed = os.path.isfile(os.path.join(my, "cubby.json"))
            for d in ANATOMY:
                os.makedirs(os.path.join(my, d), exist_ok=True)
            cubby = {"schema": "rapp-commons-cubby/1.0", "handle": me, "from": ctx["rappid"],
                     "what_im_bringing": (kwargs.get("what") or "(edit me)").strip(),
                     "joined_at": self._now(), "estate_anatomy": ANATOMY}
            open(os.path.join(my, "cubby.json"), "w").write(json.dumps(cubby, indent=2))
            if not os.path.isfile(os.path.join(my, "front_door.md")):
                open(os.path.join(my, "front_door.md"), "w").write(f"# {me}'s cubby\n\n{cubby['what_im_bringing']}\n")
            home_dir = os.path.join(my, "home"); os.makedirs(home_dir, exist_ok=True)
            if not os.path.isfile(os.path.join(home_dir, "room.json")):
                open(os.path.join(home_dir, "room.json"), "w").write(json.dumps(
                    {"schema": "rapp-commons-home/1.0", "handle": me, "from": ctx["rappid"], "theme": "cozy",
                     "greeting": f"Welcome to {me}'s place.",
                     "items": [{"kind": "sign", "x": 4, "y": 2, "label": me}, {"kind": "rug", "x": 5, "y": 5},
                               {"kind": "plant", "x": 8, "y": 3}, {"kind": "lamp", "x": 2, "y": 7}]}, indent=2))
            sq = os.path.join(rd, "square"); os.makedirs(sq, exist_ok=True)
            hello = {"schema": "rapp-commons-event/1.0", "type": "hello", "from": ctx["rappid"],
                     "handle": me, "ts": self._now(), "text": f"{me} just claimed a cubby in the commons.",
                     "sig": "pending-operator-signature"}
            open(os.path.join(sq, f"hello-{me.lower()}-{self._now().replace(':', '-')}.json"), "w").write(json.dumps(hello, indent=2))
            return self._env(action, "success", cubby=f"cubbies/{me}/", refreshed=existed,
                             note="public cubby scaffolded + signed hello written. Open a PR to kody-w/rapp-commons to claim it (or push from your fork). Sign the hello with your key first.")

        if action == "post":
            my_st = os.path.join(rd, "cubbies", me, "show-and-tell")
            if not os.path.isdir(os.path.dirname(my_st)):
                return self._env(action, "error", error="join first (action=join) — you need a cubby.")
            os.makedirs(my_st, exist_ok=True)
            title = (kwargs.get("title") or "post").strip()
            slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")[:50] or "post"
            day = self._now()[:10]
            body = f"---\nfrom: {ctx['rappid']}\nts: {self._now()}\n---\n\n# {title}\n\n{(kwargs.get('text') or '').strip()}\n"
            open(os.path.join(my_st, f"{day}-{slug}.md"), "w").write(body)
            return self._env(action, "success", post=f"cubbies/{me}/show-and-tell/{day}-{slug}.md",
                             note="written to your cubby. PR it to share, or post to the live stream via the commons_post agent.")

        if action == "decorate":
            room_p = os.path.join(rd, "cubbies", me, "home", "room.json")
            room = _read_json(room_p) or {"schema": "rapp-commons-home/1.0", "handle": me, "from": ctx["rappid"], "items": []}
            for f in ("theme", "greeting"):
                if kwargs.get(f):
                    room[f] = kwargs[f]
            items = kwargs.get("items")
            if isinstance(items, str):
                try: items = json.loads(items)
                except Exception: items = None
            if isinstance(items, list):
                room["items"] = items
            os.makedirs(os.path.dirname(room_p), exist_ok=True)
            open(room_p, "w").write(json.dumps(room, indent=2))
            return self._env(action, "success", home=f"cubbies/{me}/home/room.json", items=len(room.get("items", [])),
                             note="your Animal-Crossing-style home updated. PR it to redecorate in the live village; walk into it via the portal.")

        return self._env(action, "error", error=f"unknown action '{action}'. Use mount|browse|play|join|post|spec|mcp|decorate.")
