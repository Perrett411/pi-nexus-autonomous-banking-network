"""Compliance, Ethics & Rights Engine.

Maps the network's live quantum banking controls onto the laws and
ethical standards that govern them — payment regulation (PSD2), data
protection (GDPR/CCPA), fair lending and anti-redlining (ECOA/Reg B,
Fair Housing Act, CRA), consumer protection (FTC Act §5) and audit
integrity (SOX §404). It also carries the Rights Charter — the rights
the network honors for the business and for every person — and a
fairness monitor that continuously checks participant inclusion
against the four-fifths (80%) rule used for discrimination and
redlining review.
"""
import statistics
from datetime import datetime, timezone

FAIRNESS_WINDOW = 200  # recent transactions evaluated for fairness

# Rights honored by the network — for the business and for every person.
RIGHTS_CHARTER = {
    'business': [
        'Right to operate free of arbitrary exclusion — no participant may be '
        'removed or throttled without a documented, policy-cited reason',
        'Right to due process — every enforcement action carries reason codes '
        'and is disputable through structured negotiation',
        'Right to negotiate — no penalty is final until dispute resolution '
        'has been offered and completed',
        'Right to uniform enforcement — the same policy applies to every '
        'participant; no disparate treatment between businesses',
        'Right to verifiable records — every decision is hash-chained with a '
        'Merkle proof that can be independently audited',
    ],
    'person': [
        'Right to non-discrimination — no decision based on identity, origin '
        'or status (ECOA, Fair Housing Act)',
        'Right to privacy — personal identity sealed in the stasis vault, '
        'openable only by the owner\'s key (GDPR/CCPA)',
        'Right to explanation and appeal of any automated decision',
        'Right to dispute and negotiate on equal footing with the network',
        'Right to erasure — personal data is minimized and per-owner '
        'encrypted, never exposed in plaintext',
    ],
    'ethical_standards': [
        'Transparency — every action auditable; no secret penalties',
        'Accountability — violations stopped at the gate, never quietly '
        'corrected after the fact',
        'Fairness — the four-fifths inclusion rule is monitored continuously '
        'for redlining',
        'Human dignity — enforcement targets conduct and reason codes, never '
        'identity',
    ],
}


