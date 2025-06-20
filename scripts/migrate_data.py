#!/usr/bin/env python3
"""Migrate existing Freshbooks data to blockchain."""

import asyncio
import os
import sys
from pathlib import Path
from datetime import datetime
from decimal import Decimal
from typing import List, Dict, Any
from dotenv import load_dotenv

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from blockchain.core import BlockchainCore, Transaction
from freshbooks.auth import FreshbooksAuth
from freshbooks.client import FreshbooksClient


async def migrate_invoices(blockchain: BlockchainCore, fb_client: FreshbooksClient):
    """Migrate existing invoices to blockchain."""
    print("\nMigrating invoices...")
    
    # Get all invoices
    invoices = await fb_client.list_invoices()
    
    for invoice in invoices:
        # Create blockchain transaction
        transaction = Transaction(
            transaction_id=f"migrated_invoice_{invoice.id}_{int(datetime.now().timestamp() * 1_000_000)}",
            timestamp=int(invoice.issue_date.timestamp() * 1_000_000),
            transaction_type="invoice",
            data={
                "invoice_number": invoice.invoice_number,
                "client_id": invoice.client_id,
                "amount": float(invoice.amount),
                "currency": invoice.currency_code,
                "status": invoice.status,
                "due_date": invoice.due_date.isoformat(),
                "issue_date": invoice.issue_date.isoformat(),
                "freshbooks_id": invoice.id,
                "migrated": True
            },
            metadata={"migration_date": datetime.now().isoformat()}
        )
        
        await blockchain.add_transaction(transaction)
        print(f"  ✓ Invoice #{invoice.invoice_number}")
    
    print(f"Migrated {len(invoices)} invoices")


async def migrate_expenses(blockchain: BlockchainCore, fb_client: FreshbooksClient):
    """Migrate existing expenses to blockchain."""
    print("\nMigrating expenses...")
    
    # Get all expenses from the last year
    start_date = datetime.now().replace(year=datetime.now().year - 1).strftime("%Y-%m-%d")
    expenses = await fb_client.list_expenses(start_date=start_date)
    
    for expense in expenses:
        transaction = Transaction(
            transaction_id=f"migrated_expense_{expense.id}_{int(datetime.now().timestamp() * 1_000_000)}",
            timestamp=int(expense.date.timestamp() * 1_000_000),
            transaction_type="expense",
            data={
                "amount": float(expense.amount),
                "currency": expense.currency_code,
                "category": expense.category_name,
                "vendor": expense.vendor,
                "date": expense.date.isoformat(),
                "notes": expense.notes,
                "freshbooks_id": expense.id,
                "migrated": True
            },
            metadata={"migration_date": datetime.now().isoformat()}
        )
        
        await blockchain.add_transaction(transaction)
        print(f"  ✓ Expense from {expense.date.strftime('%Y-%m-%d')} - ${expense.amount}")
    
    print(f"Migrated {len(expenses)} expenses")


async def migrate_clients(blockchain: BlockchainCore, fb_client: FreshbooksClient):
    """Migrate client data to blockchain."""
    print("\nMigrating clients...")
    
    clients = await fb_client.list_clients()
    
    for client in clients:
        transaction = Transaction(
            transaction_id=f"migrated_client_{client.id}_{int(datetime.now().timestamp() * 1_000_000)}",
            timestamp=int(datetime.now().timestamp() * 1_000_000),
            transaction_type="client_record",
            data={
                "client_id": client.id,
                "display_name": client.display_name,
                "email": client.email,
                "organization": client.organization,
                "migrated": True
            },
            metadata={"migration_date": datetime.now().isoformat()}
        )
        
        await blockchain.add_transaction(transaction)
        print(f"  ✓ {client.display_name}")
    
    print(f"Migrated {len(clients)} clients")


async def main():
    """Main migration function."""
    load_dotenv()
    
    print("Freshbooks to Blockchain Migration Tool")
    print("=======================================")
    
    # Initialize blockchain
    blockchain = BlockchainCore()
    await blockchain.initialize()
    print(f"✓ Blockchain initialized with {len(blockchain.chain)} blocks")
    
    # Initialize Freshbooks
    auth = FreshbooksAuth(
        client_id=os.getenv("FRESHBOOKS_CLIENT_ID"),
        client_secret=os.getenv("FRESHBOOKS_CLIENT_SECRET")
    )
    
    if not await auth.authenticate():
        print("✗ Failed to authenticate with Freshbooks")
        return
    
    print("✓ Authenticated with Freshbooks")
    
    fb_client = FreshbooksClient(auth)
    
    # Confirm migration
    print("\nThis will migrate your Freshbooks data to the blockchain.")
    print("This is a one-time operation and may take several minutes.")
    confirm = input("\nContinue? (yes/no): ")
    
    if confirm.lower() != "yes":
        print("Migration cancelled.")
        return
    
    # Run migrations
    try:
        await migrate_clients(blockchain, fb_client)
        await migrate_invoices(blockchain, fb_client)
        await migrate_expenses(blockchain, fb_client)
        
        # Mine final block
        await blockchain.mine_pending_transactions()
        
        print("\n✓ Migration complete!")
        print(f"✓ Blockchain now has {len(blockchain.chain)} blocks")
        print(f"✓ Total transactions: {sum(len(block.transactions) for block in blockchain.chain)}")
        
    except Exception as e:
        print(f"\n✗ Migration failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())