"""Tools configuration for MCP server."""

from typing import List, Dict, Any
from mcp import Tool
from pydantic import BaseModel, Field


class InvoiceLineItem(BaseModel):
    """Line item for invoice creation."""
    name: str = Field(default="Service", description="Name of the service or product")
    description: str = Field(default="", description="Description of the line item")
    quantity: float = Field(description="Quantity of items")
    rate: float = Field(description="Rate per item")


class InvoiceCreationParams(BaseModel):
    """Parameters for creating an invoice."""
    client_id: int = Field(description="Client ID from Freshbooks")
    line_items: List[InvoiceLineItem] = Field(description="List of line items for the invoice")
    due_days: int = Field(default=30, description="Number of days until invoice is due")
    currency: str = Field(default="USD", description="Currency code")
    notes: str = Field(default="", description="Additional notes for the invoice")


class PaymentRecordParams(BaseModel):
    """Parameters for recording a payment."""
    invoice_id: int = Field(description="Invoice ID to apply payment to")
    amount: float = Field(description="Payment amount")
    payment_method: str = Field(
        default="bank_transfer", 
        description="Payment method: credit_card, debit_card, bank_transfer, check, cash, crypto"
    )


class ExpenseRecordParams(BaseModel):
    """Parameters for recording an expense."""
    amount: float = Field(description="Expense amount")
    category: str = Field(description="Expense category: office_supplies, travel, meals, software, hardware, other")
    description: str = Field(description="Description of the expense")
    vendor: str = Field(default=None, description="Vendor name")
    receipt_url: str = Field(default=None, description="URL to receipt image")


class TimeLogParams(BaseModel):
    """Parameters for logging time."""
    hours: float = Field(description="Number of hours worked")
    project_id: int = Field(default=None, description="Project ID if applicable")
    description: str = Field(default="", description="Description of work performed")


class RecurringInvoiceParams(BaseModel):
    """Parameters for creating recurring invoice."""
    client_id: int = Field(description="Client ID from Freshbooks")
    amount: float = Field(description="Invoice amount")
    frequency: str = Field(description="Frequency: weekly, biweekly, monthly, quarterly, yearly")
    line_items: List[InvoiceLineItem] = Field(description="List of line items")
    start_date: str = Field(description="Start date in ISO format")
    end_date: str = Field(default=None, description="End date in ISO format (optional)")


class TaxSummaryParams(BaseModel):
    """Parameters for tax summary."""
    year: int = Field(description="Tax year")
    quarter: int = Field(default=None, description="Quarter (1-4) for quarterly summary")


# Tool definitions for MCP
TOOLS = [
    Tool(
        name="list_invoices",
        description="List all invoices with optional filtering by status or client",
        input_schema={
            "type": "object",
            "properties": {
                "status": {
                    "type": "string",
                    "enum": ["draft", "sent", "viewed", "paid", "overdue"],
                    "description": "Filter by invoice status"
                },
                "client_id": {
                    "type": "integer",
                    "description": "Filter by client ID"
                }
            }
        }
    ),
    Tool(
        name="create_invoice",
        description="Create a new invoice with blockchain record. Use natural language like 'Create invoice for Jordan Jr tennis lessons, 10 sessions at $50 each'",
        input_schema=InvoiceCreationParams.model_json_schema()
    ),
    Tool(
        name="send_invoice",
        description="Send an invoice via email to the client",
        input_schema={
            "type": "object",
            "properties": {
                "invoice_id": {
                    "type": "integer",
                    "description": "ID of the invoice to send"
                },
                "email_message": {
                    "type": "string",
                    "description": "Custom email message (optional)"
                }
            },
            "required": ["invoice_id"]
        }
    ),
    Tool(
        name="record_payment",
        description="Record a payment for an invoice with blockchain receipt",
        input_schema=PaymentRecordParams.model_json_schema()
    ),
    Tool(
        name="record_expense",
        description="Record a business expense with blockchain audit trail",
        input_schema=ExpenseRecordParams.model_json_schema()
    ),
    Tool(
        name="list_clients",
        description="List all clients in Freshbooks",
        input_schema={
            "type": "object",
            "properties": {
                "active_only": {
                    "type": "boolean",
                    "default": True,
                    "description": "Show only active clients"
                }
            }
        }
    ),
    Tool(
        name="get_client_balance",
        description="Get a client's current balance including outstanding invoices",
        input_schema={
            "type": "object",
            "properties": {
                "client_id": {
                    "type": "integer",
                    "description": "Client ID to check balance for"
                }
            },
            "required": ["client_id"]
        }
    ),
    Tool(
        name="get_blockchain_summary",
        description="Get blockchain statistics and financial summary from immutable ledger",
        input_schema={"type": "object", "properties": {}}
    ),
    Tool(
        name="verify_transaction",
        description="Verify a transaction on the blockchain by its ID",
        input_schema={
            "type": "object",
            "properties": {
                "transaction_id": {
                    "type": "string",
                    "description": "Transaction ID to verify"
                }
            },
            "required": ["transaction_id"]
        }
    ),
    Tool(
        name="create_recurring_invoice",
        description="Create a recurring invoice rule with smart contract automation",
        input_schema=RecurringInvoiceParams.model_json_schema()
    ),
    Tool(
        name="process_recurring_invoices",
        description="Process all due recurring invoices",
        input_schema={"type": "object", "properties": {}}
    ),
    Tool(
        name="get_tax_summary",
        description="Get tax summary for a year or quarter",
        input_schema=TaxSummaryParams.model_json_schema()
    ),
    Tool(
        name="log_time",
        description="Log billable time with blockchain timestamp",
        input_schema=TimeLogParams.model_json_schema()
    )
]


# Orchestrator registration data
ORCHESTRATOR_CONFIG = {
    "mcp_name": "freshbooks-blockchain",
    "display_name": "Freshbooks Blockchain",
    "description": "Blockchain-powered accounting with Freshbooks. Every transaction creates an immutable audit trail.",
    "icon": "💰",
    "capabilities": [
        "Create and manage invoices",
        "Record payments and expenses", 
        "Track billable time",
        "Blockchain audit trail",
        "Tax calculations and withholding",
        "Recurring invoice automation",
        "Client balance tracking",
        "Compliance reporting"
    ],
    "categories": ["accounting", "finance", "blockchain", "invoicing", "expenses"],
    "keywords": [
        "invoice", "payment", "expense", "accounting", "freshbooks",
        "blockchain", "audit", "tax", "billing", "receipt", "client",
        "balance", "recurring", "time tracking", "financial", "ledger",
        "crypto", "immutable", "compliance", "withholding"
    ],
    "tools": [tool.name for tool in TOOLS]
}
