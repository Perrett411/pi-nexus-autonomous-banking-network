'use strict';

/**
 * Quantum Consensus Engine (QCF-DRIVE)
 *
 * JavaScript port of the quantum consensus function from
 * quantum_nexus_integration/quantum_ai_security_guardian.py
 * (simulate_quantum_consensus_decision).
 *
 * Uses GHZ-state entanglement emulation: validator nodes are entangled
 * so their measurements are highly correlated (all 0s or all 1s), with a
 * small per-node decoherence (flip) probability. Consensus passes when the
 * agreement ratio meets the Byzantine fault-tolerance threshold (2/3).
 */

const crypto = require('crypto');

const DEFAULT_BRANCHES = [
  'North_America_Branch',
  'Europe_Branch',
  'Asia_Pacific_Branch',
  'Latin_America_Branch',
  'Middle_East_Africa_Branch',
];

const QCF_DRIVE_PARAMETERS = {
  consensusThreshold: 0.67, // Byzantine fault tolerance (2/3)
  validationEngine: 'DRIVE_v1.0',
  requiredQubits: 5,
  simulatedNodes: 5,
};

/** Deterministic JSON serialization (mirrors Python's sort_keys=True). */
function stableStringify(value) {
  if (value === null || typeof value !== 'object') return JSON.stringify(value);
  if (Array.isArray(value)) return '[' + value.map(stableStringify).join(',') + ']';
  const keys = Object.keys(value).sort();
  return '{' + keys.map((k) => JSON.stringify(k) + ':' + stableStringify(value[k])).join(',') + '}';
}

class QuantumConsensus {
  constructor(options = {}) {
    this.qcf = { ...QCF_DRIVE_PARAMETERS, ...(options.qcfDriveParameters || {}) };
    this.connectedBranches = new Map();
    this.ledger = [];
    (options.branches || DEFAULT_BRANCHES).forEach((branchId) => {
      this.connectBranch(branchId, { logToLedger: false });
    });
  }

  hash(data) {
    return crypto.createHash('sha256').update(data).digest();
  }

  connectBranch(branchId, { logToLedger = true } = {}) {
    if (!branchId || typeof branchId !== 'string') return false;
    this.connectedBranches.set(branchId, {
      branchId,
      name: branchId.replace(/_/g, ' '),
      connectedAt: new Date().toISOString(),
      status: 'connected',
      quantumSecured: true,
    });
    if (logToLedger) this.appendLedger('branch_connected_to_qcf_drive', { branchId });
    return true;
  }

  disconnectBranch(branchId, { logToLedger = true } = {}) {
    if (!this.connectedBranches.has(branchId)) return false;
    this.connectedBranches.delete(branchId);
    if (logToLedger) this.appendLedger('branch_disconnected_from_qcf_drive', { branchId });
    return true;
  }

  getBranches() {
    return [...this.connectedBranches.values()];
  }

  /** Active consensus node count (connected branches, or simulated fallback). */
  activeNodeCount() {
    const active = this.getBranches().filter((b) => b.status === 'connected').length;
    return active >= 2 ? active : this.qcf.simulatedNodes;
  }

  /**
   * GHZ entanglement emulation: hash entropy drives a correlated base vote;
   * each node has a ~5% decoherence (flip) chance. Deterministic per input.
   */
  emulateQuantumConsensus(decisionData, numNodes, threshold) {
    const entropy = this.hash(stableStringify(decisionData));
    const baseVote = entropy[0] % 2;
    const nodeVotes = [];
    for (let i = 0; i < numNodes; i++) {
      const flipHash = entropy[(i + 1) % entropy.length];
      nodeVotes.push(flipHash % 20 === 0 ? 1 - baseVote : baseVote);
    }
    const agreementVotes = nodeVotes.filter((v) => v === baseVote).length;
    const agreementRatio = agreementVotes / numNodes;
    return {
      consensusPassed: agreementRatio >= threshold,
      quantum: {
        method: 'GHZ Entanglement Emulation (quantum-entropy)',
        baseVote,
        nodeVotes,
        agreementVotes,
        agreementRatio: Math.round(agreementRatio * 10000) / 10000,
        threshold,
      },
    };
  }

  /**
   * Runs a decentralized quantum consensus decision (the quantum consensus
   * function). Every service action flows through here.
   */
  runConsensusDecision(action, payload = {}) {
    const decisionData = {
      action,
      payload,
      nonce: crypto.randomUUID(),
      timestamp: new Date().toISOString(),
    };
    const numNodes = this.activeNodeCount();
    const { consensusPassed, quantum } = this.emulateQuantumConsensus(
      decisionData,
      numNodes,
      this.qcf.consensusThreshold
    );
    const record = {
      decisionId: crypto.randomUUID(),
      timestamp: decisionData.timestamp,
      action,
      payload,
      consensusPassed,
      nodes: numNodes,
      validatorBranches: this.getBranches()
        .filter((b) => b.status === 'connected')
        .map((b) => b.branchId),
      quantum,
    };
    this.ledger.push(record);
    return record;
  }

  appendLedger(action, payload) {
    this.ledger.push({
      decisionId: crypto.randomUUID(),
      timestamp: new Date().toISOString(),
      action,
      payload,
      consensusPassed: null,
    });
  }

  getLedger(limit = 25) {
    return this.ledger.slice(-limit).reverse();
  }

  getStats() {
    const decisions = this.ledger.filter((r) => r.consensusPassed !== null);
    const passed = decisions.filter((r) => r.consensusPassed).length;
    return {
      totalDecisions: decisions.length,
      passed,
      failed: decisions.length - passed,
      passRate: decisions.length ? Math.round((passed / decisions.length) * 10000) / 10000 : null,
      activeBranches: this.getBranches().filter((b) => b.status === 'connected').length,
    };
  }
}

module.exports = QuantumConsensus;
