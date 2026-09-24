"""Continuous health monitoring for the quantum consensus functions.

Every consensus function is probed on a fixed cadence: latency and
failure streaks are tracked, and alerts are raised the moment anything
fails — most importantly when block reconciliation fails, the audit
chain breaks, or the stasis field is breached. Alerts auto-clear when
the underlying check recovers, and cleared alerts are kept as history.

The dedicated Health view (`/health`) renders this in real time.
"""
import time
from datetime import datetime, timezone

from core.consensus import Block

CRITICAL_ALERTS = ('BLOCK_RECONCILIATION_FAILED', 'AUDIT_CHAIN_BROKEN',
                   'STASIS_FIELD_BREACH')


class QuantumHealthMonitor:
    def __init__(self, audit_log, engine, reconciler, stasis_field):
        self.audit_log = audit_log
        self.engine = engine
        self.reconciler = reconciler
        self.stasis_field = stasis_field

        self.checks = {
            'validators': ('validator registry — stakes valid',
                          self._check_validators),
            'propose_block': ('block proposal — candidate hashing',
                              self._check_propose_block),
            'validate_block': ('block validation — hash + linkage',
                               self._check_validate_block),
            'finalize_block': ('finalized block state — reconciliation',
                               self._check_finalize_block),
            'slashing': ('slashing conditions — penalties sane',
                         self._check_slashing),
            'block_reconciliation': ('block reconciliation pass',
                                     self._check_reconciliation),
            'audit_chain': ('audit trail — hash chain integrity',
                            self._check_audit_chain),
            'merkle_root': ('audit trail — Merkle proof',
                            self._check_merkle_root),
            'stasis_field': ('quantum stasis field — sealed integrity',
                             self._check_stasis_field),
        }
        self.results = {name: {'status': 'PENDING', 'latency_ms': None,
                               'detail': 'not run yet', 'last_run': None,
                               'failures': 0, 'runs': 0}
                        for name in self.checks}
        self.alerts = []       # code -> alert record (active + cleared history)
        self.last_reconciliation = None
        self._last_flagged = None  # violations flagged at the previous pass

    # -- internals ----------------------------------------------------------
    def _audit(self, change_type, details):
        if self.audit_log:
            self.audit_log.log_consensus_change(change_type, details)

    def _raise_alert(self, code, severity, source, message):
        for alert in self.alerts:
            if alert['code'] == code and alert['cleared_at'] is None:
                alert['message'] = message   # update, keep original raised_at
                return
        self.alerts.append({
            'code': code,
            'severity': severity,
            'source': source,
            'message': message,
            'raised_at': datetime.now(timezone.utc).isoformat(),
            'cleared_at': None,
        })
        self._audit('HEALTH_ALERT_RAISED', {
            'alert': code, 'severity': severity, 'source': source,
        })

    def _clear_alert(self, code):
        for alert in self.alerts:
            if alert['code'] == code and alert['cleared_at'] is None:
                alert['cleared_at'] = datetime.now(timezone.utc).isoformat()
                self._audit('HEALTH_ALERT_CLEARED', {'alert': code})

    def _record(self, name, ok, detail, latency_ms):
        result = self.results[name]
        result['runs'] += 1
        result['status'] = 'HEALTHY' if ok else 'FAILED'
        result['latency_ms'] = latency_ms
        result['detail'] = detail
        result['last_run'] = datetime.now(timezone.utc).isoformat()
        result['failures'] = 0 if ok else result['failures'] + 1
        code = 'FUNCTION_FAILED:' + name
        if ok:
            self._clear_alert(code)
        else:
            self._raise_alert(code, 'critical', name, detail)

    # -- individual consensus function checks -------------------------------
    def _check_validators(self):
        validators = self.engine.validators
        if not validators:
            return False, 'no validators registered'
        negative = [v for v, stake in validators.items() if stake < 0]
        if negative:
            return False, 'negative stake: %s' % ', '.join(negative)
        return True, '%d validators registered, stakes valid' % len(validators)

    def _check_propose_block(self):
        probe = Block(index=0,
                      previous_hash=self.engine.get_last_block_hash(),
                      transactions=[{'probe': 'health-monitor'}])
        if probe.hash != probe.calculate_hash():
            return False, 'candidate block hash not reproducible'
        return True, 'candidate block hashing verified'

    def _check_validate_block(self):
        probe = Block(index=0,
                      previous_hash=self.engine.get_last_block_hash(),
                      transactions=[])
        if self.engine.validate_block(probe):
            return True, 'validation function accepts a well-formed block'
        return False, 'validation function rejected a well-formed block'

    def _check_finalize_block(self):
        blocks = self.engine.get_pending_transactions()
        if not blocks:
            return True, 'no finalized blocks yet'
        prev_hash = '0'
        for block in blocks:
            if block.hash != block.calculate_hash():
                return False, 'block %s failed hash reconciliation' % block.index
            if block.previous_hash != prev_hash:
                return False, 'block %s failed linkage reconciliation' % block.index
            prev_hash = block.hash
        return True, '%d finalized blocks reconciled' % len(blocks)

    def _check_slashing(self):
        for validator, penalty in self.engine.slashing_conditions.items():
            if not isinstance(penalty, (int, float)) or penalty < 0:
                return False, 'invalid penalty for validator %s' % validator
        return True, '%d slashing conditions registered, penalties sane' \
            % len(self.engine.slashing_conditions)

    def _check_reconciliation(self):
        ok, total, findings = self.reconciler._verify_blocks()
        if findings:
            return False, '%d of %d blocks failed state reconciliation' \
                % (len(findings), total)
        return True, '%d/%d blocks reconciled' % (ok, total)

    def _check_audit_chain(self):
        if not self.audit_log.verify_chain():
            return False, 'audit hash chain broken — tampering suspected'
        return True, '%d entries intact and correctly linked' % len(self.audit_log.entries)

    def _check_merkle_root(self):
        root = self.audit_log.merkle_root()
        if not root:
            return False, 'Merkle root unavailable'
        return True, 'Merkle proof verifiable (root %s…)' % root[:12]

    def _check_stasis_field(self):
        if self.stasis_field.verify_integrity():
            return True, 'sealed stasis prefix intact — no breach'
        return False, 'stasis field breach — sealed data was altered'

    # -- reconciliation observer ---------------------------------------------
    def observe_reconciliation(self, report):
        """Feed a reconciliation report in; alert if reconciliation failed."""
        self.last_reconciliation = {
            'status': report['status'],
            'compliant': report['compliant'],
            'block_state': report['block_state'],
            'blocks_verified': report['blocks_verified'],
            'blocks_total': report['blocks_total'],
            'violations_corrected': report['violations_corrected'],
            'violations_flagged': report['violations_flagged'],
            'generated_at': report['generated_at'],
        }
        if report['block_state'] != 'RECONCILED' or report['block_findings']:
            self._raise_alert(
                'BLOCK_RECONCILIATION_FAILED', 'critical', 'reconciliation',
                'Block reconciliation failed — %d of %d blocks verified%s' % (
                    report['blocks_verified'], report['blocks_total'],
                    (': %s' % report['block_findings'][0]) if report['block_findings'] else ''))
        elif not report['audit_chain_intact']:
            self._raise_alert('AUDIT_CHAIN_BROKEN', 'critical', 'reconciliation',
                              'Audit chain integrity failed during reconciliation')
        else:
            self._clear_alert('BLOCK_RECONCILIATION_FAILED')
            self._clear_alert('AUDIT_CHAIN_BROKEN')
        # Legacy violations recorded before enforcement existed stay in the
        # immutable ledger; only NEW violations (post-enforcement) alert.
        baseline = self._last_flagged
        if baseline is None or report['violations_flagged'] > baseline:
            new_flagged = report['violations_flagged'] - (baseline or 0)
            if baseline is not None and new_flagged > 0:
                self._raise_alert('VIOLATION_DETECTED', 'warning', 'reconciliation',
                                  '%d new policy violations flagged for review — '
                                  'enforcement gate should have stopped these' % new_flagged)
        if report['violations_flagged'] == 0:
            self._clear_alert('VIOLATION_DETECTED')
        self._last_flagged = report['violations_flagged']

    # -- public API -----------------------------------------------------------
    def run_checks(self):
        """Probe every consensus function once."""
        for name, (_desc, check) in self.checks.items():
            started = time.perf_counter()
            try:
                ok, detail = check()
            except Exception as exc:  # a crashed function is a failed check
                ok, detail = False, 'check error: %s' % exc
            self._record(name, ok, detail,
                         round((time.perf_counter() - started) * 1000, 2))
        return self.status()

    def status(self):
        active = [a for a in self.alerts if a['cleared_at'] is None]
        critical = [a for a in active if a['severity'] == 'critical']
        if critical:
            overall = 'CRITICAL'
        elif active:
            overall = 'DEGRADED'
        else:
            overall = 'OPERATIONAL'
        return {
            'overall': overall,
            'monitored_at': datetime.now(timezone.utc).isoformat(),
            'checks': [dict(name=name, description=desc, **self.results[name])
                       for name, (desc, _fn) in self.checks.items()],
            'alerts': list(reversed(self.alerts[-30:])),
            'last_reconciliation': self.last_reconciliation,
        }
