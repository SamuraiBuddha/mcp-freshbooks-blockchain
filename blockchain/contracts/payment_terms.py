"""Smart contract for payment terms enforcement."""

import json
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
from decimal import Decimal
from dataclasses import dataclass, field
import asyncio


@dataclass
class PaymentTerm:
    """Defines payment terms for an invoice."""
    
    term_id: str
    invoice_id: str
    due_date: datetime
    discount_percentage: Optional[Decimal] = None
    discount_deadline: Optional[datetime] = None
    late_fee_percentage: Optional[Decimal] = None
    late_fee_grace_days: int = 0
    payment_schedule: Optional[List[Dict[str, Any]]] = None  # For installments
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PaymentReminder:
    """Payment reminder configuration."""
    
    reminder_id: str
    invoice_id: str
    reminder_date: datetime
    reminder_type: str  # friendly, urgent, final
    sent: bool = False
    response: Optional[str] = None


class PaymentTermsContract:
    """Smart contract for automated payment terms enforcement."""
    
    def __init__(self, blockchain_core):
        self.blockchain = blockchain_core
        self.payment_terms: Dict[str, PaymentTerm] = {}
        self.reminders: Dict[str, PaymentReminder] = {}
        self.payment_history: Dict[str, List[Dict[str, Any]]] = {}  # invoice_id -> payments
        
        # Default reminder schedule (days before due)
        self.reminder_schedule = {
            "friendly": [14, 7],  # 14 and 7 days before
            "urgent": [3, 1],     # 3 and 1 day before
            "final": [-1, -7]     # 1 and 7 days after due
        }
    
    async def create_payment_terms(self, 
                                 invoice_id: str,
                                 invoice_amount: Decimal,
                                 due_days: int = 30,
                                 early_payment_discount: Optional[Tuple[Decimal, int]] = None,
                                 late_fee: Optional[Tuple[Decimal, int]] = None,
                                 installments: Optional[List[Dict[str, Any]]] = None) -> str:
        """Create payment terms for an invoice."""
        
        term_id = f"terms_{int(datetime.now().timestamp() * 1000000)}"
        due_date = datetime.now() + timedelta(days=due_days)
        
        # Process early payment discount
        discount_percentage = None
        discount_deadline = None
        if early_payment_discount:
            discount_percentage = early_payment_discount[0]
            discount_deadline = datetime.now() + timedelta(days=early_payment_discount[1])
        
        # Process late fee
        late_fee_percentage = None
        late_fee_grace_days = 0
        if late_fee:
            late_fee_percentage = late_fee[0]
            late_fee_grace_days = late_fee[1]
        
        # Create payment schedule if installments requested
        payment_schedule = None
        if installments:
            payment_schedule = self._create_installment_schedule(
                invoice_amount, installments, due_days
            )
        
        payment_term = PaymentTerm(
            term_id=term_id,
            invoice_id=invoice_id,
            due_date=due_date,
            discount_percentage=discount_percentage,
            discount_deadline=discount_deadline,
            late_fee_percentage=late_fee_percentage,
            late_fee_grace_days=late_fee_grace_days,
            payment_schedule=payment_schedule
        )
        
        self.payment_terms[term_id] = payment_term
        
        # Record on blockchain
        transaction = {
            "transaction_id": term_id,
            "timestamp": int(datetime.now().timestamp() * 1000000),
            "transaction_type": "smart_contract",
            "data": {
                "contract_type": "payment_terms",
                "action": "create",
                "invoice_id": invoice_id,
                "due_date": due_date.isoformat(),
                "terms": {
                    "discount": f"{discount_percentage}% by {discount_deadline.isoformat()}" if discount_percentage else None,
                    "late_fee": f"{late_fee_percentage}% after {late_fee_grace_days} days" if late_fee_percentage else None,
                    "installments": len(payment_schedule) if payment_schedule else None
                }
            }
        }
        
        await self.blockchain.add_transaction(transaction)
        
        # Schedule reminders
        await self._schedule_reminders(invoice_id, due_date)
        
        return term_id
    
    def _create_installment_schedule(self, 
                                   total_amount: Decimal,
                                   installments: List[Dict[str, Any]],
                                   base_due_days: int) -> List[Dict[str, Any]]:
        """Create installment payment schedule."""
        schedule = []
        remaining = total_amount
        
        for i, installment in enumerate(installments):
            if "percentage" in installment:
                amount = total_amount * (Decimal(str(installment["percentage"])) / 100)
            elif "amount" in installment:
                amount = Decimal(str(installment["amount"]))
            else:
                # Equal installments
                amount = total_amount / len(installments)
            
            due_date = datetime.now() + timedelta(
                days=base_due_days + (i * installment.get("interval_days", 30))
            )
            
            schedule.append({
                "installment_number": i + 1,
                "amount": float(amount.quantize(Decimal("0.01"))),
                "due_date": due_date.isoformat(),
                "paid": False,
                "paid_date": None,
                "paid_amount": None
            })
            
            remaining -= amount
        
        # Adjust last installment for rounding
        if remaining != 0:
            schedule[-1]["amount"] += float(remaining)
        
        return schedule
    
    async def _schedule_reminders(self, invoice_id: str, due_date: datetime) -> None:
        """Schedule payment reminders."""
        for reminder_type, days_list in self.reminder_schedule.items():
            for days in days_list:
                reminder_date = due_date - timedelta(days=days)
                
                # Only schedule future reminders
                if reminder_date > datetime.now():
                    reminder = PaymentReminder(
                        reminder_id=f"reminder_{invoice_id}_{reminder_type}_{days}",
                        invoice_id=invoice_id,
                        reminder_date=reminder_date,
                        reminder_type=reminder_type
                    )
                    
                    self.reminders[reminder.reminder_id] = reminder
    
    async def process_payment(self, 
                            invoice_id: str,
                            payment_amount: Decimal,
                            payment_date: Optional[datetime] = None) -> Dict[str, Any]:
        """Process a payment and calculate applicable discounts/fees."""
        
        payment_date = payment_date or datetime.now()
        
        # Find payment terms for invoice
        terms = None
        for term in self.payment_terms.values():
            if term.invoice_id == invoice_id:
                terms = term
                break
        
        if not terms:
            return {
                "error": "No payment terms found for invoice",
                "invoice_id": invoice_id
            }
        
        result = {
            "invoice_id": invoice_id,
            "payment_amount": float(payment_amount),
            "payment_date": payment_date.isoformat(),
            "applied_discount": 0,
            "applied_late_fee": 0,
            "net_amount": float(payment_amount)
        }
        
        # Check for early payment discount
        if (terms.discount_percentage and 
            terms.discount_deadline and 
            payment_date <= terms.discount_deadline):
            
            discount = payment_amount * (terms.discount_percentage / 100)
            result["applied_discount"] = float(discount)
            result["net_amount"] = float(payment_amount - discount)
            result["discount_reason"] = f"Early payment by {terms.discount_deadline}"
        
        # Check for late fee
        elif payment_date > terms.due_date:
            days_late = (payment_date - terms.due_date).days
            
            if days_late > terms.late_fee_grace_days and terms.late_fee_percentage:
                late_fee = payment_amount * (terms.late_fee_percentage / 100)
                result["applied_late_fee"] = float(late_fee)
                result["net_amount"] = float(payment_amount + late_fee)
                result["late_fee_reason"] = f"{days_late} days late"
        
        # Record payment
        if invoice_id not in self.payment_history:
            self.payment_history[invoice_id] = []
        
        self.payment_history[invoice_id].append({
            "payment_date": payment_date.isoformat(),
            "amount": float(payment_amount),
            "discount": result["applied_discount"],
            "late_fee": result["applied_late_fee"],
            "net_amount": result["net_amount"]
        })
        
        # Update installment schedule if applicable
        if terms.payment_schedule:
            await self._update_installment_payment(
                terms, payment_amount, payment_date
            )
        
        # Record on blockchain
        transaction = {
            "transaction_id": f"payment_terms_{int(datetime.now().timestamp() * 1000000)}",
            "timestamp": int(datetime.now().timestamp() * 1000000),
            "transaction_type": "smart_contract",
            "data": {
                "contract_type": "payment_terms",
                "action": "payment_processed",
                "invoice_id": invoice_id,
                "payment_result": result
            }
        }
        
        await self.blockchain.add_transaction(transaction)
        
        # Cancel future reminders if paid in full
        if await self._is_invoice_paid_in_full(invoice_id):
            await self._cancel_reminders(invoice_id)
        
        return result
    
    async def _update_installment_payment(self,
                                        terms: PaymentTerm,
                                        payment_amount: Decimal,
                                        payment_date: datetime) -> None:
        """Update installment schedule with payment."""
        remaining_payment = payment_amount
        
        for installment in terms.payment_schedule:
            if installment["paid"] or remaining_payment <= 0:
                continue
            
            installment_amount = Decimal(str(installment["amount"]))
            
            if remaining_payment >= installment_amount:
                # Pay full installment
                installment["paid"] = True
                installment["paid_date"] = payment_date.isoformat()
                installment["paid_amount"] = float(installment_amount)
                remaining_payment -= installment_amount
            else:
                # Partial payment
                installment["paid_amount"] = float(remaining_payment)
                remaining_payment = Decimal("0")
    
    async def _is_invoice_paid_in_full(self, invoice_id: str) -> bool:
        """Check if invoice is fully paid."""
        # This would normally check against the invoice total
        # For now, return True if any payment exists
        return invoice_id in self.payment_history
    
    async def _cancel_reminders(self, invoice_id: str) -> None:
        """Cancel future reminders for paid invoice."""
        for reminder in self.reminders.values():
            if reminder.invoice_id == invoice_id and not reminder.sent:
                reminder.sent = True
                reminder.response = "Cancelled - Invoice paid"
    
    async def check_and_send_reminders(self) -> List[Dict[str, Any]]:
        """Check for due reminders and return list to send."""
        due_reminders = []
        now = datetime.now()
        
        for reminder in self.reminders.values():
            if not reminder.sent and reminder.reminder_date <= now:
                due_reminders.append({
                    "reminder_id": reminder.reminder_id,
                    "invoice_id": reminder.invoice_id,
                    "reminder_type": reminder.reminder_type,
                    "reminder_date": reminder.reminder_date.isoformat()
                })
                
                reminder.sent = True
                reminder.response = f"Sent at {now.isoformat()}"
        
        if due_reminders:
            # Record on blockchain
            transaction = {
                "transaction_id": f"reminders_{int(now.timestamp() * 1000000)}",
                "timestamp": int(now.timestamp() * 1000000),
                "transaction_type": "smart_contract",
                "data": {
                    "contract_type": "payment_terms",
                    "action": "reminders_sent",
                    "reminder_count": len(due_reminders),
                    "reminders": due_reminders
                }
            }
            
            await self.blockchain.add_transaction(transaction)
        
        return due_reminders
    
    async def get_payment_status(self, invoice_id: str) -> Dict[str, Any]:
        """Get comprehensive payment status for an invoice."""
        
        # Find terms
        terms = None
        for term in self.payment_terms.values():
            if term.invoice_id == invoice_id:
                terms = term
                break
        
        if not terms:
            return {"error": "No payment terms found"}
        
        # Calculate status
        now = datetime.now()
        days_until_due = (terms.due_date - now).days
        is_overdue = now > terms.due_date
        
        status = {
            "invoice_id": invoice_id,
            "due_date": terms.due_date.isoformat(),
            "days_until_due": days_until_due if not is_overdue else 0,
            "days_overdue": abs(days_until_due) if is_overdue else 0,
            "is_overdue": is_overdue,
            "payment_history": self.payment_history.get(invoice_id, []),
            "terms": {
                "discount": {
                    "percentage": float(terms.discount_percentage) if terms.discount_percentage else None,
                    "deadline": terms.discount_deadline.isoformat() if terms.discount_deadline else None,
                    "available": bool(terms.discount_deadline and now <= terms.discount_deadline)
                },
                "late_fee": {
                    "percentage": float(terms.late_fee_percentage) if terms.late_fee_percentage else None,
                    "grace_days": terms.late_fee_grace_days,
                    "applies": is_overdue and (now - terms.due_date).days > terms.late_fee_grace_days
                }
            },
            "reminders": {
                "sent": [],
                "pending": []
            }
        }
        
        # Add reminder status
        for reminder in self.reminders.values():
            if reminder.invoice_id == invoice_id:
                reminder_info = {
                    "type": reminder.reminder_type,
                    "date": reminder.reminder_date.isoformat()
                }
                
                if reminder.sent:
                    status["reminders"]["sent"].append(reminder_info)
                else:
                    status["reminders"]["pending"].append(reminder_info)
        
        # Add installment status if applicable
        if terms.payment_schedule:
            status["installments"] = terms.payment_schedule
        
        return status