# Document Console

Start with `python dashboard.py`, then open http://127.0.0.1:8765/.
Keep the app local. Click Start to process the current input folder; watching the
folder refreshes the list but does not start new jobs automatically.

Each unique file gets a filename check. Ambiguous names go to Docling and then
content classification. Each successful result is copied immediately, checked
with SHA-256, and recorded. Input originals are never removed.

After an interruption, start again with the same folders and page setting.
New durable checkpoints reuse saved filename decisions, Docling extraction and
classifications. A pending copy is retried without inference. Files changed since
the checkpoint get a new job. Checkpoints from older app versions are not
automatically trusted; those files may be processed again.

`sorted/state.sqlite3` is the durable job store. `sorted/processing.log` persists
logs; `sorted/manifest.jsonl` is an append-only audit of results. Keep these and
`docling_json` together when backing up the workspace. Interrupted copy temporary
files have `.partial` extensions and are not considered finished documents.

Stopping the local process can leave an active request on OnePlus. The next run
checks `/slots` and waits for idle before inference. Unknown server state blocks
new requests. Streaming must finish before the next inference starts.

The app checks copy integrity, not classification truth. Review categories before
deleting any originals. Power-loss recovery reduces lost work but cannot guarantee
against disk failure; retain a separate backup of important documents.

Validation: `python -m unittest test_recovery.py`.
