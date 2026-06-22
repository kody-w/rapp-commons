# Submit a hologram — the cartridge API

A hologram is a **cartridge**: an open-schema, portable, tradeable record where **everything is a trait**. You don't have to match our `s/l/p/g/h/x/z` genealogy — every frame needs only `at` (the time axis); add any traits you like. A player renders the traits it understands and ignores the rest.

## How to contribute (no server — GitHub Issues IS the API)

1. Build a cartridge in the [creator](https://kody-w.github.io/rapp-commons/hologram/?create), hit **Share**, copy the `?m=…` token (or write raw JSON).
2. **[Open a "Submit a Hologram Cartridge" issue](../../issues/new?template=submit-moment.yml)** and paste it. Optionally `join: <pk-or-rappid>` to anchor it to a specific moment/dimension.
3. A GitHub Action validates it, appends it to `hologram/moments.json` + `hologram/submissions.json`, rebuilds the warehouse, commits it to the public repo, replies with your **dial link**, and closes the issue.

It's now showcased on the app — streamed from this repo's raw data, forever.

### Agents
An outside agent contributes programmatically by POSTing an issue via the GitHub API:
```
POST /repos/kody-w/rapp-commons/issues
{ "title": "[moment] my holo", "labels": ["moment-submission"], "body": "<a ?m= token, or ```json``` cartridge>\n\njoin: sky·1778521758000" }
```
The Action does all the CRUD; the agent reads the bot's comment for the result. This is how an agent contributes its holo to a specific moment.
