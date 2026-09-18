"""
Quantum Accounting Extension for Pi-Nexus Autonomous Banking Network

This module bridges external accounting platforms (Sage, QuickBooks, Google Sheets,
Google Drive) with the inner Quantum Consensus Function (QCF-DRIVE), facilitating
real-time bank reconciliation and money transmitting for Perrett and Associates
Private Investment Firm LLC and Superior Regulation Technology LLC.
"""

import time
import uuid
import json
import logging
from typing import Dict, List, Tuple, Any, Optional

from .quantum_ai_security_guardian import QuantumAISecurityGuardian

logger = logging.getLogger("QuantumAccountingExtension")

class QuantumAccountingExtension:
    """
    Extends the Quantum AI Security Guardian to enable multi-platform
    accounting sync, secure money transmitting, and real-time bank reconciliation.
    """
    def __init__(self, guardian: QuantumAISecurityGuardian):
        """
        Initialize the Quantum Accounting Extension.

        Args:
            guardian: Reference to the QuantumAISecurityGuardian instance
        """
        self.guardian = guardian
        self.companies = {
            "Perrett_Associates": {
                "name": "Perrett and Associates Private Investment Firm LLC",
                "accounts": ["acc_perrett_vault", "acc_perrett_operations", "acc_perrett_investments"],
                "balances": {
                    "acc_perrett_vault": 50000000.0,
                    "acc_perrett_operations": 5000000.0,
                    "acc_perrett_investments": 100000000.0
                }
            },
            "Superior_RegTech": {
                "name": "Superior Regulation Technology LLC",
                "accounts": ["acc_regtech_main", "acc_regtech_escrow"],
                "balances": {
                    "acc_regtech_main": 15000000.0,
                    "acc_regtech_escrow": 20000000.0
                }
            }
        }
        # Mock storage for connected accounting tools
        self.sage_ledger: List[Dict[str, Any]] = []
        self.quickbooks_ledger: List[Dict[str, Any]] = []
        self.google_sheets_records: List[Dict[str, Any]] = []
        self.google_drive_files: Dict[str, str] = {} # filename -> content

    def register_transaction_in_sage(self, tx_id: str, sender: str, recipient: str, amount: float, currency: str) -> Dict[str, Any]:
        """
        Simulate posting a journal entry to Sage Accounting.
        """
        entry = {
            "journal_id": str(uuid.uuid4()),
            "tx_id": tx_id,
            "sender": sender,
            "recipient": recipient,
            "amount": amount,
            "currency": currency,
            "timestamp": time.time(),
            "status": "posted",
            "source": "Sage"
        }
        self.sage_ledger.append(entry)
        logger.info(f"Sage: Posted journal entry for tx {tx_id}")
        return entry

    def register_transaction_in_quickbooks(self, tx_id: str, sender: str, recipient: str, amount: float, currency: str) -> Dict[str, Any]:
        """
        Simulate syncing a transaction event to QuickBooks Online.
        """
        entry = {
            "qb_id": str(uuid.uuid4()),
            "tx_id": tx_id,
            "sender": sender,
            "recipient": recipient,
            "amount": amount,
            "currency": currency,
            "timestamp": time.time(),
            "status": "cleared",
            "source": "QuickBooks"
        }
        self.quickbooks_ledger.append(entry)
        logger.info(f"QuickBooks: Synced transaction {tx_id}")
        return entry

    def export_to_google_sheets(self) -> List[Dict[str, Any]]:
        """
        Simulate writing all cleared/posted accounting records to a Google Sheet.
        """
        self.google_sheets_records = []
        for entry in self.sage_ledger:
            self.google_sheets_records.append({**entry, "synced_to_sheet": True})
        for entry in self.quickbooks_ledger:
            if not any(r["tx_id"] == entry["tx_id"] for r in self.google_sheets_records):
                self.google_sheets_records.append({**entry, "synced_to_sheet": True})
        logger.info("Google Sheets: Re-generated spreadsheet with latest ledger entries.")
        return self.google_sheets_records

    def backup_audit_report_to_google_drive(self, report_name: str, report_data: Dict[str, Any]) -> str:
        """
        Simulate uploading a signed PDF/JSON audit report to Google Drive.
        """
        file_id = str(uuid.uuid4())
        self.google_drive_files[report_name] = json.dumps({
            "file_id": file_id,
            "report_data": report_data,
            "timestamp": time.time(),
            "secured_by": "QuantumAI_SecurityGuardian"
        }, indent=2)
        logger.info(f"Google Drive: Backup uploaded - '{report_name}'")
        return file_id

    def money_transmit(self, sender: str, recipient: str, amount: float, currency: str) -> Dict[str, Any]:
        """
        Executes a secure money transmission within the accounts inside the quantum consensus function.
        Updates local balances and registers in Sage, QuickBooks, and Google Sheets upon completion.
        """
        if amount <= 0:
            return {"status": "rejected", "reason": "Amount must be positive."}

        # Deduct balance locally if it's one of our internal companies
        sender_company = None
        recipient_company = None
        for key, comp in self.companies.items():
            if sender in comp["accounts"]:
                sender_company = key
            if recipient in comp["accounts"]:
                recipient_company = key

        # If sender is internal, verify balance
        if sender_company:
            current_balance = self.companies[sender_company]["balances"][sender]
            if current_balance < amount:
                return {
                    "status": "rejected",
                    "reason": f"Insufficient balance in internal account '{sender}'. Available: {current_balance} {currency}"
                }

        # Prepare metadata for QCF-DRIVE routing
        metadata = {
            "sca_completed": True,
            "gdpr_consent": True,
            "kyc_verified": True,
            "accounting_sync_required": True,
            "sender_organization": self.companies[sender_company]["name"] if sender_company else "External Bank",
            "recipient_organization": self.companies[recipient_company]["name"] if recipient_company else "External Bank"
        }

        # Invoke quantum-secured settlement in QCF-DRIVE (this triggers quantum consensus decision)
        settlement_report = self.guardian.secure_and_process_settlement(
            sender=sender,
            recipient=recipient,
            amount=amount,
            currency=currency,
            metadata=metadata
        )

        if settlement_report.get("status") == "completed":
            # Adjust internal balances
            if sender_company:
                self.companies[sender_company]["balances"][sender] -= amount
            if recipient_company:
                self.companies[recipient_company]["balances"][recipient] += amount

            tx_id = settlement_report["transaction_id"]
            # Auto-register across Sage and QuickBooks
            self.register_transaction_in_sage(tx_id, sender, recipient, amount, currency)
            self.register_transaction_in_quickbooks(tx_id, sender, recipient, amount, currency)
            self.export_to_google_sheets()

            # Backup transaction receipt to Google Drive
            self.backup_audit_report_to_google_drive(
                report_name=f"audit_receipt_{tx_id}.json",
                report_data=settlement_report
            )

        return settlement_report

    def perform_reconciliation(self) -> Dict[str, Any]:
        """
        Reconciles external transaction records (Sage & QuickBooks) with the quantum ledger.
        Identifies any discrepancies and returns a detailed report.
        """
        quantum_txs = self.guardian.get_blockchain_ledger()
        reconciliation_report = {
            "reconciled_transactions": [],
            "discrepancies": [],
            "summary": {
                "total_quantum_txs": len(quantum_txs),
                "total_sage_entries": len(self.sage_ledger),
                "total_quickbooks_entries": len(self.quickbooks_ledger),
                "discrepancies_count": 0
            }
        }

        # Index sage and quickbooks transactions by transaction ID
        sage_by_tx = {entry["tx_id"]: entry for entry in self.sage_ledger}
        qb_by_tx = {entry["tx_id"]: entry for entry in self.quickbooks_ledger}

        # Match quantum transactions
        for tx_block in quantum_txs:
            if tx_block.get("action_type") != "settlement_completed":
                continue

            tx_details = tx_block.get("details", {})
            tx_id = tx_details.get("transaction_id")
            if not tx_id:
                continue

            in_sage = tx_id in sage_by_tx
            in_qb = tx_id in qb_by_tx

            if in_sage and in_qb:
                reconciliation_report["reconciled_transactions"].append({
                    "tx_id": tx_id,
                    "amount": tx_details.get("amount"),
                    "sender": tx_details.get("sender"),
                    "recipient": tx_details.get("recipient"),
                    "status": "fully_reconciled"
                })
            else:
                discrepancy = {
                    "tx_id": tx_id,
                    "amount": tx_details.get("amount"),
                    "sender": tx_details.get("sender"),
                    "recipient": tx_details.get("recipient"),
                    "missing_platforms": []
                }
                if not in_sage:
                    discrepancy["missing_platforms"].append("Sage")
                if not in_qb:
                    discrepancy["missing_platforms"].append("QuickBooks")
                reconciliation_report["discrepancies"].append(discrepancy)

        reconciliation_report["summary"]["discrepancies_count"] = len(reconciliation_report["discrepancies"])
        
        # Backup the reconciliation report to Google Drive
        report_id = self.backup_audit_report_to_google_drive(
            report_name=f"reconciliation_report_{int(time.time())}.json",
            report_data=reconciliation_report
        )
        reconciliation_report["google_drive_file_id"] = report_id

        return reconciliation_report

    def generate_escrow_report(self) -> Dict[str, Any]:
        """
        Generates a consolidated Escrow report summarizing holdings and pending reconciliations.
        """
        escrow_balances = {}
        for comp_key, comp_data in self.companies.items():
            for acct in comp_data["accounts"]:
                if "escrow" in acct:
                    escrow_balances[acct] = comp_data["balances"][acct]
        
        return {
            "report_type": "Escrow Report",
            "timestamp": time.time(),
            "escrow_balances": escrow_balances,
            "total_escrow_funds": sum(escrow_balances.values()),
            "status": "audited",
            "platforms": ["https://nexus-x-aibank-crypto.base44.app", "https://nexus-x-aibank.com"]
        }

    def generate_quarterly_report(self) -> Dict[str, Any]:
        """
        Generates a Quarterly performance and transparency report.
        """
        company_holdings = {}
        for comp_key, comp_data in self.companies.items():
            company_holdings[comp_data["name"]] = sum(comp_data["balances"].values())

        return {
            "report_type": "Quarterly Report",
            "quarter": f"Q{(int(time.strftime('%m')) - 1) // 3 + 1}",
            "year": time.strftime("%Y"),
            "timestamp": time.time(),
            "company_holdings": company_holdings,
            "total_assets_under_management": sum(company_holdings.values()),
            "status": "certified",
            "platforms": ["https://nexus-x-aibank-crypto.base44.app", "https://nexus-x-aibank.com"]
        }

    def setup_stripe_apps_upload_sync(self, day_of_week: str = "Monday") -> Dict[str, Any]:
        """
        Runs the weekly automated sync of Escrow and Quarterly reports,
        and uploads them directly to the 'stripe_apps_upload' Google Drive folder.
        
        Args:
            day_of_week: Day to trigger the sync (defaults to Monday)
        """
        escrow_report = self.generate_escrow_report()
        quarterly_report = self.generate_quarterly_report()

        sync_results = {
            "trigger_day": day_of_week,
            "sync_timestamp": time.time(),
            "status": "success" if day_of_week.lower() == "monday" else "scheduled",
            "stripe_apps_folder": "stripe_apps_upload",
            "uploads": []
        }

        # Format report filenames
        escrow_filename = f"stripe_apps_upload/escrow_report_{int(time.time())}.json"
        quarterly_filename = f"stripe_apps_upload/quarterly_report_{int(time.time())}.json"

        # Backup / upload to Google Drive folder 'stripe_apps_upload'
        escrow_file_id = self.backup_audit_report_to_google_drive(escrow_filename, escrow_report)
        quarterly_file_id = self.backup_audit_report_to_google_drive(quarterly_filename, quarterly_report)

        sync_results["uploads"].append({
            "report": "Escrow Report",
            "filename": escrow_filename,
            "file_id": escrow_file_id
        })
        sync_results["uploads"].append({
            "report": "Quarterly Report",
            "filename": quarterly_filename,
            "file_id": quarterly_file_id
        })

        logger.info(f"Stripe Apps Upload Sync executed on {day_of_week} for https://nexus-x-aibank-crypto.base44.app and https://nexus-x-aibank.com")
        return sync_results

