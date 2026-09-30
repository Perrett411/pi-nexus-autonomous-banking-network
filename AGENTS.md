# Base44 Development Guide

## Overview
This is the **Pi Nexus Autonomous Banking Network** — a large monorepo with many sub-projects (blockchain, AI, banking, etc.). The primary web entry point is `index.html`, a static landing page served on port 3000.

## Running the App
```bash
docker compose -f docker-compose.base44.yml up -d
```
- Web entry point: `http://localhost:3000` (serves `index.html` via nginx)
- No build step required — `index.html` uses CDN-loaded Tailwind CSS and Font Awesome
- After editing `index.html`, call `reload_preview` to see changes (static files, no HMR)

## Key Structure
- `index.html` — main landing page (static, Tailwind CSS via CDN) + Live Services Dashboard section
- `services-dashboard.js` — frontend JS building the six service panels (talks to `/api/*`)
- `server/` — Node.js/Express backend (single origin: serves the frontend + API on port 3000)
  - `server/quantum-consensus.js` — QCF-DRIVE quantum consensus engine (JS port of `simulate_quantum_consensus_decision` from `quantum_nexus_integration/quantum_ai_security_guardian.py`: GHZ entanglement emulation, 0.67 Byzantine threshold, branch nodes as validators, consensus ledger)
  - `server/services/` — the six services, each consensus-gated: `analytics.js`, `security.js` (AML scan), `integrations.js` (branch connect/disconnect), `automation.js` (settlement/compliance/fraud workflows), `privacy.js` (GDPR requests), `support.js` (AI tickets)
  - `server/server.js` — wires services to the consensus engine and exposes `/api/*`
- `app/` — Python Flask app (many broken imports, not currently used for the web entry point)
- `api/` — mixed Python/JS API definitions
- `frontend/src/` — React app (no package.json, not currently built)
- `blockchain_integration/` — blockchain platform code (Node.js)
- Many sub-project directories under `projects/`, `pi-nexus-*`, etc.

## Services API
- `GET/POST /api/consensus` — engine info / run a consensus decision
- `POST /api/analytics/transactions`, `GET /api/analytics/metrics`
- `POST /api/security/scan`
- `GET /api/integrations`, `POST /api/integrations/connect|disconnect`
- `POST /api/automation/run` (`automated_settlement` | `compliance_report` | `fraud_sweep`)
- `GET/POST /api/privacy/requests` (`data_export` | `right_to_be_forgotten`)
- `GET/POST /api/support/tickets`

State is in-memory (no database). App state resets on container restart.

## Known Issues
- `Dockerfile` references `manage.py` which does not exist at repo root
- `app/main.py` has many broken imports (services, utils, blockchain modules don't exist)
- `docker-compose.yml` (original) maps port 3000 but Dockerfile exposes 8000
- `frontend/src/` has no `package.json` — React app can't be built standalone
- Root `package.json` says `start: "node index.js"` but no `index.js` exists at root

## Notes
- The app is a static landing page; no database or external services are required to run
- `nexus-x-aibank.com` domain does not resolve (DNS not configured) — this is a domain registration issue, not a code issue
- `nexus-x-aibank-crypto.base44.app` is a separate Base44-published app
