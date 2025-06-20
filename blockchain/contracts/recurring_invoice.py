"""Smart contract for recurring invoice automation."""

import json
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
import asyncio


@dataclass
class RecurringInvoiceRule:
    """Defines a recurring invoice rule."""
    
    rule_id: str
    client_id: str
    amount: float
    currency: str
    frequency: str  # weekly, biweekly, monthly, quarterly, yearly
    start_date: datetime
    end_date: Optional[datetime]
    line_items: List[Dict[str, Any]]
    payment_terms: int  # days
    active: bool = True
    last_generated: Optional[datetime] = None
    metadata: Dict[str, Any] = None


class RecurringInvoiceContract:
    """Smart contract for automated recurring invoices."""
    
    def __init__(self, blockchain_core):
        self.blockchain = blockchain_core
        self.rules: Dict[str, RecurringInvoiceRule] = {}
        self.frequency_deltas = {
            "weekly": timedelta(weeks=1),
            "biweekly": timedelta(weeks=2),
            "monthly": timedelta(days=30),  # Approximation
            "quarterly": timedelta(days=91),
            "yearly": timedelta(days=365)
        }
    
    async def create_rule(self, rule_data: Dict[str, Any]) -> str:
        """Create a new recurring invoice rule."""
        rule = RecurringInvoiceRule(
            rule_id=f"recurring_{int(datetime.now().timestamp() * 1000000)}",
            client_id=rule_data["client_id"],
            amount=rule_data["amount"],
            currency=rule_data["currency"],
            frequency=rule_data["frequency"],
            start_date=datetime.fromisoformat(rule_data["start_date"]),
            end_date=datetime.fromisoformat(rule_data["end_date"]) if rule_data.get("end_date") else None,
            line_items=rule_data["line_items"],
            payment_terms=rule_data.get("payment_terms", 30),
            metadata=rule_data.get("metadata", {})
        )
        
        self.rules[rule.rule_id] = rule
        
        # Record rule creation on blockchain
        transaction = {
            "transaction_id": f"contract_recurring_{rule.rule_id}",
            "timestamp": int(datetime.now().timestamp() * 1000000),
            "transaction_type": "smart_contract",
            "data": {
                "contract_type": "recurring_invoice_rule",
                "action": "create",
                "rule_id": rule.rule_id,
                "rule_data": rule_data
            }
        }
        
        await self.blockchain.add_transaction(transaction)
        return rule.rule_id
    
    async def check_and_generate_invoices(self) -> List[Dict[str, Any]]:
        """Check all rules and generate invoices as needed."""
        generated_invoices = []
        now = datetime.now()
        
        for rule_id, rule in self.rules.items():
            if not rule.active:
                continue
            
            if rule.end_date and now > rule.end_date:
                rule.active = False
                continue
            
            # Calculate next invoice date
            if rule.last_generated:
                next_date = rule.last_generated + self.frequency_deltas[rule.frequency]
            else:
                next_date = rule.start_date
            
            # Generate invoice if due
            if now >= next_date:
                invoice = await self.generate_invoice_from_rule(rule)
                generated_invoices.append(invoice)
                rule.last_generated = now
        
        return generated_invoices
    
    async def generate_invoice_from_rule(self, rule: RecurringInvoiceRule) -> Dict[str, Any]:
        """Generate an invoice from a recurring rule."""
        due_date = datetime.now() + timedelta(days=rule.payment_terms)
        
        invoice_data = {
            "client_id": rule.client_id,
            "amount": rule.amount,
            "currency": rule.currency,
            "line_items": rule.line_items,
            "due_date": due_date.isoformat(),
            "recurring_rule_id": rule.rule_id,
            "invoice_number": f"INV-{datetime.now().strftime('%Y%m%d')}-{rule.rule_id[-6:]}",
            "metadata": {
                **rule.metadata,
                "generated_by": "recurring_invoice_contract",
                "generation_date": datetime.now().isoformat()
            }
        }
        
        # Record invoice generation on blockchain
        transaction = {
            "transaction_id": f"invoice_{int(datetime.now().timestamp() * 1000000)}",
            "timestamp": int(datetime.now().timestamp() * 1000000),
            "transaction_type": "invoice",
            "data": invoice_data
        }
        
        await self.blockchain.add_transaction(transaction)
        
        return invoice_data
    
    async def update_rule(self, rule_id: str, updates: Dict[str, Any]) -> bool:
        """Update a recurring invoice rule."""
        if rule_id not in self.rules:
            return False
        
        rule = self.rules[rule_id]
        
        # Update allowed fields
        allowed_updates = ["amount", "line_items", "payment_terms", "end_date", "active"]
        for field in allowed_updates:
            if field in updates:
                setattr(rule, field, updates[field])
        
        # Record update on blockchain
        transaction = {
            "transaction_id": f"contract_update_{int(datetime.now().timestamp() * 1000000)}",
            "timestamp": int(datetime.now().timestamp() * 1000000),
            "transaction_type": "smart_contract",
            "data": {
                "contract_type": "recurring_invoice_rule",
                "action": "update",
                "rule_id": rule_id,
                "updates": updates
            }
        }
        
        await self.blockchain.add_transaction(transaction)
        return True
    
    def get_active_rules(self) -> List[RecurringInvoiceRule]:
        """Get all active recurring invoice rules."""
        return [rule for rule in self.rules.values() if rule.active]
    
    async def cancel_rule(self, rule_id: str) -> bool:
        """Cancel a recurring invoice rule."""
        return await self.update_rule(rule_id, {"active": False})