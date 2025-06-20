"""Transaction validators for accounting rules."""

from typing import Dict, Any, List, Optional
from datetime import datetime
import re


class TransactionValidator:
    """Validates financial transactions according to accounting rules."""
    
    def __init__(self):
        self.validation_rules = {
            "invoice": self.validate_invoice,
            "payment": self.validate_payment,
            "expense": self.validate_expense,
            "credit": self.validate_credit,
            "refund": self.validate_refund,
            "time_entry": self.validate_time_entry
        }
    
    def validate_transaction(self, transaction_type: str, data: Dict[str, Any]) -> tuple[bool, Optional[str]]:
        """Validate a transaction based on its type."""
        if transaction_type not in self.validation_rules:
            return False, f"Unknown transaction type: {transaction_type}"
        
        return self.validation_rules[transaction_type](data)
    
    def validate_invoice(self, data: Dict[str, Any]) -> tuple[bool, Optional[str]]:
        """Validate invoice transaction."""
        required_fields = ["client_id", "amount", "currency", "line_items", "due_date"]
        
        # Check required fields
        for field in required_fields:
            if field not in data:
                return False, f"Missing required field: {field}"
        
        # Validate amount
        if not isinstance(data["amount"], (int, float)) or data["amount"] <= 0:
            return False, "Invoice amount must be positive"
        
        # Validate currency
        valid_currencies = ["USD", "CAD", "EUR", "GBP", "AUD"]
        if data["currency"] not in valid_currencies:
            return False, f"Invalid currency: {data['currency']}"
        
        # Validate line items
        if not isinstance(data["line_items"], list) or len(data["line_items"]) == 0:
            return False, "Invoice must have at least one line item"
        
        total = 0
        for item in data["line_items"]:
            if "quantity" not in item or "rate" not in item:
                return False, "Line items must have quantity and rate"
            
            if item["quantity"] <= 0 or item["rate"] <= 0:
                return False, "Line item quantity and rate must be positive"
            
            total += item["quantity"] * item["rate"]
        
        # Verify total matches
        if abs(total - data["amount"]) > 0.01:  # Allow for rounding errors
            return False, f"Line items total ({total}) doesn't match invoice amount ({data['amount']})"
        
        # Validate due date
        try:
            due_date = datetime.fromisoformat(data["due_date"].replace('Z', '+00:00'))
            if due_date < datetime.now():
                return False, "Due date cannot be in the past"
        except:
            return False, "Invalid due date format"
        
        return True, None
    
    def validate_payment(self, data: Dict[str, Any]) -> tuple[bool, Optional[str]]:
        """Validate payment transaction."""
        required_fields = ["invoice_id", "amount", "currency", "payment_method"]
        
        for field in required_fields:
            if field not in data:
                return False, f"Missing required field: {field}"
        
        # Validate amount
        if not isinstance(data["amount"], (int, float)) or data["amount"] <= 0:
            return False, "Payment amount must be positive"
        
        # Validate payment method
        valid_methods = ["credit_card", "debit_card", "bank_transfer", "check", "cash", "crypto"]
        if data["payment_method"] not in valid_methods:
            return False, f"Invalid payment method: {data['payment_method']}"
        
        return True, None
    
    def validate_expense(self, data: Dict[str, Any]) -> tuple[bool, Optional[str]]:
        """Validate expense transaction."""
        required_fields = ["amount", "currency", "category", "description"]
        
        for field in required_fields:
            if field not in data:
                return False, f"Missing required field: {field}"
        
        # Validate amount
        if not isinstance(data["amount"], (int, float)) or data["amount"] <= 0:
            return False, "Expense amount must be positive"
        
        # Validate category
        valid_categories = [
            "office_supplies", "travel", "meals", "entertainment",
            "utilities", "rent", "insurance", "professional_services",
            "software", "hardware", "marketing", "other"
        ]
        if data["category"] not in valid_categories:
            return False, f"Invalid expense category: {data['category']}"
        
        # Validate description
        if not data["description"] or len(data["description"]) < 3:
            return False, "Expense description must be at least 3 characters"
        
        return True, None
    
    def validate_credit(self, data: Dict[str, Any]) -> tuple[bool, Optional[str]]:
        """Validate credit transaction."""
        required_fields = ["invoice_id", "amount", "reason"]
        
        for field in required_fields:
            if field not in data:
                return False, f"Missing required field: {field}"
        
        if not isinstance(data["amount"], (int, float)) or data["amount"] <= 0:
            return False, "Credit amount must be positive"
        
        return True, None
    
    def validate_refund(self, data: Dict[str, Any]) -> tuple[bool, Optional[str]]:
        """Validate refund transaction."""
        required_fields = ["payment_id", "amount", "reason"]
        
        for field in required_fields:
            if field not in data:
                return False, f"Missing required field: {field}"
        
        if not isinstance(data["amount"], (int, float)) or data["amount"] <= 0:
            return False, "Refund amount must be positive"
        
        return True, None
    
    def validate_time_entry(self, data: Dict[str, Any]) -> tuple[bool, Optional[str]]:
        """Validate time entry transaction."""
        required_fields = ["project_id", "duration", "description"]
        
        for field in required_fields:
            if field not in data:
                return False, f"Missing required field: {field}"
        
        # Validate duration
        if not isinstance(data["duration"], (int, float)) or data["duration"] <= 0:
            return False, "Duration must be positive"
        
        # Validate description
        if not data["description"] or len(data["description"]) < 10:
            return False, "Time entry description must be at least 10 characters"
        
        return True, None


class ComplianceValidator:
    """Validates transactions for regulatory compliance."""
    
    def __init__(self, jurisdiction: str = "US"):
        self.jurisdiction = jurisdiction
    
    def validate_tax_compliance(self, transaction_type: str, data: Dict[str, Any]) -> tuple[bool, Optional[str]]:
        """Validate tax compliance requirements."""
        if self.jurisdiction == "US":
            return self._validate_us_tax_compliance(transaction_type, data)
        # Add other jurisdictions as needed
        return True, None
    
    def _validate_us_tax_compliance(self, transaction_type: str, data: Dict[str, Any]) -> tuple[bool, Optional[str]]:
        """US-specific tax compliance validation."""
        if transaction_type == "invoice":
            # Check for tax ID if amount exceeds threshold
            if data.get("amount", 0) > 600 and "client_tax_id" not in data:
                return False, "Client tax ID required for invoices over $600 (1099 reporting)"
        
        elif transaction_type == "expense":
            # Validate receipt requirement for expenses over $75
            if data.get("amount", 0) > 75 and "receipt_url" not in data:
                return False, "Receipt required for expenses over $75"
        
        return True, None
    
    def validate_data_protection(self, data: Dict[str, Any]) -> tuple[bool, Optional[str]]:
        """Validate data protection compliance (GDPR, etc)."""
        # Check for PII in appropriate fields only
        sensitive_fields = ["notes", "description", "memo"]
        
        # Simple PII patterns (SSN, credit card)
        ssn_pattern = re.compile(r'\b\d{3}-\d{2}-\d{4}\b')
        cc_pattern = re.compile(r'\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b')
        
        for field in sensitive_fields:
            if field in data and isinstance(data[field], str):
                if ssn_pattern.search(data[field]):
                    return False, f"SSN detected in {field} - remove sensitive data"
                if cc_pattern.search(data[field]):
                    return False, f"Credit card number detected in {field} - remove sensitive data"
        
        return True, None