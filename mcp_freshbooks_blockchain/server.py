"""MCP server for Freshbooks with blockchain integration."""

import os
import sys
import json
import asyncio
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path

from mcp import Server, Tool
from mcp.types import TextContent, ImageContent, EmbeddedResource
from pydantic import BaseModel

# Import our modules
sys.path.append(str(Path(__file__).parent.parent))

from blockchain.core import BlockchainCore, Transaction
from blockchain.contracts.recurring_invoice import RecurringInvoiceContract
from blockchain.contracts.tax_withholding import TaxWithholdingContract
from blockchain.validators import TransactionValidator, ComplianceValidator
from freshbooks.auth import FreshbooksAuth
from freshbooks.client import FreshbooksClient

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class FreshbooksBlockchainServer:
    """MCP server for blockchain-powered Freshbooks integration."""
    
    def __init__(self):
        self.server = Server("freshbooks-blockchain")
        self.blockchain: Optional[BlockchainCore] = None
        self.freshbooks_auth: Optional[FreshbooksAuth] = None
        self.freshbooks_client: Optional[FreshbooksClient] = None
        self.recurring_contract: Optional[RecurringInvoiceContract] = None
        self.tax_contract: Optional[TaxWithholdingContract] = None
        self.validator = TransactionValidator()
        self.compliance = ComplianceValidator()
        self.instance_id = os.getenv("INSTANCE_ID", "Default-001")
        
        # Register tools
        self._register_tools()
    
    async def initialize(self) -> None:
        """Initialize blockchain and Freshbooks connection."""
        # Initialize blockchain
        self.blockchain = BlockchainCore(difficulty=4)
        await self.blockchain.initialize()
        
        # Initialize Freshbooks auth
        client_id = os.getenv("FRESHBOOKS_CLIENT_ID")
        client_secret = os.getenv("FRESHBOOKS_CLIENT_SECRET")
        redirect_uri = os.getenv("FRESHBOOKS_REDIRECT_URI", "http://localhost:8080/callback")
        
        if not client_id or not client_secret:
            logger.error("Freshbooks credentials not configured")
            return
        
        self.freshbooks_auth = FreshbooksAuth(client_id, client_secret, redirect_uri)
        self.freshbooks_client = FreshbooksClient(self.freshbooks_auth)
        
        # Initialize smart contracts
        self.recurring_contract = RecurringInvoiceContract(self.blockchain)
        self.tax_contract = TaxWithholdingContract(self.blockchain)
        
        logger.info(f"Freshbooks Blockchain MCP initialized - Instance: {self.instance_id}")
    
    def _register_tools(self):
        """Register all MCP tools."""
        
        # Invoice tools
        @self.server.tool("list_invoices")
        async def list_invoices(status: Optional[str] = None, client_id: Optional[int] = None) -> List[TextContent]:
            """List invoices with optional filters."""
            if not self.freshbooks_client:
                return [TextContent(text="Freshbooks not initialized. Please check credentials.")]
            
            try:
                invoices = await self.freshbooks_client.list_invoices(status, client_id)
                
                if not invoices:
                    return [TextContent(text="No invoices found.")]
                
                result = []
                for invoice in invoices:
                    result.append(TextContent(
                        text=f"Invoice #{invoice.invoice_number} - {invoice.client_id} - "
                             f"${invoice.amount} {invoice.currency_code} - Status: {invoice.status} - "
                             f"Outstanding: ${invoice.outstanding}"
                    ))
                
                return result
            except Exception as e:
                return [TextContent(text=f"Error listing invoices: {str(e)}")]
        
        @self.server.tool("create_invoice")
        async def create_invoice(
            client_id: int,
            line_items: List[Dict[str, Any]],
            due_days: int = 30,
            currency: str = "USD",
            notes: str = ""
        ) -> List[TextContent]:
            """Create a new invoice with blockchain record."""
            if not self.freshbooks_client or not self.blockchain:
                return [TextContent(text="System not initialized.")]
            
            try:
                # Calculate due date
                due_date = (datetime.now() + timedelta(days=due_days)).isoformat()
                
                # Calculate total
                total = sum(item["quantity"] * item["rate"] for item in line_items)
                
                # Prepare invoice data
                invoice_data = {
                    "client_id": client_id,
                    "amount": total,
                    "currency": currency,
                    "line_items": line_items,
                    "due_date": due_date,
                    "notes": notes
                }
                
                # Validate with compliance
                valid, error = self.validator.validate_invoice(invoice_data)
                if not valid:
                    return [TextContent(text=f"Validation error: {error}")]
                
                # Check compliance
                compliant, compliance_error = self.compliance.validate_tax_compliance("invoice", invoice_data)
                if not compliant:
                    return [TextContent(text=f"Compliance error: {compliance_error}")]
                
                # Create invoice in Freshbooks
                invoice = await self.freshbooks_client.create_invoice(invoice_data)
                
                # Record on blockchain
                transaction = Transaction(
                    transaction_id=f"invoice_{self.instance_id}_{int(datetime.now().timestamp() * 1_000_000)}",
                    timestamp=int(datetime.now().timestamp() * 1_000_000),
                    transaction_type="invoice",
                    data={
                        **invoice_data,
                        "invoice_number": invoice.invoice_number,
                        "freshbooks_id": invoice.id
                    }
                )
                
                await self.blockchain.add_transaction(transaction)
                
                # Calculate tax withholding if applicable
                withholding = await self.tax_contract.calculate_withholding("invoice", Decimal(str(total)), {})
                
                result = f"Invoice #{invoice.invoice_number} created successfully!\n"
                result += f"Amount: ${total} {currency}\n"
                result += f"Due date: {due_date}\n"
                result += f"Blockchain TX: {transaction.transaction_id}\n"
                
                if withholding:
                    result += "\nTax calculations:\n"
                    for tax_type, amount in withholding.items():
                        result += f"  {tax_type}: ${amount}\n"
                
                return [TextContent(text=result)]
                
            except Exception as e:
                return [TextContent(text=f"Error creating invoice: {str(e)}")]
        
        @self.server.tool("send_invoice")
        async def send_invoice(invoice_id: int, email_message: Optional[str] = None) -> List[TextContent]:
            """Send invoice via email."""
            if not self.freshbooks_client:
                return [TextContent(text="Freshbooks not initialized.")]
            
            try:
                success = await self.freshbooks_client.send_invoice(invoice_id, email_message)
                
                if success:
                    # Record sending on blockchain
                    transaction = Transaction(
                        transaction_id=f"invoice_sent_{self.instance_id}_{int(datetime.now().timestamp() * 1_000_000)}",
                        timestamp=int(datetime.now().timestamp() * 1_000_000),
                        transaction_type="invoice_action",
                        data={
                            "action": "sent",
                            "invoice_id": invoice_id,
                            "timestamp": datetime.now().isoformat()
                        }
                    )
                    await self.blockchain.add_transaction(transaction)
                    
                    return [TextContent(text=f"Invoice {invoice_id} sent successfully!")]
                else:
                    return [TextContent(text=f"Failed to send invoice {invoice_id}")]
                    
            except Exception as e:
                return [TextContent(text=f"Error sending invoice: {str(e)}")]
        
        @self.server.tool("record_payment")
        async def record_payment(
            invoice_id: int,
            amount: float,
            payment_method: str = "bank_transfer"
        ) -> List[TextContent]:
            """Record a payment with blockchain receipt."""
            if not self.freshbooks_client or not self.blockchain:
                return [TextContent(text="System not initialized.")]
            
            try:
                # Create payment in Freshbooks
                payment = await self.freshbooks_client.mark_invoice_paid(
                    invoice_id, 
                    Decimal(str(amount)), 
                    payment_method
                )
                
                # Record on blockchain
                transaction = Transaction(
                    transaction_id=f"payment_{self.instance_id}_{int(datetime.now().timestamp() * 1_000_000)}",
                    timestamp=int(datetime.now().timestamp() * 1_000_000),
                    transaction_type="payment",
                    data={
                        "invoice_id": invoice_id,
                        "amount": amount,
                        "payment_method": payment_method,
                        "payment_date": payment.date.isoformat(),
                        "freshbooks_payment_id": payment.id
                    }
                )
                
                await self.blockchain.add_transaction(transaction)
                
                # Calculate tax withholding
                withholding = await self.tax_contract.calculate_withholding(
                    "payment", 
                    Decimal(str(amount)), 
                    {"payment_method": payment_method}
                )
                
                result = f"Payment recorded successfully!\n"
                result += f"Amount: ${amount}\n"
                result += f"Method: {payment_method}\n"
                result += f"Blockchain TX: {transaction.transaction_id}\n"
                
                if withholding:
                    result += "\nTax withholding:\n"
                    total_withheld = sum(withholding.values())
                    for tax_type, tax_amount in withholding.items():
                        result += f"  {tax_type}: ${tax_amount}\n"
                    result += f"Net amount: ${Decimal(str(amount)) - total_withheld}\n"
                
                return [TextContent(text=result)]
                
            except Exception as e:
                return [TextContent(text=f"Error recording payment: {str(e)}")]
        
        # Expense tools
        @self.server.tool("record_expense")
        async def record_expense(
            amount: float,
            category: str,
            description: str,
            vendor: Optional[str] = None,
            receipt_url: Optional[str] = None
        ) -> List[TextContent]:
            """Record an expense with blockchain audit trail."""
            if not self.freshbooks_client or not self.blockchain:
                return [TextContent(text="System not initialized.")]
            
            try:
                # Map category to Freshbooks category ID (simplified)
                category_map = {
                    "office_supplies": 1,
                    "travel": 2,
                    "meals": 3,
                    "software": 4,
                    "hardware": 5,
                    "other": 6
                }
                
                expense_data = {
                    "amount": amount,
                    "currency": "USD",
                    "category": category,
                    "category_id": category_map.get(category, 6),
                    "description": description,
                    "vendor": vendor or "",
                    "receipt_url": receipt_url
                }
                
                # Validate
                valid, error = self.validator.validate_expense(expense_data)
                if not valid:
                    return [TextContent(text=f"Validation error: {error}")]
                
                # Check compliance
                compliant, compliance_error = self.compliance.validate_tax_compliance("expense", expense_data)
                if not compliant:
                    return [TextContent(text=f"Compliance error: {compliance_error}")]
                
                # Create expense in Freshbooks
                expense = await self.freshbooks_client.record_expense(expense_data)
                
                # Record on blockchain
                transaction = Transaction(
                    transaction_id=f"expense_{self.instance_id}_{int(datetime.now().timestamp() * 1_000_000)}",
                    timestamp=int(datetime.now().timestamp() * 1_000_000),
                    transaction_type="expense",
                    data={
                        **expense_data,
                        "freshbooks_expense_id": expense.id,
                        "date": expense.date.isoformat()
                    }
                )
                
                await self.blockchain.add_transaction(transaction)
                
                result = f"Expense recorded successfully!\n"
                result += f"Amount: ${amount}\n"
                result += f"Category: {category}\n"
                result += f"Vendor: {vendor or 'N/A'}\n"
                result += f"Blockchain TX: {transaction.transaction_id}\n"
                
                if receipt_url:
                    result += f"Receipt attached: {receipt_url}\n"
                
                return [TextContent(text=result)]
                
            except Exception as e:
                return [TextContent(text=f"Error recording expense: {str(e)}")]
        
        # Client tools
        @self.server.tool("list_clients")
        async def list_clients(active_only: bool = True) -> List[TextContent]:
            """List all clients."""
            if not self.freshbooks_client:
                return [TextContent(text="Freshbooks not initialized.")]
            
            try:
                clients = await self.freshbooks_client.list_clients(active_only)
                
                if not clients:
                    return [TextContent(text="No clients found.")]
                
                result = []
                for client in clients:
                    result.append(TextContent(
                        text=f"Client: {client.display_name} - Email: {client.email} - ID: {client.id}"
                    ))
                
                return result
                
            except Exception as e:
                return [TextContent(text=f"Error listing clients: {str(e)}")]
        
        @self.server.tool("get_client_balance")
        async def get_client_balance(client_id: int) -> List[TextContent]:
            """Get client's current balance."""
            if not self.freshbooks_client:
                return [TextContent(text="Freshbooks not initialized.")]
            
            try:
                balance = await self.freshbooks_client.get_client_balance(client_id)
                
                result = f"Client Balance (ID: {client_id}):\n"
                result += f"Total Invoiced: ${balance['total_invoiced']}\n"
                result += f"Total Paid: ${balance['total_paid']}\n"
                result += f"Outstanding: ${balance['outstanding']}\n"
                
                return [TextContent(text=result)]
                
            except Exception as e:
                return [TextContent(text=f"Error getting client balance: {str(e)}")]
        
        # Blockchain tools
        @self.server.tool("get_blockchain_summary")
        async def get_blockchain_summary() -> List[TextContent]:
            """Get blockchain statistics and balance sheet."""
            if not self.blockchain:
                return [TextContent(text="Blockchain not initialized.")]
            
            try:
                # Get blockchain stats
                chain_length = len(self.blockchain.chain)
                pending_count = len(self.blockchain.pending_transactions)
                
                # Get balance sheet from blockchain
                balance_sheet = self.blockchain.get_balance_sheet()
                
                # Get tax withholding balance
                tax_balance = self.tax_contract.get_withholding_account_balance() if self.tax_contract else 0
                
                result = f"Blockchain Summary:\n"
                result += f"Chain length: {chain_length} blocks\n"
                result += f"Pending transactions: {pending_count}\n\n"
                
                result += "Financial Summary (from blockchain):\n"
                result += f"Total Invoiced: ${balance_sheet['total_invoiced']}\n"
                result += f"Total Paid: ${balance_sheet['total_paid']}\n"
                result += f"Total Expenses: ${balance_sheet['total_expenses']}\n"
                result += f"Outstanding: ${balance_sheet['outstanding']}\n"
                result += f"Net Income: ${balance_sheet['net_income']}\n\n"
                
                result += f"Tax Withholding Account: ${tax_balance}\n"
                
                return [TextContent(text=result)]
                
            except Exception as e:
                return [TextContent(text=f"Error getting blockchain summary: {str(e)}")]
        
        @self.server.tool("verify_transaction")
        async def verify_transaction(transaction_id: str) -> List[TextContent]:
            """Verify a transaction on the blockchain."""
            if not self.blockchain:
                return [TextContent(text="Blockchain not initialized.")]
            
            try:
                # Search for transaction
                found = False
                transaction_data = None
                block_info = None
                
                for block in self.blockchain.chain:
                    for tx in block.transactions:
                        if tx.transaction_id == transaction_id:
                            found = True
                            transaction_data = tx
                            block_info = block
                            break
                    if found:
                        break
                
                if not found:
                    return [TextContent(text=f"Transaction {transaction_id} not found on blockchain.")]
                
                result = f"Transaction Verified!\n"
                result += f"Transaction ID: {transaction_id}\n"
                result += f"Type: {transaction_data.transaction_type}\n"
                result += f"Timestamp: {datetime.fromtimestamp(transaction_data.timestamp / 1_000_000)}\n"
                result += f"Block #: {block_info.index}\n"
                result += f"Block Hash: {block_info.hash}\n"
                result += f"Data: {json.dumps(transaction_data.data, indent=2)}\n"
                
                # Verify block integrity
                if block_info.hash == block_info.calculate_hash():
                    result += "\n✓ Block integrity verified"
                else:
                    result += "\n✗ Block integrity check failed!"
                
                return [TextContent(text=result)]
                
            except Exception as e:
                return [TextContent(text=f"Error verifying transaction: {str(e)}")]
        
        # Recurring invoice tools
        @self.server.tool("create_recurring_invoice")
        async def create_recurring_invoice(
            client_id: int,
            amount: float,
            frequency: str,
            line_items: List[Dict[str, Any]],
            start_date: str,
            end_date: Optional[str] = None
        ) -> List[TextContent]:
            """Create a recurring invoice rule."""
            if not self.recurring_contract:
                return [TextContent(text="Recurring contract not initialized.")]
            
            try:
                rule_data = {
                    "client_id": client_id,
                    "amount": amount,
                    "currency": "USD",
                    "frequency": frequency,
                    "line_items": line_items,
                    "start_date": start_date,
                    "end_date": end_date,
                    "payment_terms": 30
                }
                
                rule_id = await self.recurring_contract.create_rule(rule_data)
                
                result = f"Recurring invoice rule created!\n"
                result += f"Rule ID: {rule_id}\n"
                result += f"Client ID: {client_id}\n"
                result += f"Amount: ${amount}\n"
                result += f"Frequency: {frequency}\n"
                result += f"Start date: {start_date}\n"
                
                return [TextContent(text=result)]
                
            except Exception as e:
                return [TextContent(text=f"Error creating recurring invoice: {str(e)}")]
        
        @self.server.tool("process_recurring_invoices")
        async def process_recurring_invoices() -> List[TextContent]:
            """Process all due recurring invoices."""
            if not self.recurring_contract or not self.freshbooks_client:
                return [TextContent(text="System not initialized.")]
            
            try:
                generated = await self.recurring_contract.check_and_generate_invoices()
                
                if not generated:
                    return [TextContent(text="No recurring invoices due.")]
                
                result = f"Generated {len(generated)} recurring invoices:\n\n"
                
                for invoice_data in generated:
                    # Create in Freshbooks
                    invoice = await self.freshbooks_client.create_invoice(invoice_data)
                    
                    result += f"Invoice #{invoice.invoice_number} - "
                    result += f"Client: {invoice_data['client_id']} - "
                    result += f"Amount: ${invoice_data['amount']}\n"
                
                return [TextContent(text=result)]
                
            except Exception as e:
                return [TextContent(text=f"Error processing recurring invoices: {str(e)}")]
        
        # Tax tools
        @self.server.tool("get_tax_summary")
        async def get_tax_summary(year: int, quarter: Optional[int] = None) -> List[TextContent]:
            """Get tax summary for a period."""
            if not self.tax_contract:
                return [TextContent(text="Tax contract not initialized.")]
            
            try:
                if quarter:
                    # Calculate quarter dates
                    quarter_starts = {
                        1: datetime(year, 1, 1),
                        2: datetime(year, 4, 1),
                        3: datetime(year, 7, 1),
                        4: datetime(year, 10, 1)
                    }
                    quarter_ends = {
                        1: datetime(year, 3, 31),
                        2: datetime(year, 6, 30),
                        3: datetime(year, 9, 30),
                        4: datetime(year, 12, 31)
                    }
                    start_date = quarter_starts[quarter]
                    end_date = quarter_ends[quarter]
                else:
                    start_date = datetime(year, 1, 1)
                    end_date = datetime(year, 12, 31)
                
                summary = await self.tax_contract.get_tax_summary(start_date, end_date)
                
                result = f"Tax Summary for {year}"
                if quarter:
                    result += f" Q{quarter}"
                result += ":\n\n"
                
                result += f"Total Income: ${summary['total_income']}\n"
                result += f"Total Withheld: ${summary['total_withheld']}\n\n"
                
                result += "By Category:\n"
                for category, amount in summary['by_category'].items():
                    result += f"  {category}: ${amount}\n"
                
                if summary.get('quarterly_estimates'):
                    result += "\nQuarterly Estimates:\n"
                    for q, data in summary['quarterly_estimates'].items():
                        result += f"  {q}: Income ${data['income']}, Withheld ${data['withheld']}\n"
                
                return [TextContent(text=result)]
                
            except Exception as e:
                return [TextContent(text=f"Error getting tax summary: {str(e)}")]
        
        # Time tracking tools
        @self.server.tool("log_time")
        async def log_time(
            hours: float,
            project_id: Optional[int] = None,
            description: str = ""
        ) -> List[TextContent]:
            """Log billable time."""
            if not self.freshbooks_client or not self.blockchain:
                return [TextContent(text="System not initialized.")]
            
            try:
                time_data = {
                    "project_id": project_id,
                    "duration": int(hours * 3600),  # Convert to seconds
                    "notes": description
                }
                
                # Validate
                valid, error = self.validator.validate_time_entry(time_data)
                if not valid:
                    return [TextContent(text=f"Validation error: {error}")]
                
                # Create time entry
                time_entry = await self.freshbooks_client.log_time(time_data)
                
                # Record on blockchain
                transaction = Transaction(
                    transaction_id=f"time_{self.instance_id}_{int(datetime.now().timestamp() * 1_000_000)}",
                    timestamp=int(datetime.now().timestamp() * 1_000_000),
                    transaction_type="time_entry",
                    data={
                        "hours": hours,
                        "project_id": project_id,
                        "description": description,
                        "freshbooks_entry_id": time_entry.id,
                        "started_at": time_entry.started_at.isoformat()
                    }
                )
                
                await self.blockchain.add_transaction(transaction)
                
                result = f"Time logged successfully!\n"
                result += f"Hours: {hours}\n"
                result += f"Project ID: {project_id or 'N/A'}\n"
                result += f"Blockchain TX: {transaction.transaction_id}\n"
                
                return [TextContent(text=result)]
                
            except Exception as e:
                return [TextContent(text=f"Error logging time: {str(e)}")]


async def main():
    """Main entry point."""
    # Load environment variables
    from dotenv import load_dotenv
    load_dotenv()
    
    # Create and initialize server
    fb_server = FreshbooksBlockchainServer()
    await fb_server.initialize()
    
    # Run MCP server
    from mcp.server.stdio import stdio_server
    
    async with stdio_server() as (read_stream, write_stream):
        await fb_server.server.run(
            read_stream,
            write_stream,
            fb_server.server.create_initialization_options()
        )


if __name__ == "__main__":
    asyncio.run(main())
