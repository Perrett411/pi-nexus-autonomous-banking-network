import hashlib
import time
from collections import defaultdict

from core.reconciliation import correct_transaction, inspect_transaction

class Block:
    def __init__(self, index, previous_hash, transactions, timestamp=None):
        self.index = index
        self.previous_hash = previous_hash
        self.transactions = transactions
        self.timestamp = timestamp or time.time()
        self.hash = self.calculate_hash()

    def calculate_hash(self):
        block_string = f"{self.index}{self.previous_hash}{self.transactions}{self.timestamp}".encode()
        return hashlib.sha256(block_string).hexdigest()

class ConsensusAlgorithm:
    def __init__(self, audit_log=None):
        self.validators = {}
        self.current_block = None
        self.pending_transactions = []
        self.validator_rewards = defaultdict(int)
        self.slashing_conditions = {}
        self.audit_log = audit_log

    def _audit_consensus(self, change_type, details=None):
        if self.audit_log:
            self.audit_log.log_consensus_change(change_type, details)

    def register_validator(self, validator_id, stake):
        self.validators[validator_id] = stake
        self._audit_consensus('VALIDATOR_REGISTERED', {'validator_id': validator_id, 'stake': stake})

    def propose_block(self, transactions):
        if not self.validators:
            raise Exception("No validators registered.")

        self.current_block = Block(
            index=len(self.pending_transactions) + 1,
            previous_hash=self.get_last_block_hash(),
            transactions=transactions
        )
        if self.audit_log:
            for tx in transactions:
                self.audit_log.log_transaction(tx)
        self._audit_consensus('BLOCK_PROPOSED', {'block_index': self.current_block.index,
                                                 'block_hash': self.current_block.hash})
        return self.current_block

    def validate_block(self, block):
        # Validate block hash and structure
        if block.hash != block.calculate_hash():
            return False
        if block.previous_hash != self.get_last_block_hash():
            return False
        return True

    def correct_block_violations(self, block):
        """Auto-correct transactional violations inside a proposed block.

        The consensus function fixes fixable errors (invalid amounts,
        missing fields) before finalization; every correction is audited
        for transparency, and uncorrectable policy violations
        (self-transfers) are flagged for review.
        """
        corrections = 0
        for tx in block.transactions:
            if not isinstance(tx, dict):
                continue
            violations = inspect_transaction(tx)
            if not violations:
                continue
            fixable = [v for v in violations if v != 'SELF_TRANSFER']
            if fixable:
                original = dict(tx)
                corrected, corrections_made = correct_transaction(tx)
                tx.update(corrected)
                corrections += len(corrections_made)
                self._audit_consensus('TRANSACTION_CORRECTED', {
                    'transaction_id': tx.get('id'),
                    'corrections': corrections_made,
                    'original': original,
                    'corrected': corrected,
                })
            if 'SELF_TRANSFER' in violations:
                self._audit_consensus('VIOLATION_FLAGGED', {
                    'transaction_id': tx.get('id'),
                    'violation': 'SELF_TRANSFER',
                    'note': 'policy violation — manual review required',
                })
        if corrections:
            block.hash = block.calculate_hash()
        return corrections

    def finalize_block(self, block):
        # Consensus auto-corrects transactional violations before
        # finalizing, keeping every correction transparent in the audit log.
        self.correct_block_violations(block)
        if self.validate_block(block):
            self.pending_transactions.append(block)
            self.reward_validators(block)
            self._audit_consensus('BLOCK_FINALIZED', {'block_index': block.index,
                                                     'block_hash': block.hash})
            return True
        return False

    def reward_validators(self, block):
        # Reward validators for proposing a valid block
        for validator in self.validators:
            self.validator_rewards[validator] += 1  # Simple reward mechanism

    def get_last_block_hash(self):
        return self.pending_transactions[-1].hash if self.pending_transactions else "0"

    def handle_fork(self, competing_chain):
        # Implement logic to handle forks in the blockchain
        if len(competing_chain) > len(self.pending_transactions):
            self.pending_transactions = competing_chain
            self._audit_consensus('FORK_RESOLVED', {'new_chain_length': len(competing_chain)})

    def slash_validator(self, validator_id):
        # Implement slashing conditions for malicious behavior
        if validator_id in self.slashing_conditions:
            # Deduct stake or impose penalties
            self.validators[validator_id] = max(0, self.validators[validator_id] - self.slashing_conditions[validator_id])
            self._audit_consensus('VALIDATOR_SLASHED', {'validator_id': validator_id,
                                                        'remaining_stake': self.validators[validator_id]})

    def set_slashing_condition(self, validator_id, penalty):
        self.slashing_conditions[validator_id] = penalty
        self._audit_consensus('SLASHING_CONDITION_SET', {'validator_id': validator_id, 'penalty': penalty})

    def get_validator_rewards(self):
        return self.validator_rewards

    def get_pending_transactions(self):
        return self.pending_transactions

    def get_validators(self):
        return self.validators
