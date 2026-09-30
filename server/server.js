'use strict';

/**
 * Pi Nexus Services API — implements the six services from the landing page
 * Services section, every action connected to the QCF-DRIVE quantum
 * consensus function (server/quantum-consensus.js).
 */

const path = require('path');
const express = require('express');
const cors = require('cors');

const QuantumConsensus = require('./quantum-consensus');
const { AnalyticsService } = require('./services/analytics');
const { SecurityService } = require('./services/security');
const { IntegrationService } = require('./services/integrations');
const { AutomationService } = require('./services/automation');
const { PrivacyService } = require('./services/privacy');
const { SupportService } = require('./services/support');

const app = express();
app.use(cors());
app.use(express.json());

// --- Wire services to the quantum consensus engine ---
const consensus = new QuantumConsensus();
const analytics = new AnalyticsService(consensus);
const security = new SecurityService(consensus, analytics);
const integrations = new IntegrationService(consensus);
const automation = new AutomationService(consensus, analytics, security);
const privacy = new PrivacyService(consensus, analytics);
const support = new SupportService(consensus);

function handleError(res, error) {
  res.status(error.status || 500).json({ error: error.message });
}

// --- Static frontend (live source from repo root) ---
const ROOT = path.join(__dirname, '..');
app.get('/', (req, res) => res.sendFile(path.join(ROOT, 'index.html')));
app.get('/services-dashboard.js', (req, res) => res.sendFile(path.join(ROOT, 'services-dashboard.js')));

// --- Quantum consensus engine ---
app.get('/api/consensus', (req, res) => {
  res.json({
    qcf: consensus.qcf,
    branches: consensus.getBranches(),
    stats: consensus.getStats(),
    history: consensus.getLedger(15),
  });
});

app.post('/api/consensus', (req, res) => {
  try {
    const decision = req.body && req.body.decision ? req.body.decision : { label: 'manual consensus test' };
    res.status(201).json(consensus.runConsensusDecision('manual_consensus_test', decision));
  } catch (error) {
    handleError(res, error);
  }
});

// --- Real-Time Analytics ---
app.post('/api/analytics/transactions', (req, res) => {
  try {
    res.status(201).json(analytics.submitTransaction(req.body || {}));
  } catch (error) {
    handleError(res, error);
  }
});

app.get('/api/analytics/metrics', (req, res) => res.json(analytics.getMetrics()));

// --- Enhanced Security ---
app.post('/api/security/scan', (req, res) => {
  try {
    res.json(security.scanTransactions());
  } catch (error) {
    handleError(res, error);
  }
});

// --- Seamless Integration ---
app.get('/api/integrations', (req, res) => res.json({ branches: integrations.list() }));

app.post('/api/integrations/connect', (req, res) => {
  try {
    res.json(integrations.connect(req.body ? req.body.branchId : undefined));
  } catch (error) {
    handleError(res, error);
  }
});

app.post('/api/integrations/disconnect', (req, res) => {
  try {
    res.json(integrations.disconnect(req.body ? req.body.branchId : undefined));
  } catch (error) {
    handleError(res, error);
  }
});

// --- Automated Processes ---
app.post('/api/automation/run', (req, res) => {
  try {
    res.json(automation.run(req.body ? req.body.workflow : undefined));
  } catch (error) {
    handleError(res, error);
  }
});

// --- User Privacy ---
app.get('/api/privacy/requests', (req, res) => res.json({ requests: privacy.list() }));

app.post('/api/privacy/requests', (req, res) => {
  try {
    res.status(201).json(privacy.submit(req.body || {}));
  } catch (error) {
    handleError(res, error);
  }
});

// --- 24/7 Customer Support ---
app.get('/api/support/tickets', (req, res) => res.json({ tickets: support.list() }));

app.post('/api/support/tickets', (req, res) => {
  try {
    res.status(201).json(support.submit(req.body || {}));
  } catch (error) {
    handleError(res, error);
  }
});

const PORT = process.env.PORT || 3000;
app.listen(PORT, '0.0.0.0', () => {
  console.log(`Pi Nexus services API listening on port ${PORT} (quantum consensus engine online)`);
});
