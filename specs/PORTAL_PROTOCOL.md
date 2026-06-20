# PORTAL_PROTOCOL.md — `rapp-portal/1.0`

> Portal worlds in the RAPP Commons. The public analog of "housed apps," for things you *step into* (3D worlds, voxel builds, holographic companions).

## The split
A **portal world** separates **code** from **data**:

- **code (the surface)** — a self-contained HTML app at a public `surface_url` (e.g. on GitHub Pages). It never has to live in this repo.
- **data (the state)** — housed *here*, in the commons repo, under `games/<slug>/state/`, **streamed for free over `raw.githubusercontent.com`**, append-only and **signed-by-rappid**.

## How it loads — the portal iframe
`portal.html` is the hub. For each world in [`worlds.json`](../worlds.json) it:

1. opens `surface_url` in a **sandboxed iframe** (`allow-scripts allow-same-origin allow-pointer-lock allow-fullscreen`),
2. appends `?state=<raw URL of games/<slug>/state/>&commons=<raw base>` so the app can fetch its world data directly from the public repo,
3. `postMessage`s the housed state object in (`{type:'rapp-portal/1.0', world, state, commons}`) for apps that listen.

So the app's **bytecode loads from its surface, its world streams from the commons repo's raw CDN** — no server. Anyone forks the repo to fork a world; anyone PRs a signed file under `state/` to add a scene, a build, or a companion.

## Declaring a world
Add an entry to `worlds.json` (`rapp-portal-registry/1.0`) and a `games/<slug>/` with a `game.json` (`kind: realtime-world | portal-hub | portal-app`, `surface_url`, `state_dir`) + a `state/` folder. That's it — it shows up in the portal hub and the `Commons` agent's `portal` action.

Schema family: `rapp-portal/1.0` · `rapp-portal-registry/1.0` · `rapp-portal-state/1.0`. The commons social-network app is unchanged; portals are just another thing the commons houses.
