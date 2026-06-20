#!/usr/bin/env python3
"""build.py - regenerate mcp/registry.json from mcp/manifest.json (rapp-static-mcp/1.0).
The ONLY build step. Idempotent stable-write: commits only real changes. A profile of rapp-static-api/1.0."""
import json, hashlib, os
HERE=os.path.dirname(os.path.abspath(__file__)); ROOT=os.path.dirname(HERE)
man=json.load(open(os.path.join(HERE,"manifest.json")))
b=open(os.path.join(ROOT,man["agent_frame"]),"rb").read(); h=hashlib.sha256(b).hexdigest()
reg={"schema":"rapp-static-mcp/1.0","profile_of":"rapp-static-api/1.0","name":man["name"],"title":man["title"],
 "neighborhood_rappid":man["neighborhood_rappid"],"raw_base":man["raw_base"],"description":man["description"],
 "how_to_connect":man["how_to_connect"],
 "agent_frame":{"path":man["agent_frame"],"raw_url":man["raw_base"]+man["agent_frame"],"sha256":h,"sha8":h[:8],"bytes":len(b)},
 "tools":man["tools"]}
new=json.dumps(reg,indent=2)+"\n"; out=os.path.join(HERE,"registry.json")
old=open(out).read() if os.path.exists(out) else None
print("no change" if new==old else "wrote "+out)
open(out,"w").write(new)
