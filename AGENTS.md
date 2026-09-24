# AGENTS.md

## Running the app (Base44 sandbox)

The preview shows the **Quantum Nexus Protocol live dashboard**:

```
docker compose -f docker-compose.base44.yml up -d
```

- Single service `dashboard` (python:3.12-slim, repo bind-mounted) runs
  `QuantumNexusProtocol/src/frontend/dashboard_server.py` (Flask, port 3000).
- Flask dependencies (`pip install flask`) install at container startup —
  first boot takes a few extra seconds.
- The Flask reloader watches `.py` files: edits to `dashboard_server.py` or
  anything under `src/core/` restart the server automatically. Frontend
  files (html/js/css) are re-read per request — just refresh the browser.

## Architecture (quantum function drive dashboard)

- `src/core/audit_log.py` — `QuantumAuditLog`: hash-chained JSONL audit trail
  with payload dedup and a Merkle root. Persists to `src/core/audit_log.jsonl`;
  the chain continues across restarts. Duplicate payloads are silently ignored.
- `src/core/consensus.py` — `ConsensusAlgorithm`: accepts an `audit_log` and
  auto-records validators, block proposals/finalizations, slashing and forks.
- `src/frontend/dashboard_server.py` — Flask server. A background thread (the
  "quantum function drive") generates transactions and consensus events. It is
  deliberately started only in the reloader child
  (`WERKZEUG_RUN_MAIN == 'true'`) so it never runs twice.
- API: `GET /api/events?after=<index>` returns audit stats plus entries after
  the given index (last 200 when `after=-1`). The dashboard polls this every
  1.5s. All engine/audit access is guarded by `ENGINE_LOCK`.
- Frontend renders everything via `textContent`/`createElement` — never
  `innerHTML` (XSS policy for on-chain data; see security fixes in
  `coin/Eonix`, `smart_contracts`, AstralPlane).

## Verify it works

```
curl -s http://localhost:3000/                    # dashboard HTML
curl -s 'http://localhost:3000/api/events?after=-1' | python3 -m json.tool
```

`total` should grow between calls; `stats.chain_intact` must be `true`.
