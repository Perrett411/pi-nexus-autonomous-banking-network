"""Negotiation & Dispute Resolution Protocol.

A rights-preserving dispute flow: any quarantined transaction or
flagged violation can be disputed by its party. The network enters
structured negotiation — the party's position, the network's standing
offer, and a settlement — and every step is recorded in the immutable
audit log. Disputing never affects standing or scoring; settlements
are reached on documented merits, and any party may escalate to human
review at any time.
"""
from datetime import datetime, timezone

STANDING_OFFER = ('Network standing offer: full release and refund, or '
                  'assisted resubmission of a corrected transaction. '
                  'Disputing never affects your standing or score.')

RESOLUTIONS = {
    'release_refund': 'RESOLVED — network releases the held value and '
                      'refunds the party in full. Rights preserved; no '
                      'admission of wrongdoing by either side.',
    'resubmit_clean': 'RESOLVED — party may resubmit a policy-clean '
                      'transaction; network waives all penalties and '
                      'provides correction guidance.',
    'escalate': 'ESCALATED — human ombudsman review requested. Automated '
                'negotiation paused; all rights remain in force.',
}


class NegotiationLedger:
    def __init__(self, audit_log=None):
        self.audit_log = audit_log
        self.disputes = []

    # -- internals ----------------------------------------------------------
    def _audit(self, change_type, details):
        if self.audit_log:
            self.audit_log.log_consensus_change(change_type, details)

    def _find(self, dispute_id):
        for dispute in self.disputes:
            if dispute['id'] == dispute_id:
                return dispute
        return None

    # -- public API -----------------------------------------------------------
    def open_dispute(self, party, subject_id, subject_type, claim):
        dispute = {
            'id': 'DSP-%03d' % (len(self.disputes) + 1),
            'party': party or 'unknown',
            'subject_id': subject_id,
            'subject_type': subject_type,
            'claim': claim,
            'state': 'NEGOTIATING',
            'opened_at': datetime.now(timezone.utc).isoformat(),
            'network_position': STANDING_OFFER,
            'resolution': None,
        }
        self.disputes.append(dispute)
        self._audit('DISPUTE_OPENED', {
            'dispute_id': dispute['id'],
            'party': dispute['party'],
            'subject_id': subject_id,
            'subject_type': subject_type,
            'rights_cited': ['due process', 'negotiation', 'explanation'],
        })
        return dispute

    def propose(self, dispute_id, offer):
        """Settle a dispute with a structured offer, or escalate."""
        if offer not in RESOLUTIONS:
            raise ValueError('unknown offer: %s' % offer)
        dispute = self._find(dispute_id)
        if dispute is None:
            raise KeyError('unknown dispute: %s' % dispute_id)
        if dispute['state'] == 'RESOLVED':
            return dispute
        dispute['resolution'] = RESOLUTIONS[offer]
        dispute['state'] = 'RESOLVED' if offer != 'escalate' else 'ESCALATED'
        dispute['resolved_at'] = datetime.now(timezone.utc).isoformat()
        self._audit('NEGOTIATION_%s' % dispute['state'], {
            'dispute_id': dispute['id'],
            'party': dispute['party'],
            'offer': offer,
            'resolution': dispute['resolution'],
        })
        return dispute

    def status(self):
        open_count = sum(1 for d in self.disputes if d['state'] == 'NEGOTIATING')
        return {
            'standing_offer': STANDING_OFFER,
            'open_disputes': open_count,
            'total_disputes': len(self.disputes),
            'disputes': list(reversed(self.disputes[-25:])),
        }
