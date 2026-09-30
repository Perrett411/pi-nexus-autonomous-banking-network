'use strict';

/** User Privacy service — GDPR-style requests validated by quantum consensus. */

const crypto = require('crypto');

const REQUEST_TYPES = ['data_export', 'right_to_be_forgotten'];

class PrivacyService {
  constructor(consensus, analytics) {
    this.consensus = consensus;
    this.analytics = analytics;
    this.requests = [];
  }

  /**
   * Submits a privacy request. The quantum consensus function decides
   * approval; approved "right to be forgotten" requests anonymize records.
   */
  submit({ type, subject }) {
    if (!REQUEST_TYPES.includes(type)) {
      const error = new Error(`type must be one of: ${REQUEST_TYPES.join(', ')}`);
      error.status = 400;
      throw error;
    }
    if (!subject || typeof subject !== 'string') {
      const error = new Error('subject (user identifier/email) is required');
      error.status = 400;
      throw error;
    }

    const record = this.consensus.runConsensusDecision('privacy_request', { type, subject });
    const approved = record.consensusPassed;
    const request = {
      id: crypto.randomUUID(),
      type,
      subject,
      status: approved ? 'approved' : 'pending_manual_review',
      createdAt: record.timestamp,
      consensus: record,
      affectedRecords: 0,
      export: null,
    };

    if (approved && type === 'right_to_be_forgotten') {
      request.affectedRecords = this.analytics.transactions
        .filter((t) => t.sender === subject || t.recipient === subject)
        .map((t) => {
          if (t.sender === subject) t.sender = '[anonymized]';
          if (t.recipient === subject) t.recipient = '[anonymized]';
          return t;
        }).length;
    }

    if (approved && type === 'data_export') {
      request.export = this.analytics.transactions
        .filter((t) => t.sender === subject || t.recipient === subject)
        .map((t) => ({ id: t.id, amount: t.amount, currency: t.currency, status: t.status, createdAt: t.createdAt }));
    }

    this.requests.push(request);
    return request;
  }

  list() {
    return this.requests.slice().reverse();
  }
}

module.exports = { PrivacyService, REQUEST_TYPES };
