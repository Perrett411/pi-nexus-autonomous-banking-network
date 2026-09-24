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
- `src/core/analytics.py` — `AuditAnalytics`: time-buckets the audit trail into
  chart-ready series (per-minute transactions/consensus/volume) and detects
  anomalies: transaction spikes (>2σ vs average, min 3 tx), amount outliers
  (>3σ), invalid amounts, self-transfers, forks and slashing.
- `src/core/reconciliation.py` — `QuantumReconciler` + `inspect_transaction`/
  `correct_transaction`: scans the audit trail for transactional violations,
  auto-corrects fixable ones (logged as `TRANSACTION_CORRECTED` for
  transparency), flags self-transfers (`VIOLATION_FLAGGED` — not safely
  auto-correctable), verifies finalized block state (hash + linkage) and
  issues the compliance report. Repeat runs are idempotent — the audit log's
  payload dedup absorbs identical correction records.
- `ConsensusAlgorithm.finalize_block` auto-corrects transactional violations
  in a block BEFORE validating/finalizing it (fixable errors corrected,
  policy violations flagged). Block hash is recomputed after corrections.
- API: `GET /api/events?after=<index>` returns audit stats plus entries after
  the given index (last 200 when `after=-1`). The dashboard polls this every
  1.5s. `GET /api/analytics` returns chart series + anomalies (polled every
  6s). `GET|POST /api/reconciliation` runs a compliance pass and returns the
  report; the drive thread also auto-reconciles every 20 ticks. All
  engine/audit access is guarded by `ENGINE_LOCK`.
- NOTE: the audit log deep-copies payloads on append — never hand it an
  object you intend to mutate later (in-place mutation would break the
  hash chain).
- Frontend renders everything via `textContent`/`createElement` — never
  `innerHTML` (XSS policy for on-chain data; see security fixes in
  `coin/Eonix`, `smart_contracts`, AstralPlane).

## Verify it works

```
curl -s http://localhost:3000/                    # dashboard HTML
curl -s 'http://localhost:3000/api/events?after=-1' | python3 -m json.tool
```

`total` should grow between calls; `stats.chain_intact` must be `true`.
