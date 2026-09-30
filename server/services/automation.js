'use strict';

/** Automated Processes service — workflows executed under quantum consensus. */

const { publicTx } = require('./analytics');

class AutomationService {
  constructor(consensus, analytics, security) {
    this.consensus = consensus;
    this.analytics = analytics;
    this.security = security;
  }

  run(workflow) {
    switch (workflow) {
      case 'automated_settlement':
        return this.automatedSettlement();
      case 'compliance_report':
        return this.complianceReport();
      case 'fraud_sweep':
        return this.fraudSweep();
      default: {
        const error = new Error("workflow must be one of: automated_settlement, compliance_report, fraud_sweep");
        error.status = 400;
        throw error;
      }
    }
  }

  /** Settles all confirmed, non-quarantined transactions (consensus-gated batch). */
  automatedSettlement() {
    const eligible = this.analytics.transactions.filter(
      (t) => t.status === 'confirmed' && t.securityStatus !== 'quarantined' && t.settlementStatus === 'pending'
    );
    const volume = eligible.reduce((sum, t) => sum + t.amount, 0);
    const record = this.consensus.runConsensusDecision('automated_settlement', {
      transactionCount: eligible.length,
      volume,
    });
    let settled = [];
    if (record.consensusPassed) {
      settled = eligible.map((t) => {
        t.settlementStatus = 'settled';
        return publicTx(t);
      });
    }
    return {
      workflow: 'automated_settlement',
      consensus: record,
      executed: record.consensusPassed,
      settledCount: settled.length,
      volume,
      transactions: settled,
    };
  }

  /** Generates a compliance report; publication is consensus-gated. */
  complianceReport() {
    const metrics = this.analytics.getMetrics();
    const report = {
      generatedAt: new Date().toISOString(),
      totalTransactions: metrics.totalTransactions,
      confirmed: metrics.confirmed,
      rejected: metrics.rejected,
      totalVolume: metrics.totalVolume,
      volumeByCurrency: metrics.volumeByCurrency,
      consensusEngineStats: metrics.consensus,
    };
    const record = this.consensus.runConsensusDecision('compliance_report_publication', {
      totalTransactions: report.totalTransactions,
      totalVolume: report.totalVolume,
    });
    return { workflow: 'compliance_report', consensus: record, published: record.consensusPassed, report };
  }

  /** Runs a fraud sweep across transactions (per-item consensus validation). */
  fraudSweep() {
    const scan = this.security.scanTransactions();
    const record = this.consensus.runConsensusDecision('fraud_sweep_execution', {
      flaggedCount: scan.flaggedCount,
      quarantined: scan.quarantined,
    });
    return {
      workflow: 'fraud_sweep',
      consensus: record,
      executed: record.consensusPassed,
      scan,
    };
  }
}

module.exports = { AutomationService };
