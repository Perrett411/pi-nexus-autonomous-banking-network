# Base44 Dev Environment

## What this app is
A Node.js/Express API server (`app.js`) for a decentralized banking platform.
The server listens on port 3000 and exposes endpoints (`/create-account`,
`/deposit-funds`, `/withdraw-funds`, `/get-balance`) backed by
`blockchain_integration/banking_platform.js`.

## Why it failed to start (commit 2c363339d)
The merge commit changed `app.js` to self-start only when run directly
(`if (require.main === module)`), but `package.json`'s start script still
pointed to `node index.js` — and **`index.js` does not exist** in the repo.
Running `node index.js` failed with "Cannot find module".

## Fix applied
- `package.json` start script changed from `node index.js` to `node app.js`
  (the real entry point with the self-start guard).

## How to run
```
docker compose -f docker-compose.base44.yml up -d
```
- Base image: `node:22-slim` with the repo bind-mounted at `/app`.
- `npm ci` runs on startup from `package-lock.json`, then `nodemon app.js`
  for live reload.
- Port 3000 is the web entry point.

## Known limitations (pre-existing, not introduced by this fix)
- `BankingPlatform` only implements `createAccount`; calling `/get-balance`,
  `/deposit-funds`, or `/withdraw-funds` throws `TypeError` (stub methods
  missing) and crashes the process. Nodemon restarts on the next file change.
- `app.js` does not register `express.json()` middleware, so `req.body` is
  undefined on POST routes.
- No root (`/`) route is defined — `GET /` returns 404. The healthcheck
  treats any status < 500 as healthy.

## Verification
- `docker compose ps` shows the app service as `healthy`.
- `curl http://localhost:3000/` returns HTTP 404 (server is responding).
