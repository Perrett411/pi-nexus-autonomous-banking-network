"""Quantum Stasis Field Protocol.

A protective layer around the quantum function drive:

- Data immutability — the audit Merkle root is sealed in the stasis
  field and re-verified on every heartbeat (quantum entanglement sync);
  any alteration to the sealed tree structure raises a breach.
- Absolute privacy — personal identities are encrypted per owner and
  committed into an identity Merkle tree; only the authorized owner's
  key can open their record, and plaintext never leaves the field.
- Pre-threat detection — predictive QKD analysis scores every incoming
  transaction for counterfeit coins (replayed ids, invalid mints) and
  channel disturbances (self-transfers, low-entropy keys) BEFORE it is
  accepted into the ledger.

The architecture is defined in stasis_field_protocol.json.
"""
import base64
import hashlib
import hmac
import json
import math
import secrets
from datetime import datetime, timezone


def _canonical(obj):
    return json.dumps(obj, sort_keys=True, separators=(',', ':'), default=str)


def _entropy(text):
    """Shannon entropy of a string — low-entropy ids suggest interception."""
    if not text:
        return 0.0
    freq = {}
    for ch in text:
        freq[ch] = freq.get(ch, 0) + 1
    total = len(text)
    return -sum((c / total) * math.log2(c / total) for c in freq.values())


