import hashlib
import time

from contract_sandbox import safe_eval
from transaction import Transaction


class Contract:
    def __init__(self, address, code):
        self.address = address
        self.code = code
        self.state = {}

    def execute(self, transaction):
        # Check if the transaction sender has enough funds
        if self.state.get(transaction.sender, 0) < transaction.amount:
            return False

        # Execute the contract code in a restricted sandbox — never eval()
        # untrusted contract source in the host interpreter. Transaction
        # fields are exposed as a dict so contract code needs no attribute
        # access (e.g. transaction['amount']).
        code_output = safe_eval(self.code, {
            "transaction": {
                "sender": transaction.sender,
                "receiver": transaction.receiver,
                "amount": transaction.amount,
            }
        })

        # Update the contract state
        self.state[transaction.receiver] = (
            self.state.get(transaction.receiver, 0) + transaction.amount
        )
        self.state[transaction.sender] = (
            self.state.get(transaction.sender, 0) - transaction.amount
        )

        # Return the output of the contract code
        return code_output

    def to_dict(self):
        return {"address": self.address, "code": self.code, "state": self.state}
