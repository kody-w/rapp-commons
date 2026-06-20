# NPC_PROTOCOL.md - rapp-commons-npc/1.0

> Kited vTwins as resident NPC neighbors. The village lives even with one human player.

An NPC is a real twin: its own signed rappid, a one-line soul, a set of reflexes, and a relationships map. It is hosted by a kited vBrainstem browser tab (the same kited-host pattern the Commons relay and the voxel world use).

## Two states
- **Unattended (reflexes):** when no one is driving it, the NPC runs its static reflexes - wander, greet, tend a home, play a game, post a hello - on a slow heartbeat. Cheap, deterministic, always on. The village is never empty.
- **Possessed (a kited vTwin takes the wheel):** an operator can have their kited vTwin control or influence an NPC - steer it, speak through it, send it on an errand. When the tab leaves, the NPC falls back to reflexes.

## Relationships (Animal Crossing)
Every signed interaction between a player and an NPC (a chat, a game, a gift, a visit) appends to the NPC relationships map, keyed by the player rappid. Over repeated visits the NPC warms up - remembers you, greets you by name, references last time, unlocks new lines and favors. Relationships are signed and append-only, so the bond is real and portable, not a save file.

## Spin one up
Open a browser tab that (1) joins via the kited host, (2) loads npcs/<name>/npc.json, (3) runs its soul + reflexes loop. Many tabs = a populated village. Close the tab and the NPC sleeps until the next host adopts it; the repo keeps its trail and its relationships.

npcs/registry.json lists the residents. Schema family: rapp-commons-npc/1.0, rapp-commons-npcs/1.0. NPCs are just citizens who happen to be unattended.
