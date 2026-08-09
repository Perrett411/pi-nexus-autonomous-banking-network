import unittest
import time
from quantum_nexus_integration import (
    QuantumAISecurityGuardian,
    QUANTUM_SECURITY_LEVEL_2
)


class TestQuantumAISecurityGuardian(unittest.TestCase):
    """
    Unit test suite for the Quantum AI Security Guardian (QCF-DRIVE Compliant).
    """

    def setUp(self):
        self.guardian = QuantumAISecurityGuardian(security_level=QUANTUM_SECURITY_LEVEL_2)
        # Speed up key generation for testing by using 2048-bit RSA keys
        original_gen = self.guardian.crypto.generate_key_pair
        def fast_generate_key_pair():
            from cryptography.hazmat.primitives.asymmetric import rsa
            priv_key = rsa.generate_private_key(
                public_exponent=65537,
                key_size=2048,
                backend=self.guardian.crypto.backend
            )
            return priv_key, priv_key.public_key()
        self.guardian.crypto.generate_key_pair = fast_generate_key_pair

    def test_initialization(self):
        """Test default configs are set up and systems initialized."""
        self.assertIsNotNone(self.guardian.config)
        self.assertEqual(self.guardian.config["name"], "QuantumAI_SecurityGuardian")
        self.assertEqual(self.guardian.security_level, QUANTUM_SECURITY_LEVEL_2)
        self.assertIsNotNone(self.guardian.crypto)
        self.assertIsNotNone(self.guardian.processor)
        self.assertEqual(len(self.guardian.blockchain_ledger), 0)

    def test_enforce_legal_compliance_success(self):
        """Test compliance checks pass with valid credentials/metadata."""
        valid_transaction = {
            "amount": 2500.00,
            "currency": "USD",
            "sender": "acc_alice",
            "recipient": "acc_bob",
            "metadata": {
                "sca_completed": True,
                "gdpr_consent": True,
                "kyc_verified": True
            }
        }
        compliant, logs = self.guardian.enforce_legal_compliance(valid_transaction)
        self.assertTrue(compliant)
        self.assertTrue(any("Pass" in log for log in logs))

    def test_enforce_legal_compliance_failure_sca(self):
        """Test PSD2 failure when strong customer authentication is missing."""
        invalid_transaction = {
            "amount": 100.00,
            "currency": "USD",
            "sender": "acc_alice",
            "recipient": "acc_bob",
            "metadata": {
                "sca_completed": False,  # SCA Missing
                "gdpr_consent": True,
                "kyc_verified": True
            }
        }
        compliant, logs = self.guardian.enforce_legal_compliance(invalid_transaction)
        self.assertFalse(compliant)
        self.assertTrue(any("PSD2 Failure" in log for log in logs))

    def test_enforce_legal_compliance_failure_aml(self):
        """Test AML failure on high value transactions without KYC verification."""
        invalid_transaction = {
            "amount": 15000.00,  # > $10,000 threshold
            "currency": "USD",
            "sender": "acc_alice",
            "recipient": "acc_bob",
            "metadata": {
                "sca_completed": True,
                "gdpr_consent": True,
                "kyc_verified": False  # KYC Missing
            }
        }
        compliant, logs = self.guardian.enforce_legal_compliance(invalid_transaction)
        self.assertFalse(compliant)
        self.assertTrue(any("AML Failure" in log for log in logs))

    def test_enforce_legal_compliance_failure_gdpr(self):
        """Test GDPR failure when explicit user consent is missing."""
        invalid_transaction = {
            "amount": 100.00,
            "currency": "USD",
            "sender": "acc_alice",
            "recipient": "acc_bob",
            "metadata": {
                "sca_completed": True,
                "gdpr_consent": False,  # Consent Missing
                "kyc_verified": True
            }
        }
        compliant, logs = self.guardian.enforce_legal_compliance(invalid_transaction)
        self.assertFalse(compliant)
        self.assertTrue(any("GDPR Failure" in log for log in logs))

    def test_quantum_consensus_decision_emulated(self):
        """Test emulated QCF consensus mechanism decision outcome."""
        decision_data = {"transaction_id": "test-tx-uuid", "amount": 100}
        passed, details = self.guardian.simulate_quantum_consensus_decision(decision_data)
        
        self.assertIn("agreement_ratio", details)
        self.assertIn("consensus_passed", details)
        self.assertEqual(passed, details["consensus_passed"])

    def test_secure_account_activity(self):
        """Test account activity validation signing and ledger audit log."""
        verified, event_id = self.guardian.secure_account_activity(
            account_id="user_john",
            action="update_password",
            details={"ip": "192.168.1.10"}
        )
        self.assertTrue(verified)
        self.assertIsNotNone(event_id)
        
        # Verify block ledger entry
        ledger = self.guardian.get_blockchain_ledger()
        self.assertEqual(len(ledger), 1)
        self.assertEqual(ledger[0]["action_type"], "account_security_activity")
        self.assertEqual(ledger[0]["details"]["account_id"], "user_john")

    def test_cohesive_secure_and_process_settlement_success(self):
        """Test end-to-end transaction processing and settlements run cohesively."""
        metadata = {
            "sca_completed": True,
            "gdpr_consent": True,
            "kyc_verified": True
        }
        
        settlement_report = self.guardian.secure_and_process_settlement(
            sender="sender@pinexus.com",
            recipient="recipient@pinexus.com",
            amount=500.00,
            currency="USD",
            metadata=metadata
        )
        
        # Verify successful settlement outcomes
        self.assertEqual(settlement_report["status"], "completed")
        self.assertTrue(settlement_report["quantum_secured"])
        self.assertTrue(settlement_report["compliance_audit"]["compliant"])
        self.assertTrue(settlement_report["quantum_consensus_audit"]["passed"])
        self.assertIn("blockchain_receipt", settlement_report)
        
        # Ledger checks
        ledger = self.guardian.get_blockchain_ledger()
        self.assertGreater(len(ledger), 0)
        self.assertEqual(ledger[-1]["action_type"], "settlement_completed")
        self.assertEqual(ledger[-1]["details"]["transaction_id"], settlement_report["transaction_id"])

    def test_cohesive_secure_and_process_settlement_failed_compliance(self):
        """Test settlement is rejected and logged when compliance checks fail."""
        metadata = {
            "sca_completed": False,  # Cause failure
            "gdpr_consent": True,
            "kyc_verified": True
        }
        
        settlement_report = self.guardian.secure_and_process_settlement(
            sender="sender@pinexus.com",
            recipient="recipient@pinexus.com",
            amount=500.00,
            currency="USD",
            metadata=metadata
        )
        
        self.assertEqual(settlement_report["status"], "rejected")
        self.assertEqual(settlement_report["reason"], "Legal Compliance Enforcement Failure")
        
        # Verify rejection logged
        ledger = self.guardian.get_blockchain_ledger()
        self.assertEqual(ledger[-1]["action_type"], "settlement_rejection")


if __name__ == "__main__":
    unittest.main()
