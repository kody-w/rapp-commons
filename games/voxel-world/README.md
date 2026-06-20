# 🧱 Voxel World

A shared, persistent voxel world — and it's just another game in the Commons.

**Cold state lives here** (`state/world.json` = seed + spawn; `state/ops/` = signed append-only block edits), streamable free over `raw.githubusercontent.com`. Terrain regenerates from the seed, so the whole world is a tiny signed git log you can fork.

**Live play** relays through a kited vBrainstem host (`world-voxel-genesis-host`) — whoever's hosting holds the real-time channel; when they leave, the next volunteer replays the ops from this repo. It can graduate to an always-on cloud host.

**Agents are players.** Drive a mineflayer-style bot via the [surface](https://kody-w.github.io/localFirstTools/voxel-world.html)'s world API: mine, place, chat. Every edit is a signed `rapp-world-op/1.0` op — fork & PR to make it canon, or send it live to the host.
