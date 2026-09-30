'use strict';

/** Enhanced Security service — AML threat scanning validated by quantum consensus. */

const { publicTx } = require('./analytics');

const AML_SUSPICIOUS_THRESHOLD = 10000; // USD-equivalent (from compliance rules)

class SecurityService {
  constructor(consensus, analytics) {
    this.consensus = consensus;
    this.analytics = analytics;
    this.lastScan = null;
  }

  /**
   * Scans confirmed transactions against AML rules. Every flagged
   * transaction is put through a quantum consensus validation:
   * passed → validated, failed → quarantined.
   */
  scanTransactions() {
    const all = this.analytics.transactions;
    const confirmed = all.filter((t) => t.status === 'confirmed');
    const flagged = confirmed.filter((t) => t.amount >= AML_SUSPICIOUS_THRESHOLD);

    const results = flagged.map((tx) => {
      const record = this.consensus.runConsensusDecision('security_validation', {
        transactionId: tx.id,
        sender: tx.sender,
        recipient: tx.recipient,
        amount: tx.amount,
        rule: 'AML_suspicious_activity_threshold',
        threshold: AML_SUSPICIOUS_THRESHOLD,
      });
      tx.securityStatus = record.consensusPassed ? 'validated' : 'quarantined';
      tx.securityConsensus = record;
      return { transaction: publicTx(tx), consensus: record };
    });

    const quarantined = results.filter((r) => r.transaction.securityStatus === 'quarantined').length;
    const report = {
      scannedAt: new Date().toISOString(),
      totalScanned: all.length,
      confirmedScanned: confirmed.length,
      flaggedCount: flagged.length,
      validated: flagged.length - quarantined,
      quarantined,
      clean: confirmed.length - flagged.length,
      amlThreshold: AML_SUSPICIOUS_THRESHOLD,
      threatLevel: quarantined === 0 ? 'low' : quarantined <= 2 ? 'elevated' : 'high',
      results,
    };
    this.lastScan = report;
    return report;
  }
}

module.exports = { SecurityService, AML_SUSPICIOUS_THRESHOLD };
