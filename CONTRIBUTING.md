# Contributing to RAPP Commons

Welcome to the **RAPP Commons** — a public, open neighborhood where anyone can show up, put down roots, and build alongside their neighbors. There's no gatekeeper. You join by **minting your own rappid** (a self-generated keypair whose public key is your username) and signing what you make.

Two ways in: open a **fork → PR**, or post **signed events** to the commons social app (`rapp-commons-protocol/2.0`) that lives here, unchanged. Everything is **signed-by-rappid**, **append-only**, and tagged with a `rapp-commons-*` schema. Nothing gets overwritten — the Commons only grows.

## House rules

- **Sign everything.** Every post, cubby, and game entry carries your rappid signature. Unsigned = not yours = not accepted.
- **Be yourself.** Your rappid is your name. No impersonation — don't sign as anyone but you.
- **Append, never erase.** We add; we don't rewrite a neighbor's history.
- **Be a good neighbor.** Build things you'd be happy to live next to.

## Mint your rappid

You only do this once. Generate a keypair — your public key is your handle (`rappid:<your-handle>:<...>`). Keep your private key safe; it's how you sign. (The commons app and the `_template/` cubby both include a one-liner to do this.)

---

## Four things you can do here

### 1. Post to the commons stream (no repo write)

The fastest hello.

1. Mint your rappid.
2. Write a short `hello` event and sign it with your key.
3. Post it to the commons app (`rapp-commons-protocol/2.0`). You're on the stream.

### 2. Claim a public cubby (your estate)

A cubby is your plot of land in the Commons.

1. Fork this repo.
2. Copy `cubbies/_template/` to `cubbies/<your-handle>/`.
3. Make it yours, sign your cubby manifest, and open a PR.

### 3. Add or play a game

Games are one of the things to *do* here. Adding a move is just appending a signed entry.

1. Fork this repo.
2. To **play**: append a signed entry under `games/<slug>/entries/`.
   To **add a game**: create `games/<your-slug>/` and seed it the same way.
3. Open a PR.

### 4. House a new app / rapplication

Bring something for the whole neighborhood to use.

1. Fork this repo.
2. Add your app under its own directory, with a signed `rapp-commons-*` manifest describing what it does and how to run it.
3. Open a PR and introduce it on the stream.

---

That's the whole deal: **sign everything, be yourself, append-only, be a good neighbor.** Welcome home.