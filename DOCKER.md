# Document Console container

The container runs the local dashboard and processing worker. Mount `input`,
`sorted`, and `docling_json` so documents, JSON, state, and logs survive
restarts. Docling and OnePlus remain external LAN services at their configured
addresses.

```bash
docker compose up -d --build
```

Open `http://localhost:8765`. Add files to `input`, then start processing from
the dashboard. The originals remain in `input`; verified copies go to `sorted`.

Check status:

```bash
docker compose ps
docker compose logs -f document-console
```

The container uses Python 3.12, requests, and pypdf. It has no access to files
outside the three mounted directories.
