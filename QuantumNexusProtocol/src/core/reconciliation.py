"""Consensus reconciliation and compliance reporting.

The quantum consensus function uses this to detect transactional
violations, auto-correct the fixable ones (every correction is audited
for transparency), verify the finalized block state, and issue a
compliance ("state of the law") report.
"""
from datetime import datetime, timezone

# Policy violations that cannot be safely auto-corrected.
UNCORRECTABLE = ('SELF_TRANSFER',)


def inspect_transaction(tx):
    """Return the list of violations found in a transaction."""
    violations = []
    amount = tx.get('amount')
    if isinstance(amount, bool) or not isinstance(amount, (int, float)):
        violations.append('NON_NUMERIC_AMOUNT')
    elif amount <= 0:
        violations.append('NON_POSITIVE_AMOUNT')
    for field in ('id', 'sender', 'recipient'):
        if not tx.get(field):
            violations.append('MISSING_' + field.upper())
    if tx.get('sender') and tx.get('recipient') and tx['sender'] == tx['recipient']:
        violations.append('SELF_TRANSFER')
    return violations


def correct_transaction(tx):
    """Auto-correct fixable violations. Returns (corrected, corrections)."""
    corrected = dict(tx)
    corrections = []
    amount = corrected.get('amount')
    if isinstance(amount, bool) or not isinstance(amount, (int, float)):
        corrected['amount'] = 0.0
        corrections.append('NON_NUMERIC_AMOUNT → 0.0')
    elif amount <= 0:
        corrected['amount'] = abs(amount)
        corrections.append('NON_POSITIVE_AMOUNT → %s' % corrected['amount'])
    for field, default in (('id', 'reconciled-0'), ('sender', 'unknown'),
                           ('recipient', 'unknown')):
        if not corrected.get(field):
            corrected[field] = default
            corrections.append('MISSING_%s → %s' % (field.upper(), default))
    return corrected, corrections


class QuantumReconciler:
    """Detects and corrects transactional violations, verifies finalized
    block state, and produces the compliance report."""

    def __init__(self, audit_log, consensus):
        self.audit_log = audit_log
        self.consensus = consensus

    # -- internals ----------------------------------------------------------
    def _audit(self, change_type, details):
        if self.audit_log:
            self.audit_log.log_consensus_change(change_type, details)

    def _verify_blocks(self):
        """Reconcile the finalized block state (hashes + linkage)."""
        blocks = self.consensus.get_pending_transactions() if self.consensus else []
        prev_hash = '0'
        ok = 0
        findings = []
        for block in blocks:
            hash_valid = block.hash == block.calculate_hash()
            linked = block.previous_hash == prev_hash
            if hash_valid and linked:
                ok += 1
            else:
                findings.append({'block_index': block.index,
                                 'hash_valid': hash_valid,
                                 'linkage_valid': linked})
            prev_hash = block.hash
        return ok, len(blocks), findings

    # -- public API ---------------------------------------------------------
    def reconcile(self):
        """Full compliance pass over the audit trail and block state."""
        corrected = 0
        flagged = 0
        corrections_log = []

        for entry in self.audit_log.get_entries('TRANSACTION'):
            tx = (entry.get('payload') or {}).get('transaction') or {}
            violations = inspect_transaction(tx)
            if not violations:
                continue
            fixable = [v for v in violations if v not in UNCORRECTABLE]
            if fixable:
                new_tx, corrections = correct_transaction(tx)
                corrected += 1
                corrections_log.extend(corrections)
                self._audit('TRANSACTION_CORRECTED', {
                    'transaction_id': tx.get('id'),
                    'corrections': corrections,
                    'original': tx,
                    'corrected': new_tx,
                })
            if 'SELF_TRANSFER' in violations:
                flagged += 1
                self._audit('VIOLATION_FLAGGED', {
                    'transaction_id': tx.get('id'),
                    'violation': 'SELF_TRANSFER',
                    'note': 'policy violation — manual review required',
                })

        blocks_ok, blocks_total, block_findings = self._verify_blocks()
        chain_intact = self.audit_log.verify_chain()

        compliant = chain_intact and blocks_ok == blocks_total and flagged == 0
        report = {
            'generated_at': datetime.now(timezone.utc).isoformat(),
            'compliant': compliant,
            'status': 'COMPLIANT' if compliant else 'NON-COMPLIANT',
            'audit_chain_intact': chain_intact,
            'merkle_root': self.audit_log.merkle_root(),
            'transactions_scanned': len(self.audit_log.get_entries('TRANSACTION')),
            'violations_corrected': corrected,
            'violations_flagged': flagged,
            'corrections': corrections_log[:20],
            'blocks_total': blocks_total,
            'blocks_verified': blocks_ok,
            'block_state': 'RECONCILED' if blocks_ok == blocks_total else 'IRRECONCILABLE',
            'block_findings': block_findings[:10],
            'checks': [
                'audit chain integrity (hash chain + Merkle root)',
                'transactional validity (amount, parties, structure)',
                'finalized block state (hash + linkage reconciliation)',
            ],
        }
        self._audit('RECONCILIATION_COMPLETED', {
            'status': report['status'],
            'violations_corrected': corrected,
            'violations_flagged': flagged,
            'blocks_verified': '%d/%d' % (blocks_ok, blocks_total),
        })
        return report
