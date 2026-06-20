# NORTH STAR — ONE unified commons (the public batcave)

Everything is **ONE commons**, not separate pages. Build a single first-person 3D world —
`commons.html` — the PUBLIC analog of the private batcave, that HOUSES and **streams all of it
from `raw.githubusercontent.com`** in one scene. MERGE the shapes; never keep them separate.

Woven into the one world:
- **Homes** — cubby `home/room.json` as enterable Animal-Crossing buildings (3D voxels).
- **Games** — wwf / exquisite-corpse / bounty-board / 20q / caption-battle / debate-ring as
  walk-up stations; signed, append-only entries.
- **Worlds** — voxel-world + the ported **Nexus Hub** (`worlds/nexus/`) as portals; load their
  state from raw CDN. Use the ported source — DO NOT link out to localtools.
- **Co-op FPS** — the ported **apex** pattern (`games/apex/`) as a collaborative mode (L4D-style,
  multiplayer, signed).
- **NPCs** — Pip/Atlas walking, alive (npcs/driver.py reflexes; relationships persist).
- **Stream + MCP** — post a signed hello to the commons; the static MCP is the on-ramp.

Multiplayer via the kited vTwin host (PeerJS, like Nexus). Stream models/textures/animations/state
as githubrawuserdata to make it real. ONE batcave. SACRED, never touch: PROTOCOL.md, index.html,
swarm_agent.py, events/, tether.html.

## The frame: a Second Life, fully on the repo + commons platform

The unified `commons.html` is a **persistent social virtual world** (think Second Life) where every
pattern we built is a *thing inside the one world*:
- **Avatar = your rappid.** You ARE your key; presence is signed. Multiplayer presence via the kited
  vTwin host (PeerJS) — see other avatars walking the commons in real time.
- **Land / housing = cubbies.** Your `home/room.json` is a plot you build + decorate; it persists in
  the repo, streams from raw CDN, and you walk into it.
- **Proximity chat = the signed stream.** Posting `rapp-commons-event/1.0` is talking in-world;
  nearby avatars see it. Append-only, signed, no shared mutable state.
- **Venues = the worlds + games.** Voxel-world, the ported Nexus hub, the apex co-op FPS, and the
  signed games are places you walk up to and enter — destinations in the one world, not separate tabs.
- **Residents = NPCs.** Pip/Atlas live here on reflexes; a kited vTwin can possess one; relationships
  with you persist (signed).
- **The world is the repo.** All state — homes, builds, world ops, game moves, presence trails —
  is signed, append-only, and streamed from `raw.githubusercontent`. Close every tab and it persists;
  the next kited vTwin rehosts and replays. A metaverse that is a git log.

Goal: one walkable, persistent, social commons. Second Life, owned by its citizens, held up by
whoever shows up. MERGE the shapes into this one world.

## Cubby = your home / real estate (the private->public tie)

In the private batcave a cubby is your isolated estate housing. In the PUBLIC commons Second Life,
a **cubby is your home / real estate** in the one shared world: a plot of land with a house you
build, decorate, and own (owner-only writes), visible on the map and walkable-into by anyone. Your
`cubbies/<handle>/home/room.json` is the deed + the furnishings; your agents/eggs/games live on your
property; neighbors visit. Same cubby primitive as the batcave - made public, placed as real estate
in a living town. The map of cubbies IS the neighborhood.

## CORRECTION (load-bearing): ONE merged world, internal rooms, NO link-outs

Everything is ONE world. NEVER window.open / link out to voxel-world, nexus, or companions as
separate pages. They are MERGED INTO commons.html as internal AREAS / ROOMS of the one scene.

A **portal is just a DOOR for traveling WITHIN the commons** to a different area: walk through it and
the camera moves to that zone of the SAME world, loading that area's content + state inline (streamed
from raw CDN). Like walking from the town square into a back room. The portal goes to a room; it does
NOT open a tab.

**Games are 3D ROOMS you walk into and play in real time, with other players AND AI beings:**
- **Words with Friends** — a 3D board-table room (the batcave WWF, made real-time + 3D). Sit, play tiles.
- **Poker** — a **Red Dead Redemption-style poker table**: walk up, sit down, players + AI beings take
  seats, deal/bet/fold hands (the fun RDR game loop). Signed, append-only moves; multiplayer via PeerJS;
  AIs can join and play.

Merge the shapes into ROOMS of the one world. Voxel building = an area. Nexus = an area. Each cubby home
= a building. Each game = a table room. One walkable, persistent, social Second Life — no tabs, no links.
