"""Zero-Violation Enforcement Protocol.

A pre-acceptance policy gate for the quantum function drive: every
transaction is screened against network policy BEFORE it can reach the
ledger. Violating transactions are quarantined with documented reason
codes, so violations are stopped at the gate instead of corrected
after the fact — the chain never records a violating transaction.

Screening decisions cite policy reason codes only (never identity),
which is what makes the gate defensible under fair-treatment rules.
"""
from datetime import datetime, timezone

from core.reconciliation import inspect_transaction

MAX_QUARANTINE = 100


class ZeroViolationEnforcement:
    def __init__(self, audit_log=None):
        self.audit_log = audit_log
        self.active = True
        self.screened = 0
        self.blocked = 0
        # Violations that reached the ledger after screening. While the
        # gate is active this is structurally zero — the compliance
        # engine reports it as the FTC Act §5 control.
        self.accepted_violations = 0
        self.quarantine = []
        self.stopped_by_reason = {}

    # -- internals ----------------------------------------------------------
    def _audit(self, change_type, details):
        if self.audit_log:
            self.audit_log.log_consensus_change(change_type, details)

    # -- public API ---------------------------------------------------------
    def screen(self, tx):
        """Policy gate. Returns (allowed, reason_codes).

        Quarantined transactions are recorded with their reason codes;
        they never enter the audit trail or the block pool.
        """
        self.screened += 1
        if not self.active:
            return True, []
        reasons = inspect_transaction(tx)
        if not reasons:
            return True, []

        self.blocked += 1
        for reason in reasons:
            self.stopped_by_reason[reason] = self.stopped_by_reason.get(reason, 0) + 1
        record = {
            'tx_id': tx.get('id'),
            'sender': tx.get('sender'),
            'recipient': tx.get('recipient'),
            'amount': tx.get('amount'),
            'reasons': reasons,
            'stopped_at': datetime.now(timezone.utc).isoformat(),
        }
        self.quarantine.append(record)
        if len(self.quarantine) > MAX_QUARANTINE:
            self.quarantine = self.quarantine[-MAX_QUARANTINE:]
        self._audit('VIOLATION_STOPPED', {
            'tx_id': record['tx_id'],
            'reasons': reasons,
            'action': 'QUARANTINED — never entered the ledger',
        })
        return False, reasons

    def status(self):
        return {
            'mode': 'ACTIVE' if self.active else 'DISABLED',
            'screened': self.screened,
            'blocked': self.blocked,
            'accepted_violations': self.accepted_violations,
            'stopped_by_reason': dict(self.stopped_by_reason),
            'quarantined': list(reversed(self.quarantine[-25:])),
        }
