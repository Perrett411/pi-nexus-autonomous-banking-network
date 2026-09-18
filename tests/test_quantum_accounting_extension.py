import unittest
import time
import json
from quantum_nexus_integration import (
    QuantumAISecurityGuardian,
    QuantumAccountingExtension,
    QUANTUM_SECURITY_LEVEL_2
)


class TestQuantumAccountingExtension(unittest.TestCase):
    """
    Unit test suite for the Quantum Accounting Extension.
    """

    def setUp(self):
        # Set up a real/fast-mock guardian
        self.guardian = QuantumAISecurityGuardian(security_level=QUANTUM_SECURITY_LEVEL_2)
        
        # Speed up key generation for testing by using 2048-bit RSA keys
        def fast_generate_key_pair():
            from cryptography.hazmat.primitives.asymmetric import rsa
            priv_key = rsa.generate_private_key(
                public_exponent=65537,
                key_size=2048,
                backend=self.guardian.crypto.backend
            )
            return priv_key, priv_key.public_key()
        self.guardian.crypto.generate_key_pair = fast_generate_key_pair

        # Connect default testing branches
        self.guardian.connect_branch_to_qcf_drive("North_America_Branch")
        
        # Initialize our Accounting Extension
        self.accounting = QuantumAccountingExtension(self.guardian)

    def test_initialization(self):
        """Test default configs are set up and internal companies exist."""
        self.assertIsNotNone(self.accounting.guardian)
        self.assertIn("Perrett_Associates", self.accounting.companies)
        self.assertIn("Superior_RegTech", self.accounting.companies)
        
        # Check initial balances
        perrett_info = self.accounting.companies["Perrett_Associates"]
        self.assertEqual(perrett_info["balances"]["acc_perrett_vault"], 50000000.0)
        self.assertEqual(perrett_info["balances"]["acc_perrett_operations"], 5000000.0)
        self.assertEqual(perrett_info["balances"]["acc_perrett_investments"], 100000000.0)

        regtech_info = self.accounting.companies["Superior_RegTech"]
        self.assertEqual(regtech_info["balances"]["acc_regtech_main"], 15000000.0)
        self.assertEqual(regtech_info["balances"]["acc_regtech_escrow"], 20000000.0)

    def test_sage_and_quickbooks_registration(self):
        """Test posting journal entries in Sage and syncing QuickBooks."""
        tx_id = "test-tx-12345"
        sender = "acc_perrett_operations"
        recipient = "acc_regtech_main"
        amount = 250000.0
        currency = "USD"

        # Register Sage
        sage_entry = self.accounting.register_transaction_in_sage(tx_id, sender, recipient, amount, currency)
        self.assertEqual(sage_entry["tx_id"], tx_id)
        self.assertEqual(sage_entry["amount"], amount)
        self.assertEqual(sage_entry["source"], "Sage")
        self.assertIn(sage_entry, self.accounting.sage_ledger)

        # Register QuickBooks
        qb_entry = self.accounting.register_transaction_in_quickbooks(tx_id, sender, recipient, amount, currency)
        self.assertEqual(qb_entry["tx_id"], tx_id)
        self.assertEqual(qb_entry["amount"], amount)
        self.assertEqual(qb_entry["source"], "QuickBooks")
        self.assertIn(qb_entry, self.accounting.quickbooks_ledger)

    def test_export_to_google_sheets(self):
        """Test exporting consolidated records to Google Sheets."""
        tx_id = "test-sheet-tx"
        sender = "acc_perrett_operations"
        recipient = "acc_regtech_main"
        amount = 10000.0
        currency = "USD"

        self.accounting.register_transaction_in_sage(tx_id, sender, recipient, amount, currency)
        self.accounting.register_transaction_in_quickbooks(tx_id, sender, recipient, amount, currency)

        sheets_records = self.accounting.export_to_google_sheets()
        # Should merge duplicate transaction IDs under their respective sources,
        # but here we just ensure we have rows synced to Google Sheets.
        self.assertGreater(len(sheets_records), 0)
        self.assertTrue(sheets_records[0]["synced_to_sheet"])

    def test_backup_to_google_drive(self):
        """Test backing up audit data in Google Drive."""
        report_name = "test_audit_report.json"
        report_data = {"test_key": "test_value"}

        file_id = self.accounting.backup_audit_report_to_google_drive(report_name, report_data)
        self.assertIsNotNone(file_id)
        self.assertIn(report_name, self.accounting.google_drive_files)
        
        file_content = json.loads(self.accounting.google_drive_files[report_name])
        self.assertEqual(file_content["report_data"], report_data)
        self.assertEqual(file_content["secured_by"], "QuantumAI_SecurityGuardian")

    def test_money_transmit_success(self):
        """Test successful money transmission between internal accounts with QCF-DRIVE agreement."""
        sender = "acc_perrett_operations"
        recipient = "acc_regtech_main"
        amount = 500000.0
        currency = "USD"

        # Check balances before
        init_sender_bal = self.accounting.companies["Perrett_Associates"]["balances"][sender]
        init_recipient_bal = self.accounting.companies["Superior_RegTech"]["balances"][recipient]

        # Transmit
        report = self.accounting.money_transmit(sender, recipient, amount, currency)
        self.assertEqual(report["status"], "completed")
        self.assertTrue(report["quantum_secured"])

        # Check balances after
        final_sender_bal = self.accounting.companies["Perrett_Associates"]["balances"][sender]
        final_recipient_bal = self.accounting.companies["Superior_RegTech"]["balances"][recipient]

        self.assertEqual(final_sender_bal, init_sender_bal - amount)
        self.assertEqual(final_recipient_bal, init_recipient_bal + amount)

        # Check accounting logs and backups automatically synced
        tx_id = report["transaction_id"]
        self.assertTrue(any(e["tx_id"] == tx_id for e in self.accounting.sage_ledger))
        self.assertTrue(any(e["tx_id"] == tx_id for e in self.accounting.quickbooks_ledger))
        self.assertTrue(any(f"audit_receipt_{tx_id}.json" in f for f in self.accounting.google_drive_files))

    def test_money_transmit_insufficient_balance(self):
        """Test transmission failure due to insufficient funds."""
        sender = "acc_perrett_operations"
        recipient = "acc_regtech_main"
        amount = 99000000.0  # Exceeds 5M balance
        currency = "USD"

        report = self.accounting.money_transmit(sender, recipient, amount, currency)
        self.assertEqual(report["status"], "rejected")
        self.assertIn("Insufficient balance", report["reason"])

    def test_money_transmit_invalid_amount(self):
        """Test negative or zero amount transmissions are rejected."""
        sender = "acc_perrett_operations"
        recipient = "acc_regtech_main"
        
        report = self.accounting.money_transmit(sender, recipient, -100.0, "USD")
        self.assertEqual(report["status"], "rejected")
        self.assertEqual(report["reason"], "Amount must be positive.")

    def test_perform_reconciliation(self):
        """Test performing full accounting reconciliation with QCF-DRIVE blockchain ledger."""
        sender = "acc_perrett_operations"
        recipient = "acc_regtech_main"
        amount = 10000.0
        currency = "USD"

        # Perform a normal transmission which registers everywhere
        tx_report = self.accounting.money_transmit(sender, recipient, amount, currency)
        self.assertEqual(tx_report["status"], "completed")
        tx_id = tx_report["transaction_id"]

        # Run reconciliation -> Should have 1 fully reconciled transaction
        recon_report = self.accounting.perform_reconciliation()
        self.assertEqual(recon_report["summary"]["discrepancies_count"], 0)
        self.assertEqual(len(recon_report["reconciled_transactions"]), 1)
        self.assertEqual(recon_report["reconciled_transactions"][0]["tx_id"], tx_id)
        
        # Test discrepancy: Manually insert a completed settlement in ledger but don't record in Sage or QB
        fake_tx = self.guardian.processor.create_transaction(sender, recipient, 500.0, currency)
        fake_tx["status"] = "completed"
        fake_tx_id = fake_tx["transaction_id"]
        self.guardian.blockchain_log("settlement_completed", fake_tx)

        # Run reconciliation -> Should now find 1 discrepancy
        recon_report_2 = self.accounting.perform_reconciliation()
        self.assertEqual(recon_report_2["summary"]["discrepancies_count"], 1)
        self.assertEqual(recon_report_2["discrepancies"][0]["tx_id"], fake_tx_id)
        self.assertIn("Sage", recon_report_2["discrepancies"][0]["missing_platforms"])
        self.assertIn("QuickBooks", recon_report_2["discrepancies"][0]["missing_platforms"])

    def test_generate_escrow_and_quarterly_reports(self):
        """Test generation of Escrow and Quarterly reports."""
        escrow_rep = self.accounting.generate_escrow_report()
        self.assertEqual(escrow_rep["report_type"], "Escrow Report")
        self.assertIn("acc_regtech_escrow", escrow_rep["escrow_balances"])
        self.assertEqual(escrow_rep["total_escrow_funds"], 20000000.0)

        quarterly_rep = self.accounting.generate_quarterly_report()
        self.assertEqual(quarterly_rep["report_type"], "Quarterly Report")
        self.assertIn("Superior Regulation Technology LLC", quarterly_rep["company_holdings"])

    def test_setup_stripe_apps_upload_sync(self):
        """Test Stripe apps upload sync triggers successfully on Mondays."""
        sync_res = self.accounting.setup_stripe_apps_upload_sync(day_of_week="Monday")
        self.assertEqual(sync_res["status"], "success")
        self.assertEqual(sync_res["stripe_apps_folder"], "stripe_apps_upload")
        self.assertEqual(len(sync_res["uploads"]), 2)
        
        # Verify files are stored in Google Drive mock under stripe_apps_upload folder
        escrow_file_name = sync_res["uploads"][0]["filename"]
        self.assertIn(escrow_file_name, self.accounting.google_drive_files)

    def test_check_network_commands(self):
        """Test scanning network commands for safety and forbidden keywords."""
        cmds = ["start_node", "transmit_funds", "eval(dangerous_code)", "sudo reboot"]
        res = self.accounting.check_network_commands(cmds)
        self.assertFalse(res["all_secure"])
        self.assertEqual(res["checked_commands"][2]["status"], "exposed")
        self.assertEqual(res["checked_commands"][3]["status"], "exposed")
        self.assertEqual(res["checked_commands"][0]["status"], "secure")

    def test_recheck_all_requests(self):
        """Test rechecking all compliance and transaction requests."""
        reqs = [
            {"request_id": "req-1", "amount": 100.0},
            {"request_id": "req-2", "amount": -50.0}
        ]
        res = self.accounting.recheck_all_requests(reqs)
        self.assertFalse(res["all_valid"])
        self.assertEqual(res["rechecked_requests"][0]["rechecked_status"], "verified")
        self.assertEqual(res["rechecked_requests"][1]["rechecked_status"], "rejected")

    def test_revaluate_portfolio(self):
        """Test revaluation of investment portfolios."""
        res = self.accounting.revaluate_portfolio()
        self.assertIn("Perrett and Associates Private Investment Firm LLC", res["portfolio_valuation"])
        self.assertIn("Superior Regulation Technology LLC", res["portfolio_valuation"])
        self.assertEqual(res["portfolio_valuation"]["Superior Regulation Technology LLC"]["status"], "revalued_successfully")
        self.assertTrue(res["portfolio_valuation"]["Superior Regulation Technology LLC"]["revalued_assets"] > 0)


if __name__ == "__main__":
    unittest.main()


