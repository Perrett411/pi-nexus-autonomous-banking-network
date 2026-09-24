"""Real-time dashboard server for the quantum function drive.

Serves the live dashboard page and a JSON API that streams every
transaction and consensus update recorded by the hash-chained audit
log. A background thread drives the consensus engine (the "quantum
function drive") so the dashboard always has live activity.
"""
import os
import random
import sys
import threading
import time

from flask import Flask, jsonify, request, send_from_directory

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.analytics import AuditAnalytics
from core.audit_log import QuantumAuditLog
from core.compliance import ComplianceEngine
from core.consensus import ConsensusAlgorithm
from core.enforcement import ZeroViolationEnforcement
from core.health_monitor import QuantumHealthMonitor
from core.negotiation import NegotiationLedger
from core.reconciliation import QuantumReconciler
from core.stasis_field import QuantumStasisField

APP_DIR = os.path.dirname(os.path.abspath(__file__))

app = Flask(__name__, static_folder=None)

ENGINE_LOCK = threading.Lock()
audit_log = QuantumAuditLog()
engine = ConsensusAlgorithm(audit_log=audit_log)
analytics = AuditAnalytics(audit_log)
reconciler = QuantumReconciler(audit_log, engine)
stasis_field = QuantumStasisField(audit_log)
enforcement = ZeroViolationEnforcement(audit_log)
health_monitor = QuantumHealthMonitor(audit_log, engine, reconciler, stasis_field)
compliance = ComplianceEngine(audit_log, enforcement, stasis_field, health_monitor)
negotiation = NegotiationLedger(audit_log)
tx_pool = []  # transactions waiting to be proposed into a block

PARTICIPANTS = ['alice', 'bob', 'carol', 'dave', 'eve', 'zara',
                'node-7', 'node-42', 'quantum-relay']
QUANTUM_CHANNELS = ['Q-PoS', 'Q-BFT', 'entangled-mesh', 'superposition']


def _drive_tick():
    """One heartbeat of the quantum function drive."""
    global tx_pool
    # Quantum entanglement sync: verify the sealed stasis field against the
    # live tree, then re-seal it to the current root (drift = breach).
    stasis_field.verify_integrity()
    stasis_field.seal(log=False)

    action = random.random()

    if action < 0.55 or not engine.validators:
        tx = {
            'id': f"qtx-{int(time.time() * 1000)}-{random.randint(100, 999)}",
            'sender': random.choice(PARTICIPANTS),
            'recipient': random.choice(PARTICIPANTS),
            'amount': round(random.uniform(0.01, 999.99), 2),
            'quantum_channel': random.choice(QUANTUM_CHANNELS),
        }
        # Zero-violation enforcement: the policy gate runs BEFORE the
        # ledger — violating transactions are quarantined with reason
        # codes and never enter the audit trail or block pool.
        allowed, _reasons = enforcement.screen(tx)
        if allowed:
            # Pre-emptive threat detection: no transaction enters the ledger
            # (or the stasis field) before passing predictive QKD analysis.
            accepted, _threat = stasis_field.scan_transaction(tx)
            if accepted:
                audit_log.log_transaction(tx)
                tx_pool.append(tx)
        if random.random() < 0.05:
            # Simulated counterfeit mint: forges a coin reusing a real
            # transaction id — predicted and neutralized pre-acceptance.
            forged = dict(tx)
            forged['id'] = tx['id']
            stasis_field.scan_transaction(forged)
        if random.random() < 0.06:
            # Simulated policy-violation attempt (self-transfer): proves the
            # enforcement gate stops it pre-acceptance, every time.
            violating = dict(tx)
            violating['sender'] = violating['recipient']
            enforcement.screen(violating)
    elif action < 0.75:
        engine.register_validator(f"validator-{random.randint(1, 12)}",
                                  random.randint(10, 500))
    elif action < 0.85 and tx_pool:
        block = engine.propose_block(tx_pool)
        engine.finalize_block(block)
        tx_pool = []
    elif action < 0.93 and engine.validators:
        engine.set_slashing_condition(random.choice(list(engine.validators)),
                                      random.randint(1, 20))
    elif engine.validators:
        engine.slash_validator(random.choice(list(engine.validators)))


def _run_drive():
    ticks = 0
    while True:
        with ENGINE_LOCK:
            _drive_tick()
            ticks += 1
            # Continuous health monitoring: probe every consensus function.
            if ticks % 5 == 0:
                health_monitor.run_checks()
            # Periodic compliance pass — auto-reconcile; a failed block
            # reconciliation raises a critical health alert.
            if ticks % 20 == 0:
                health_monitor.observe_reconciliation(reconciler.reconcile())
        time.sleep(random.uniform(1.0, 2.5))


