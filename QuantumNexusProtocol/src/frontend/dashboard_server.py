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
from core.consensus import ConsensusAlgorithm
from core.reconciliation import QuantumReconciler

APP_DIR = os.path.dirname(os.path.abspath(__file__))

app = Flask(__name__, static_folder=None)

ENGINE_LOCK = threading.Lock()
audit_log = QuantumAuditLog()
engine = ConsensusAlgorithm(audit_log=audit_log)
analytics = AuditAnalytics(audit_log)
reconciler = QuantumReconciler(audit_log, engine)
tx_pool = []  # transactions waiting to be proposed into a block

PARTICIPANTS = ['alice', 'bob', 'carol', 'dave', 'eve', 'zara',
                'node-7', 'node-42', 'quantum-relay']
QUANTUM_CHANNELS = ['Q-PoS', 'Q-BFT', 'entangled-mesh', 'superposition']


def _drive_tick():
    """One heartbeat of the quantum function drive."""
    global tx_pool
    action = random.random()

    if action < 0.55 or not engine.validators:
        tx = {
            'id': f"qtx-{int(time.time() * 1000)}-{random.randint(100, 999)}",
            'sender': random.choice(PARTICIPANTS),
            'recipient': random.choice(PARTICIPANTS),
            'amount': round(random.uniform(0.01, 999.99), 2),
            'quantum_channel': random.choice(QUANTUM_CHANNELS),
        }
        audit_log.log_transaction(tx)
        tx_pool.append(tx)
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
            if ticks % 20 == 0:  # periodic compliance pass — auto-reconcile
                reconciler.reconcile()
        time.sleep(random.uniform(1.0, 2.5))


def _seed_engine():
    if not engine.validators:
        for vid in ('genesis-validator', 'validator-1', 'validator-2'):
            engine.register_validator(vid, random.randint(100, 500))


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


@app.route('/<path:filename>')
def static_files(filename):
    return send_from_directory(APP_DIR, filename)


if __name__ == '__main__':
    # Only the reloader child runs the drive, so it is never started twice.
    if os.environ.get('WERKZEUG_RUN_MAIN') == 'true':
        _seed_engine()
        threading.Thread(target=_run_drive, daemon=True).start()
    app.run(host='0.0.0.0', port=3000, debug=True, use_reloader=True)
