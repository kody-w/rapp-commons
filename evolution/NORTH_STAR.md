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
