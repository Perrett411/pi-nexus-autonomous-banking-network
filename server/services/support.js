'use strict';

/** 24/7 Customer Support service — AI responses validated by quantum consensus. */

const crypto = require('crypto');

const RESPONSE_RULES = [
  {
    keywords: ['password', 'login', 'access', 'sign in'],
    response:
      'For account access issues, try resetting your password from the sign-in page. If the problem persists, your identity will be re-verified through the QCF-DRIVE quantum-secured identity layer.',
  },
  {
    keywords: ['transaction', 'transfer', 'payment', 'delay', 'stuck', 'pending'],
    response:
      'Transactions on the Pi Nexus network are validated by decentralized quantum consensus before confirmation. If a transaction shows as pending, it is awaiting consensus validation — this normally completes within seconds.',
  },
  {
    keywords: ['privacy', 'data', 'gdpr', 'delete', 'export'],
    response:
      'You can submit a data export or right-to-be-forgotten request from the User Privacy panel. Each privacy request is approved through quantum consensus, giving you a verifiable, tamper-proof decision record.',
  },
  {
    keywords: ['quantum', 'consensus', 'security', 'fraud', 'hack'],
    response:
      'The Pi Nexus network secures every action with GHZ-entangled quantum consensus across distributed banking branch nodes — there is no single point of failure. Security scans run continuously and quarantine suspicious activity automatically.',
  },
];

const FALLBACK_RESPONSE =
  'Thank you for contacting Pi Nexus support. Our quantum AI assistant has logged your request; every support interaction is recorded to the consensus ledger. A specialist will follow up if further help is needed.';

class SupportService {
  constructor(consensus) {
    this.consensus = consensus;
    this.tickets = [];
  }

  /**
   * Creates a support ticket with an AI-generated response. The quantum
   * consensus function validates the response: passed → resolved by AI,
   * failed → escalated to a human agent.
   */
  submit({ subject, message }) {
    if (!subject || !message || typeof subject !== 'string' || typeof message !== 'string') {
      const error = new Error('subject and message are required');
      error.status = 400;
      throw error;
    }

    const response = this.generateResponse(`${subject} ${message}`);
    const record = this.consensus.runConsensusDecision('support_ai_response', {
      subject,
      suggestedResponse: response,
    });

    const ticket = {
      id: crypto.randomUUID(),
      subject,
      message,
      response,
      status: record.consensusPassed ? 'resolved_by_ai' : 'escalated_to_human_agent',
      createdAt: record.timestamp,
      consensus: record,
    };
    this.tickets.push(ticket);
    return ticket;
  }

  generateResponse(text) {
    const lower = text.toLowerCase();
    const rule = RESPONSE_RULES.find((r) => r.keywords.some((k) => lower.includes(k)));
    return rule ? rule.response : FALLBACK_RESPONSE;
  }

  list() {
    return this.tickets.slice().reverse();
  }
}

module.exports = { SupportService };
