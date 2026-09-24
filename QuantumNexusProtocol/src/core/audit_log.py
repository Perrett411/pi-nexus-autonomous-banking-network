"""Automated audit log for the quantum function drive.

Tracks every transaction and consensus change as hash-chained entries,
prevents duplicate records, and exposes a Merkle root so the audit
trail itself can be verified.
"""
import hashlib
import json
import os
from datetime import datetime, timezone

ENTRY_TYPES = ('TRANSACTION', 'CONSENSUS_CHANGE')


class QuantumAuditLog:
    def __init__(self, log_path=None):
        self.log_path = log_path or os.path.join(os.path.dirname(__file__), 'audit_log.jsonl')
        self.entries = []
        self._payload_hashes = set()  # dedup: identical payloads are never recorded twice
        self._load()

    # -- internal helpers -------------------------------------------------
    def _load(self):
        """Load existing entries so the chain continues across restarts."""
        if not os.path.exists(self.log_path):
            return
        with open(self.log_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line:
                    entry = json.loads(line)
                    self.entries.append(entry)
                    self._payload_hashes.add(entry['payload_hash'])

    @staticmethod
    def _canonical(obj):
        return json.dumps(obj, sort_keys=True, separators=(',', ':'), default=str)

    def _append(self, entry_type, payload):
        payload = dict(payload)  # content hash excludes the timestamp so duplicates match
        payload_hash = hashlib.sha256(self._canonical(payload).encode()).hexdigest()
        if payload_hash in self._payload_hashes:
            return None  # duplicate — do not record

        payload['recorded_at'] = datetime.now(timezone.utc).isoformat()
        prev_hash = self.entries[-1]['entry_hash'] if self.entries else '0' * 64
        entry = {
            'entry_type': entry_type,
            'payload': payload,
            'payload_hash': payload_hash,
            'prev_hash': prev_hash,
        }
        entry['entry_hash'] = hashlib.sha256(
            self._canonical({'entry_type': entry_type, 'payload_hash': payload_hash,
                             'prev_hash': prev_hash}).encode()
        ).hexdigest()

        self.entries.append(entry)
        self._payload_hashes.add(payload_hash)
        with open(self.log_path, 'a') as f:
            f.write(self._canonical(entry) + '\n')
        return entry

    # -- public API --------------------------------------------------------
    def log_transaction(self, transaction):
        """Record a transaction in the audit trail (duplicates ignored)."""
        return self._append('TRANSACTION', {'transaction': transaction})

    def log_consensus_change(self, change_type, details=None):
        """Record a consensus change (validator, fork, slashing, block events)."""
        return self._append('CONSENSUS_CHANGE',
                             {'change_type': change_type, 'details': details or {}})

    def merkle_root(self):
        """Merkle root over all entry hashes — publishable audit anchor."""
        if not self.entries:
            return hashlib.sha256(b'').hexdigest()
        level = [bytes.fromhex(e['entry_hash']) for e in self.entries]
        while len(level) > 1:
            if len(level) % 2:
                level.append(level[-1])
            level = [hashlib.sha256(level[i] + level[i + 1]).digest()
                     for i in range(0, len(level), 2)]
        return level[0].hex()

    def verify_chain(self):
        """Return True if every entry is intact and correctly linked."""
        prev_hash = '0' * 64
        for entry in self.entries:
            content = {k: v for k, v in entry['payload'].items() if k != 'recorded_at'}
            if hashlib.sha256(self._canonical(content).encode()).hexdigest() != entry['payload_hash']:
                return False  # payload was tampered with
            expected = hashlib.sha256(
                self._canonical({'entry_type': entry['entry_type'],
                                 'payload_hash': entry['payload_hash'],
                                 'prev_hash': entry['prev_hash']}).encode()
            ).hexdigest()
            if entry['prev_hash'] != prev_hash or entry['entry_hash'] != expected:
                return False
            prev_hash = entry['entry_hash']
        return True

    def get_entries(self, entry_type=None):
        if entry_type:
            return [e for e in self.entries if e['entry_type'] == entry_type]
        return list(self.entries)


if __name__ == '__main__':
    audit = QuantumAuditLog()
    audit.log_transaction({'id': 'tx1', 'sender': 'Alice', 'recipient': 'Bob', 'amount': 50})
    audit.log_consensus_change('VALIDATOR_REGISTERED', {'validator_id': 'v1', 'stake': 10})
    print(f"Entries: {len(audit.entries)}, chain intact: {audit.verify_chain()}")
    print(f"Merkle root: {audit.merkle_root()}")