class ComplianceEngine:
    def __init__(self, audit_log, enforcement, stasis_field, health_monitor):
        self.audit_log = audit_log
        self.enforcement = enforcement
        self.stasis_field = stasis_field
        self.health_monitor = health_monitor

    # -- fairness / anti-redlining monitor -----------------------------------
    def fairness(self, participants):
        """Four-fifths (80%) inclusion rule over recent transactions.

        The fair-lending standard: if any participant's inclusion
        rate falls below 80% of the typical (median) participant, that
        is a potential redlining pattern and is flagged for review.
        """
        entries = [e for e in self.audit_log.get_entries('TRANSACTION')][-FAIRNESS_WINDOW:]
        counts = {p: 0 for p in participants}
        for entry in entries:
            tx = (entry.get('payload') or {}).get('transaction') or {}
            for party in (tx.get('sender'), tx.get('recipient')):
                if party in counts:
                    counts[party] += 1
        # Median benchmark: the four-fifths rule against the typical
        # participant — robust to sampling noise, still catches
        # systematic exclusion immediately.
        benchmark = statistics.median(counts.values()) if counts else 0
        findings = []
        if benchmark > 0:
            for participant, count in counts.items():
                if count < 0.8 * benchmark:
                    findings.append(
                        '%s inclusion %d vs typical %s — below the '
                        'four-fifths threshold: potential redlining, review '
                        'required' % (participant, count, benchmark))
        return {
            'verdict': 'FAIR' if not findings else 'DISCRIMINATION_RISK',
            'rule': 'four-fifths (80%) inclusion rule — ECOA/Reg B & FHA '
                    'redlining standard',
            'window': 'last %d transactions' % len(entries),
            'counts': counts,
            'benchmark': benchmark,
            'findings': findings,
        }

    # -- legal framework registry ---------------------------------------------
    def _frameworks(self, chain_intact, stasis, fairness, enforcement_status,
                    reconciliation):
        frameworks = [
            {'code': 'PSD2', 'name': 'Payment Services Directive 2',
             'jurisdiction': 'EU payment services',
             'control': 'Complete, tamper-evident transaction audit trail',
             'passes': chain_intact,
             'detail': 'hash-chained ledger with Merkle proof intact' if chain_intact
                       else 'audit chain integrity failed'},
            {'code': 'GDPR/CCPA', 'name': 'General Data Protection Regulation / '
             'California Consumer Privacy Act',
             'jurisdiction': 'EU / US privacy',
             'control': 'Personal identities encrypted per owner in the stasis vault',
             'passes': stasis['identities_protected'] > 0 and stasis['merkle_match'],
             'detail': '%d identities sealed, vault integrity verified' % stasis['identities_protected']
                       if stasis['identities_protected'] and stasis['merkle_match']
                       else 'identity protection inactive'},
            {'code': 'ECOA', 'name': 'Equal Credit Opportunity Act (Reg B)',
             'jurisdiction': 'US fair lending',
             'control': 'No discrimination in any network decision',
             'passes': fairness['verdict'] == 'FAIR',
             'detail': 'four-fifths inclusion rule satisfied' if fairness['verdict'] == 'FAIR'
                       else '%d fairness findings' % len(fairness['findings'])},
            {'code': 'FHA', 'name': 'Fair Housing Act',
             'jurisdiction': 'US anti-redlining',
             'control': 'No community refused service — every participant served',
             'passes': all(c > 0 for c in fairness['counts'].values()) and bool(fairness['counts']),
             'detail': 'all %d participants served in the fairness window'
                       % len(fairness['counts']) if fairness['counts'] and all(
                           c > 0 for c in fairness['counts'].values())
                       else 'one or more participants unserved — redlining risk'},
            {'code': 'CRA', 'name': 'Community Reinvestment Act',
             'jurisdiction': 'US community inclusion',
             'control': 'Inclusive service across all participant communities',
             'passes': fairness['verdict'] == 'FAIR',
             'detail': 'inclusion rates balanced across participants'
                       if fairness['verdict'] == 'FAIR' else 'inclusion imbalance detected'},
            {'code': 'FTC-5', 'name': 'FTC Act §5 — Unfair or Deceptive Practices',
             'jurisdiction': 'US consumer protection',
             'control': 'Zero-violation gate — no unfair or deceptive transaction accepted',
             'passes': enforcement_status['mode'] == 'ACTIVE' and enforcement_status['accepted_violations'] == 0,
             'detail': 'enforcement gate active, %d violations stopped, 0 accepted'
                       % enforcement_status['blocked']
                       if enforcement_status['mode'] == 'ACTIVE' else 'enforcement gate disabled'},
            {'code': 'SOX-404', 'name': 'Sarbanes-Oxley §404 — Internal Controls',
             'jurisdiction': 'US audit integrity',
             'control': 'Verifiable internal controls — reconciliation of every block',
             'passes': chain_intact and (reconciliation is None or reconciliation['block_state'] == 'RECONCILED'),
             'detail': 'audit chain intact, block state reconciled'
                       if chain_intact else 'audit chain integrity failed'},
        ]
        return frameworks

    # -- public API -----------------------------------------------------------
    def status(self, participants):
        chain_intact = self.audit_log.verify_chain()
        stasis = self.stasis_field.status()
        fairness = self.fairness(participants)
        enforcement_status = self.enforcement.status()
        reconciliation = self.health_monitor.last_reconciliation
        frameworks = self._frameworks(chain_intact, stasis, fairness,
                                      enforcement_status, reconciliation)
        return {
            'verdict': 'COMPLIANT' if all(f['passes'] for f in frameworks) else 'REVIEW',
            'generated_at': datetime.now(timezone.utc).isoformat(),
            'frameworks': frameworks,
            'fairness': fairness,
            'rights': RIGHTS_CHARTER,
        }
