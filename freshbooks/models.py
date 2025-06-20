"""Data models for Freshbooks entities."""

from typing import Dict, Any, List, Optional
from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel, Field


class LineItem(BaseModel):
    """Invoice line item."""
    name: str = "Service"
    description: str = ""
    quantity: float
    rate: Decimal
    amount: Optional[Decimal] = None
    
    def calculate_amount(self) -> Decimal:
        """Calculate line item amount."""
        return Decimal(str(self.quantity)) * self.rate


class Invoice(BaseModel):
    """Invoice model."""
    id: Optional[int] = None
    invoice_number: str
    client_id: int
    status: str  # draft, sent, viewed, paid, overdue
    amount: Decimal
    outstanding: Decimal
    paid: Decimal
    currency_code: str = "USD"
    due_date: datetime
    issue_date: datetime
    line_items: List[LineItem] = []
    notes: str = ""
    
    @classmethod
    def from_api_data(cls, data: Dict[str, Any]) -> "Invoice":
        """Create invoice from API response data."""
        line_items = []
        for line in data.get("lines", []):
            line_items.append(LineItem(
                name=line.get("name", "Service"),
                description=line.get("description", ""),
                quantity=float(line["qty"]),
                rate=Decimal(line["rate"]["amount"])
            ))
        
        return cls(
            id=data.get("id"),
            invoice_number=data["invoice_number"],
            client_id=data["clientid"],
            status=data["v3_status"],
            amount=Decimal(data["amount"]["amount"]),
            outstanding=Decimal(data["outstanding"]["amount"]),
            paid=Decimal(data["paid"]["amount"]),
            currency_code=data["currency_code"],
            due_date=datetime.fromisoformat(data["due_date"]),
            issue_date=datetime.fromisoformat(data["date"]),
            line_items=line_items,
            notes=data.get("notes", "")
        )


class Payment(BaseModel):
    """Payment model."""
    id: Optional[int] = None
    invoice_id: int
    amount: Decimal
    currency_code: str = "USD"
    date: datetime
    type: str  # credit_card, bank_transfer, check, cash
    notes: str = ""
    
    @classmethod
    def from_api_data(cls, data: Dict[str, Any]) -> "Payment":
        """Create payment from API response data."""
        return cls(
            id=data.get("id"),
            invoice_id=data["invoiceid"],
            amount=Decimal(data["amount"]["amount"]),
            currency_code=data["amount"]["code"],
            date=datetime.fromisoformat(data["date"]),
            type=data["type"],
            notes=data.get("notes", "")
        )


class Expense(BaseModel):
    """Expense model."""
    id: Optional[int] = None
    amount: Decimal
    currency_code: str = "USD"
    category_id: Optional[int] = None
    category_name: Optional[str] = None
    vendor: str = ""
    date: datetime
    notes: str
    receipt_url: Optional[str] = None
    
    @classmethod
    def from_api_data(cls, data: Dict[str, Any]) -> "Expense":
        """Create expense from API response data."""
        return cls(
            id=data.get("id"),
            amount=Decimal(data["amount"]["amount"]),
            currency_code=data["amount"]["code"],
            category_id=data.get("categoryid"),
            category_name=data.get("category_name"),
            vendor=data.get("vendor", ""),
            date=datetime.fromisoformat(data["date"]),
            notes=data.get("notes", ""),
            receipt_url=data.get("attachment", {}).get("media_url")
        )


class Client(BaseModel):
    """Client model."""
    id: Optional[int] = None
    organization: str = ""
    first_name: str = ""
    last_name: str = ""
    email: str
    phone: str = ""
    street: str = ""
    city: str = ""
    province: str = ""
    postal_code: str = ""
    country: str = "US"
    
    @property
    def display_name(self) -> str:
        """Get display name for client."""
        if self.organization:
            return self.organization
        return f"{self.first_name} {self.last_name}".strip()
    
    @classmethod
    def from_api_data(cls, data: Dict[str, Any]) -> "Client":
        """Create client from API response data."""
        return cls(
            id=data.get("id"),
            organization=data.get("organization", ""),
            first_name=data.get("fname", ""),
            last_name=data.get("lname", ""),
            email=data["email"],
            phone=data.get("phone", ""),
            street=data.get("street", ""),
            city=data.get("city", ""),
            province=data.get("province", ""),
            postal_code=data.get("postal_code", ""),
            country=data.get("country", "US")
        )


class TimeEntry(BaseModel):
    """Time entry model."""
    id: Optional[int] = None
    client_id: Optional[int] = None
    project_id: Optional[int] = None
    duration: int  # seconds
    note: str
    started_at: datetime
    is_logged: bool = True
    
    @classmethod
    def from_api_data(cls, data: Dict[str, Any]) -> "TimeEntry":
        """Create time entry from API response data."""
        return cls(
            id=data.get("id"),
            client_id=data.get("client_id"),
            project_id=data.get("project_id"),
            duration=data["duration"],
            note=data.get("note", ""),
            started_at=datetime.fromisoformat(data["started_at"]),
            is_logged=data.get("is_logged", True)
        )