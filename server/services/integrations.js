'use strict';

/** Seamless Integration service — banking branches on the QCF-DRIVE consensus network. */

class IntegrationService {
  constructor(consensus) {
    this.consensus = consensus;
  }

  list() {
    return this.consensus.getBranches();
  }

  /** Connects a branch to the quantum consensus network (consensus-gated). */
  connect(branchId) {
    if (!branchId || typeof branchId !== 'string' || branchId.trim().length < 2) {
      const error = new Error('branchId is required (min 2 characters)');
      error.status = 400;
      throw error;
    }
    const id = branchId.trim();
    if (this.consensus.connectedBranches.has(id)) {
      return { connected: false, reason: 'already_connected', branches: this.list() };
    }
    const record = this.consensus.runConsensusDecision('branch_connection_to_qcf_drive', { branchId: id });
    if (!record.consensusPassed) {
      return { connected: false, record, branches: this.list() };
    }
    this.consensus.connectBranch(id, { logToLedger: false });
    return { connected: true, record, branches: this.list() };
  }

  /** Disconnects a branch (consensus-gated). */
  disconnect(branchId) {
    if (!this.consensus.connectedBranches.has(branchId)) {
      return { disconnected: false, reason: 'not_found', branches: this.list() };
    }
    const record = this.consensus.runConsensusDecision('branch_disconnection_from_qcf_drive', { branchId });
    if (!record.consensusPassed) {
      return { disconnected: false, record, branches: this.list() };
    }
    this.consensus.disconnectBranch(branchId, { logToLedger: false });
    return { disconnected: true, record, branches: this.list() };
  }
}

module.exports = { IntegrationService };
