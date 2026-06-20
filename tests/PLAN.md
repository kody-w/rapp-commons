# Plan — the unified RAPP Commons (one walkable Second Life world)

## Goal
ONE first-person 3D world (`commons.html`), the public-batcave Second Life, where everything is an
**internal area/room** — no link-outs. Streams all state from `raw.githubusercontent`.

## The application (acceptance criteria → tests)
1. **One world, no link-outs.** `commons.html` contains **zero `window.open`**; portals are *internal*
   travel — walking a portal moves the camera to that area of the same scene (`commonsAgent.goto`),
   never a new tab. → `test_commons.py::no_link_outs`, `::portal_is_internal`
2. **Avatar body / coordinates.** `window.commonsAgent` exposes `where/teleport/walk/face/nearby/
   goto/enter/interact/say/list` that drive the real camera + interactions. → `::coordinate_api`,
   `::teleport_moves`, `::nearby_lists`
3. **Areas merged in.** `commonsAgent.list()` includes the world areas (square, voxel, nexus) AND the
   game rooms `words-with-friends` and `poker`. → `::areas_present`, `::game_rooms_present`
4. **Words with Friends room** — a 3D board-table area you walk into; signed append-only moves. → `::wwf_room`
5. **Poker room (Red Dead style)** — a 3D table you sit at; deal/bet/fold; players + AI beings seat;
   signed hands; a runnable `games/poker/engine.py`. → `::poker_room`, `test_data.py::poker_engine`
6. **Signed social.** the post HUD signs a `rapp-commons-event/1.0` hello (WebCrypto). → `::signed_post`
7. **NPCs + multiplayer.** Pip/Atlas present; PeerJS presence; `tools/spawn_beings.py` populates it. → `::npcs`, `test_data.py::spawn_beings_exists`
8. **Data integrity.** all JSON valid; manifest refs exist; sacred commons-app files untouched. → `test_data.py::*`

## Process
1. Write tests (this dir). 2. Build via the two engines until `tests/run.sh` is fully green.
3. Publish: push to **kody-w/rapp-commons** (branch → merge to `main` so it is live on Pages).
4. Notify Kody with the live URL to test.

## Hard rule
Push ONLY to `kody-w/rapp-commons`. Never touch the brainstem repo. Sacred (never edit):
`PROTOCOL.md, index.html, swarm_agent.py, events/, tether.html, copilot_swarm.py, twin_chat_agent.py`.
