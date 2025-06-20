"""Freshbooks API client."""

import json
from typing import Dict, Any, List, Optional
from datetime import datetime
import aiohttp
from decimal import Decimal

from .auth import FreshbooksAuth
from .models import Invoice, Payment, Expense, Client, TimeEntry


class FreshbooksClient:
    """Client for interacting with Freshbooks API."""
    
    def __init__(self, auth: FreshbooksAuth):
        self.auth = auth
        self.api_base = "https://api.freshbooks.com"
    
    async def _request(self, method: str, endpoint: str, data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Make authenticated API request."""
        # Ensure we're authenticated
        if not await self.auth.authenticate():
            raise Exception("Failed to authenticate with Freshbooks")
        
        url = f"{self.api_base}{endpoint}"
        headers = self.auth.get_headers()
        
        async with aiohttp.ClientSession() as session:
            kwargs = {"headers": headers}
            if data:
                kwargs["json"] = data
            
            async with session.request(method, url, **kwargs) as resp:
                response_data = await resp.json()
                
                if resp.status >= 400:
                    error_msg = response_data.get("message", "API request failed")
                    raise Exception(f"Freshbooks API error: {error_msg}")
                
                return response_data
    
    # Invoice methods
    async def list_invoices(self, status: Optional[str] = None, client_id: Optional[int] = None) -> List[Invoice]:
        """List invoices with optional filters."""
        endpoint = f"/accounting/account/{self.auth.account_id}/invoices/invoices"
        
        params = {}
        if status:
            params["search[status]"] = status
        if client_id:
            params["search[client_id]"] = client_id
        
        # Add params to endpoint
        if params:
            param_str = "&".join([f"{k}={v}" for k, v in params.items()])
            endpoint = f"{endpoint}?{param_str}"
        
        response = await self._request("GET", endpoint)
        
        invoices = []
        for invoice_data in response.get("response", {}).get("result", {}).get("invoices", []):
            invoices.append(Invoice.from_api_data(invoice_data))
        
        return invoices
    
    async def create_invoice(self, invoice_data: Dict[str, Any]) -> Invoice:
        """Create a new invoice."""
        endpoint = f"/accounting/account/{self.auth.account_id}/invoices/invoices"
        
        # Prepare invoice data
        api_data = {
            "invoice": {
                "client_id": invoice_data["client_id"],
                "lines": [
                    {
                        "name": item.get("name", "Service"),
                        "description": item.get("description", ""),
                        "rate": {"amount": str(item["rate"]), "code": invoice_data.get("currency", "USD")},
                        "quantity": item["quantity"]
                    }
                    for item in invoice_data["line_items"]
                ],
                "due_date": invoice_data["due_date"],
                "notes": invoice_data.get("notes", "")
            }
        }
        
        response = await self._request("POST", endpoint, api_data)
        return Invoice.from_api_data(response["response"]["result"]["invoice"])
    
    async def send_invoice(self, invoice_id: int, email_message: Optional[str] = None) -> bool:
        """Send invoice via email."""
        endpoint = f"/accounting/account/{self.auth.account_id}/invoices/invoices/{invoice_id}"
        
        data = {
            "invoice": {
                "action_email": {
                    "send": True,
                    "email_message": email_message or "Please find your invoice attached."
                }
            }
        }
        
        response = await self._request("PUT", endpoint, data)
        return response.get("response", {}).get("ok", False)
    
    async def mark_invoice_paid(self, invoice_id: int, amount: Decimal, payment_method: str) -> Payment:
        """Mark invoice as paid by creating a payment."""
        # Get invoice details first
        invoice_endpoint = f"/accounting/account/{self.auth.account_id}/invoices/invoices/{invoice_id}"
        invoice_response = await self._request("GET", invoice_endpoint)
        invoice_data = invoice_response["response"]["result"]["invoice"]
        
        # Create payment
        payment_data = {
            "payment": {
                "invoice_id": invoice_id,
                "amount": {"amount": str(amount), "code": invoice_data["currency_code"]},
                "date": datetime.now().strftime("%Y-%m-%d"),
                "type": payment_method
            }
        }
        
        payment_endpoint = f"/accounting/account/{self.auth.account_id}/payments/payments"
        response = await self._request("POST", payment_endpoint, payment_data)
        return Payment.from_api_data(response["response"]["result"]["payment"])
    
    # Expense methods
    async def record_expense(self, expense_data: Dict[str, Any]) -> Expense:
        """Record a new expense."""
        endpoint = f"/accounting/account/{self.auth.account_id}/expenses/expenses"
        
        api_data = {
            "expense": {
                "amount": {"amount": str(expense_data["amount"]), "code": expense_data.get("currency", "USD")},
                "category_id": expense_data.get("category_id"),
                "notes": expense_data["description"],
                "date": expense_data.get("date", datetime.now().strftime("%Y-%m-%d")),
                "vendor": expense_data.get("vendor", "")
            }
        }
        
        response = await self._request("POST", endpoint, api_data)
        return Expense.from_api_data(response["response"]["result"]["expense"])
    
    async def list_expenses(self, start_date: Optional[str] = None, end_date: Optional[str] = None, category_id: Optional[int] = None) -> List[Expense]:
        """List expenses with optional filters."""
        endpoint = f"/accounting/account/{self.auth.account_id}/expenses/expenses"
        
        params = {}
        if start_date:
            params["search[date_from]"] = start_date
        if end_date:
            params["search[date_to]"] = end_date
        if category_id:
            params["search[category_id]"] = category_id
        
        if params:
            param_str = "&".join([f"{k}={v}" for k, v in params.items()])
            endpoint = f"{endpoint}?{param_str}"
        
        response = await self._request("GET", endpoint)
        
        expenses = []
        for expense_data in response.get("response", {}).get("result", {}).get("expenses", []):
            expenses.append(Expense.from_api_data(expense_data))
        
        return expenses
    
    # Client methods
    async def list_clients(self, active: bool = True) -> List[Client]:
        """List clients."""
        endpoint = f"/accounting/account/{self.auth.account_id}/users/clients"
        
        if active:
            endpoint += "?search[vis_state]=0"  # 0 = active, 1 = deleted
        
        response = await self._request("GET", endpoint)
        
        clients = []
        for client_data in response.get("response", {}).get("result", {}).get("clients", []):
            clients.append(Client.from_api_data(client_data))
        
        return clients
    
    async def create_client(self, client_data: Dict[str, Any]) -> Client:
        """Create a new client."""
        endpoint = f"/accounting/account/{self.auth.account_id}/users/clients"
        
        api_data = {
            "client": {
                "organization": client_data.get("organization", ""),
                "first_name": client_data.get("first_name", ""),
                "last_name": client_data.get("last_name", ""),
                "email": client_data["email"],
                "phone": client_data.get("phone", ""),
                "street": client_data.get("street", ""),
                "city": client_data.get("city", ""),
                "province": client_data.get("province", ""),
                "postal_code": client_data.get("postal_code", ""),
                "country": client_data.get("country", "US")
            }
        }
        
        response = await self._request("POST", endpoint, api_data)
        return Client.from_api_data(response["response"]["result"]["client"])
    
    async def get_client_balance(self, client_id: int) -> Dict[str, Decimal]:
        """Get client's current balance."""
        # Get all invoices for client
        invoices = await self.list_invoices(client_id=client_id)
        
        total_invoiced = Decimal("0")
        total_paid = Decimal("0")
        outstanding = Decimal("0")
        
        for invoice in invoices:
            total_invoiced += invoice.amount
            total_paid += invoice.paid
            outstanding += invoice.outstanding
        
        return {
            "total_invoiced": total_invoiced,
            "total_paid": total_paid,
            "outstanding": outstanding
        }
    
    # Time tracking methods
    async def log_time(self, time_entry_data: Dict[str, Any]) -> TimeEntry:
        """Log time entry."""
        endpoint = f"/timetracking/business/{self.auth.account_id}/time_entries"
        
        api_data = {
            "time_entry": {
                "client_id": time_entry_data.get("client_id"),
                "project_id": time_entry_data.get("project_id"),
                "duration": time_entry_data["duration"],  # in seconds
                "note": time_entry_data["notes"],
                "started_at": time_entry_data.get("started_at", datetime.now().isoformat())
            }
        }
        
        response = await self._request("POST", endpoint, api_data)
        return TimeEntry.from_api_data(response["time_entry"])
    
    async def list_time_entries(self, client_id: Optional[int] = None, project_id: Optional[int] = None) -> List[TimeEntry]:
        """List time entries with optional filters."""
        endpoint = f"/timetracking/business/{self.auth.account_id}/time_entries"
        
        params = {}
        if client_id:
            params["client_id"] = client_id
        if project_id:
            params["project_id"] = project_id
        
        if params:
            param_str = "&".join([f"{k}={v}" for k, v in params.items()])
            endpoint = f"{endpoint}?{param_str}"
        
        response = await self._request("GET", endpoint)
        
        entries = []
        for entry_data in response.get("time_entries", []):
            entries.append(TimeEntry.from_api_data(entry_data))
        
        return entries