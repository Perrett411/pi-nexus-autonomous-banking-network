'use strict';

/** Real-Time Analytics service — transaction tracking validated by quantum consensus. */

const crypto = require('crypto');

function publicTx(t) {
  return {
    id: t.id,
    sender: t.sender,
    recipient: t.recipient,
    amount: t.amount,
    currency: t.currency,
    status: t.status,
    securityStatus: t.securityStatus,
    settlementStatus: t.settlementStatus,
    createdAt: t.createdAt,
  };
}

class AnalyticsService {
  constructor(consensus) {
    this.consensus = consensus;
    this.transactions = [];
  }

  submitTransaction({ sender, recipient, amount, currency = 'PI' }) {
    const parsedAmount = Number(amount);
    if (!sender || !recipient || !Number.isFinite(parsedAmount) || parsedAmount <= 0) {
      const error = new Error('sender, recipient and a positive amount are required');
      error.status = 400;
      throw error;
    }
    if (typeof currency !== 'string' || !currency.trim() || currency.length > 8) {
      const error = new Error('currency must be a short code, e.g. PI, USD, EUR');
      error.status = 400;
      throw error;
    }

    const record = this.consensus.runConsensusDecision('transaction_validation', {
      sender,
      recipient,
      amount: parsedAmount,
      currency,
    });

    const transaction = {
      id: crypto.randomUUID(),
      sender,
      recipient,
      amount: parsedAmount,
      currency,
      status: record.consensusPassed ? 'confirmed' : 'rejected_by_consensus',
      securityStatus: 'pending_scan',
      settlementStatus: 'pending',
      consensus: record,
      createdAt: record.timestamp,
    };
    this.transactions.push(transaction);
    return transaction;
  }

  getMetrics() {
    const txs = this.transactions;
    const confirmed = txs.filter((t) => t.status === 'confirmed');
    const volumeByCurrency = confirmed.reduce((acc, t) => {
      acc[t.currency] = Math.round(((acc[t.currency] || 0) + t.amount) * 100) / 100;
      return acc;
    }, {});
    return {
      totalTransactions: txs.length,
      confirmed: confirmed.length,
      rejected: txs.length - confirmed.length,
      totalVolume: confirmed.reduce((sum, t) => sum + t.amount, 0),
      volumeByCurrency,
      consensus: this.consensus.getStats(),
      recent: txs.slice(-8).reverse().map(publicTx),
    };
  }
}

module.exports = { AnalyticsService, publicTx };