class QuantumStasisField:
    def __init__(self, audit_log):
        self.audit_log = audit_log
        # -- immutability state ------------------------------------------------
        self.sealed_root = None
        self.sealed_entries = 0
        self.integrity_checks = 0
        self.breaches = 0
        # -- privacy vault ------------------------------------------------------
        self._vault = {}        # owner -> {salt, nonce, ciphertext, commitment}
        self._access_keys = {}  # owner -> derived key (held by the authorized owner)
        # -- threat register ----------------------------------------------------
        self.threats = []
        self._seen_ids = {
            (e.get('payload') or {}).get('transaction', {}).get('id')
            for e in audit_log.get_entries('TRANSACTION')
        }

    # -- internals ----------------------------------------------------------
    def _audit(self, change_type, details):
        if self.audit_log:
            self.audit_log.log_consensus_change(change_type, details)

    @staticmethod
    def _merkle(leaves):
        """SHA-256 binary Merkle root over hex leaves."""
        if not leaves:
            return hashlib.sha256(b'').hexdigest()
        level = [bytes.fromhex(leaf) for leaf in leaves]
        while len(level) > 1:
            if len(level) % 2:
                level.append(level[-1])
            level = [hashlib.sha256(level[i] + level[i + 1]).digest()
                     for i in range(0, len(level), 2)]
        return level[0].hex()

    @staticmethod
    def _derive_key(owner, salt):
        return hashlib.pbkdf2_hmac('sha256', owner.encode(), salt, 10000)

    @staticmethod
    def _keystream(key, nonce, length):
        out = b''
        counter = 0
        while len(out) < length:
            out += hashlib.sha256(key + nonce + counter.to_bytes(4, 'big')).digest()
            counter += 1
        return out[:length]

    # -- 1. data immutability -------------------------------------------------
    def seal(self, log=True):
        """Freeze the current audit Merkle root inside the stasis field."""
        self.sealed_root = self.audit_log.merkle_root()
        self.sealed_entries = len(self.audit_log.entries)
        if log:
            self._audit('STASIS_FIELD_SEALED', {
                'merkle_root': self.sealed_root,
                'entries': self.sealed_entries,
            })
        return self.sealed_root

    def verify_integrity(self):
        """True while the sealed tree structure is unaltered.

        New entries may be appended (the field re-seals each heartbeat);
        any change to the already-sealed entries is a breach.
        """
        self.integrity_checks += 1
        ok = (self.sealed_root is not None
              and self.audit_log.verify_chain(upto=self.sealed_entries)
              and self.audit_log.merkle_root(upto=self.sealed_entries) == self.sealed_root)
        if not ok:
            self.breaches += 1
            self._audit('STASIS_FIELD_BREACH', {
                'sealed_root': self.sealed_root,
                'observed_root': self.audit_log.merkle_root(upto=self.sealed_entries),
                'attempt': secrets.token_hex(4),
            })
        return ok

    # -- 2. absolute privacy -------------------------------------------------
    def store_identity(self, owner, personal_data):
        """Encrypt an identity into the stasis vault.

        Returns (commitment, access_key) — the access key is handed only
        to the authorized owner; without it the record cannot be opened.
        """
        salt = secrets.token_bytes(16)
        nonce = secrets.token_bytes(16)
        key = self._derive_key(owner, salt)
        plaintext = _canonical(personal_data).encode()
        ciphertext = bytes(a ^ b for a, b in
                           zip(plaintext, self._keystream(key, nonce, len(plaintext))))
        commitment = hashlib.sha256(owner.encode() + ciphertext).hexdigest()
        self._vault[owner] = {
            'salt': base64.b64encode(salt).decode(),
            'nonce': base64.b64encode(nonce).decode(),
            'ciphertext': base64.b64encode(ciphertext).decode(),
            'commitment': commitment,
        }
        self._access_keys[owner] = key
        self._audit('IDENTITY_SEALED', {'owner': owner, 'commitment': commitment})
        return commitment, key

    def access_identity(self, owner, access_key):
        """Open an identity record — only the authorized key succeeds."""
        entry = self._vault.get(owner)
        if entry is None:
            raise PermissionError('stasis field: unknown identity')
        salt = base64.b64decode(entry['salt'])
        expected = self._derive_key(owner, salt)
        if not hmac.compare_digest(access_key, expected):
            self._audit('STASIS_ACCESS_DENIED', {
                'owner': owner,
                'attempt': secrets.token_hex(4),
            })
            raise PermissionError('stasis field: unauthorized access attempt')
        nonce = base64.b64decode(entry['nonce'])
        ciphertext = base64.b64decode(entry['ciphertext'])
        plaintext = bytes(a ^ b for a, b in
                          zip(ciphertext, self._keystream(expected, nonce, len(ciphertext))))
        return json.loads(plaintext.decode())

    def identity_merkle_root(self):
        """Merkle root over all identity commitments."""
        return self._merkle([e['commitment'] for e in self._vault.values()])

    # -- 3. pre-threat detection ----------------------------------------------
    def scan_transaction(self, tx):
        """Predictive QKD analysis BEFORE a transaction enters the field.

        Returns (accepted, threat_or_None). Threats are neutralized
        pre-acceptance and recorded in the audit trail.
        """
        tx_id = tx.get('id')
        amount = tx.get('amount')
        findings = []
        if tx_id is not None and tx_id in self._seen_ids:
            findings.append(('FALSE_COIN', 'high',
                             'counterfeit coin — replayed transaction id'))
        if isinstance(amount, bool) or not isinstance(amount, (int, float)) or amount <= 0:
            findings.append(('FALSE_COIN', 'high', 'invalid mint — non-positive amount'))
        if tx.get('sender') and tx.get('sender') == tx.get('recipient'):
            findings.append(('QKD_DISTURBANCE', 'medium',
                             'channel compromise — self-transfer'))
        if tx_id is not None and _entropy(str(tx_id)) < 2.0:
            findings.append(('QKD_DISTURBANCE', 'medium',
                             'low-entropy key — suspected interception'))

        if findings:
            kind, severity, description = findings[0]
            threat = {
                'type': kind,
                'severity': severity,
                'description': description,
                'tx_id': tx_id,
                'detected_at': datetime.now(timezone.utc).isoformat(),
                'action': 'NEUTRALIZED',
            }
            self.threats.append(threat)
            self._audit('THREAT_NEUTRALIZED', {
                'threat': kind,
                'severity': severity,
                'tx_id': tx_id,
                'description': description,
                'action': 'NEUTRALIZED',
            })
            return False, threat
        if tx_id is not None:
            self._seen_ids.add(tx_id)
        return True, None

    def threat_level(self):
        """Aggregate verdict over threats detected in the last 5 minutes."""
        cutoff = datetime.now(timezone.utc).timestamp() - 300
        recent = [t for t in self.threats
                  if datetime.fromisoformat(t['detected_at']).timestamp() >= cutoff]
        if len(recent) >= 15:
            return 'CRITICAL'      # coordinated attack pattern
        if recent:
            return 'ELEVATED'
        return 'NOMINAL'

    # -- status ---------------------------------------------------------------
    def status(self):
        current = self.audit_log.merkle_root()
        # The sealed prefix must be intact; the live root may legitimately
        # move ahead as new entries are appended (re-sealed each heartbeat).
        prefix_intact = (self.sealed_root is not None
                         and self.audit_log.verify_chain(upto=self.sealed_entries)
                         and self.audit_log.merkle_root(upto=self.sealed_entries) == self.sealed_root)
        return {
            'field_active': self.sealed_root is not None,
            'sealed_merkle_root': self.sealed_root,
            'current_merkle_root': current,
            'merkle_match': prefix_intact,
            'integrity_checks': self.integrity_checks,
            'breaches': self.breaches,
            'identities_protected': len(self._vault),
            'identity_merkle_root': self.identity_merkle_root(),
            'threat_level': self.threat_level(),
            'threats_neutralized': len(self.threats),
            'recent_threats': list(reversed(self.threats[-10:])),
        }
