# contract.py
from contract_sandbox import safe_eval

class Contract:
    def __init__(self, code):
        self.code = code

    def execute(self, inputs):
        # Execute the contract code in a restricted sandbox — never eval()
        # untrusted contract source in the host interpreter.
        return safe_eval(self.code, {"inputs": inputs})

class EonixContract(Contract):
    def __init__(self, code):
        super().__init__(code)

    def execute(self, inputs):
        # Add Eonix-specific functionality, such as accessing the blockchain
        blockchain = Eonix().blockchain
        return super().execute(inputs)