def _seed_engine():
    if not engine.validators:
        for vid in ('genesis-validator', 'validator-1', 'validator-2'):
            engine.register_validator(vid, random.randint(100, 500))
    if stasis_field.sealed_root is None:
        stasis_field.seal()
        # Sample identities protected inside the stasis vault — encrypted
        # per owner; plaintext never leaves the field.
        for owner in PARTICIPANTS[:4]:
            stasis_field.store_identity(owner, {
                'classification': 'QUANTUM-CITIZEN',
                'clearance': 'authorized',
                'profile': 'encrypted in stasis field',
            })


def _stats_locked():
    tx_count = sum(1 for e in audit_log.entries
                   if e['entry_type'] == 'TRANSACTION')
    return {
        'total_entries': len(audit_log.entries),
        'transactions': tx_count,
        'consensus_changes': len(audit_log.entries) - tx_count,
        'chain_intact': audit_log.verify_chain(),
        'merkle_root': audit_log.merkle_root(),
        'validators': len(engine.validators),
        'blocks_finalized': len(engine.get_pending_transactions()),
        'pending_transactions': len(tx_pool),
    }


@app.route('/')
def index():
    return send_from_directory(APP_DIR, 'index.html')


@app.route('/api/events')
def api_events():
    try:
        after = int(request.args.get('after', '-1'))
    except ValueError:
        after = -1
    with ENGINE_LOCK:
        stats = _stats_locked()
        total = len(audit_log.entries)
        if after < 0:
            fresh = audit_log.entries[-200:]
        else:
            fresh = audit_log.entries[after + 1:]
    return jsonify({'stats': stats, 'total': total, 'entries': fresh})


@app.route('/api/analytics')
def api_analytics():
    """Chart-ready audit series plus detected anomalies and spikes."""
    with ENGINE_LOCK:
        return jsonify(analytics.analyze())


@app.route('/api/reconciliation', methods=['GET', 'POST'])
def api_reconciliation():
    """Run the consensus reconciliation pass and return the compliance report."""
    with ENGINE_LOCK:
        return jsonify(reconciler.reconcile())


@app.route('/api/stasis')
def api_stasis():
    """Quantum stasis field status: seal, integrity, privacy, threats."""
    with ENGINE_LOCK:
        return jsonify(stasis_field.status())


@app.route('/health')
def health_page():
    """Dedicated health monitoring view."""
    return send_from_directory(APP_DIR, 'health.html')


@app.route('/api/health')
def api_health():
    """Live health of every quantum consensus function, active alerts,
    and the zero-violation enforcement gate status."""
    with ENGINE_LOCK:
        report = health_monitor.status()
        report['enforcement'] = enforcement.status()
        return jsonify(report)


@app.route('/api/compliance')
def api_compliance():
    """Legal compliance frameworks, rights charter, anti-redlining
    fairness monitor, and the negotiation/dispute register."""
    with ENGINE_LOCK:
        report = compliance.status(PARTICIPANTS)
        report['negotiation'] = negotiation.status()
        return jsonify(report)


@app.route('/api/negotiation', methods=['GET', 'POST'])
def api_negotiation():
    """Structured dispute resolution: open a dispute on a quarantined
    item, settle with a structured offer, or escalate to human review."""
    with ENGINE_LOCK:
        if request.method == 'POST':
            data = request.get_json(silent=True) or {}
            action = data.get('action')
            try:
                if action == 'open':
                    negotiation.open_dispute(data.get('party'),
                                              data.get('subject_id'),
                                              data.get('subject_type',
                                                       'QUARANTINED_TRANSACTION'),
                                              data.get('claim', ''))
                elif action == 'propose':
                    negotiation.propose(data.get('dispute_id'),
                                        data.get('offer'))
                else:
                    return jsonify({'error': 'unknown action'}), 400
            except (ValueError, KeyError) as exc:
                return jsonify({'error': str(exc)}), 400
        return jsonify(negotiation.status())


@app.route('/<path:filename>')
def static_files(filename):
    return send_from_directory(APP_DIR, filename)


if __name__ == '__main__':
    # Only the reloader child runs the drive, so it is never started twice.
    if os.environ.get('WERKZEUG_RUN_MAIN') == 'true':
        _seed_engine()
        threading.Thread(target=_run_drive, daemon=True).start()
    app.run(host='0.0.0.0', port=3000, debug=True, use_reloader=True)
