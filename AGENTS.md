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
- `src/core/stasis_field.py` — `QuantumStasisField` (spec:
  `stasis_field_protocol.json`): seals the audit Merkle root and re-verifies
  the sealed prefix every heartbeat (appends allowed, alterations raise
  `STASIS_FIELD_BREACH`); encrypts identities per owner (PBKDF2 + SHA-256
  keystream) into a vault committed to an identity Merkle tree (owner key
  required to open a record; denied attempts audited); and runs predictive
  QKD threat analysis on every transaction BEFORE acceptance (`FALSE_COIN`
  for replayed ids/invalid mints, `QKD_DISTURBANCE` for self-transfers/
  low-entropy keys). The drive scans every tx through it and occasionally
  forges a counterfeit to exercise detection.
- API: `GET /api/stasis` returns the field status (seal, Merkle match,
  privacy coverage, identity tree root, threat level + register).
- `ConsensusAlgorithm.finalize_block` auto-corrects transactional violations
  in a block BEFORE validating/finalizing it (fixable errors corrected,
  policy violations flagged). Block hash is recomputed after corrections.
- `src/core/enforcement.py` — `ZeroViolationEnforcement`: pre-acceptance policy
  gate. Every transaction is screened (via `inspect_transaction`) BEFORE the
  ledger; violations are quarantined with reason codes (audit entry
  `VIOLATION_STOPPED`) and never enter the chain. `accepted_violations` is
  structurally 0 while active — reported as the FTC Act §5 control. The drive
  occasionally injects a deliberate self-transfer to prove the gate stops it.
- `src/core/health_monitor.py` — `QuantumHealthMonitor`: probes every consensus
  function every 5 drive ticks (validators, propose/validate/finalize block,
  slashing, block reconciliation, audit chain, Merkle root, stasis field),
  tracking latency/failure streaks per check. Alerts (auto-clearing, history
  kept) are raised for any failed check and — critically —
  `BLOCK_RECONCILIATION_FAILED` / `AUDIT_CHAIN_BROKEN` when a reconciliation
  pass fails (the drive feeds every 20-tick reconciliation report into
  `observe_reconciliation`). The `VIOLATION_DETECTED` warning only fires on
  NEW violations vs the previous pass, so legacy pre-enforcement entries in the
  immutable ledger don't keep a stale alert alive.
- `src/core/compliance.py` — `ComplianceEngine`: maps live controls onto 7 legal
  frameworks (PSD2, GDPR/CCPA, ECOA/Reg B, FHA, CRA, FTC Act §5, SOX §404),
  each verified against live state on request. Fairness monitor applies the
  four-fifths (80%) inclusion rule vs the MEDIAN participant over the last 200
  transactions (median benchmark = robust to sampling noise, still catches
  systematic redlining). Also serves the RIGHTS_CHARTER (business / person /
  ethical standards).
- `src/core/negotiation.py` — `NegotiationLedger`: rights-preserving dispute
  flow. Quarantined items are disputable; structured offers (`release_refund`,
  `resubmit_clean`) settle, `escalate` goes to human review. Every transition
  is audit-logged. Disputing never affects standing.
- Health view: `GET /health` serves `health.html` + `health.js` (dedicated
  monitoring view; polls `/api/health` every 2s and `/api/compliance` every
  6s). API: `GET /api/health` (overall verdict, per-function checks, alerts,
  enforcement status incl. quarantine), `GET /api/compliance` (frameworks,
  fairness, rights, negotiation register), `GET|POST /api/negotiation`
  (`{action: open|propose, ...}`). Both dashboard pages share a `view-nav`.
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
