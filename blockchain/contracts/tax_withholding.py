"""Smart contract for automatic tax withholding."""

import json
from datetime import datetime
from typing import Dict, Any, List, Optional
from decimal import Decimal, ROUND_HALF_UP


class TaxWithholdingContract:
    """Smart contract for automated tax calculation and withholding."""
    
    def __init__(self, blockchain_core, jurisdiction: str = "US"):
        self.blockchain = blockchain_core
        self.jurisdiction = jurisdiction
        self.withholdings: Dict[str, Dict[str, Any]] = {}
        
        # Tax rates by jurisdiction (simplified)
        self.tax_rates = {
            "US": {
                "federal_income": {
                    "self_employed": Decimal("0.153"),  # 15.3% SE tax
                    "estimated": Decimal("0.25")  # 25% estimated tax
                },
                "state_income": {
                    "FL": Decimal("0.0"),  # No state income tax
                    "CA": Decimal("0.093"),  # California rate
                    "NY": Decimal("0.0685")
                },
                "sales_tax": {
                    "FL": Decimal("0.06"),
                    "CA": Decimal("0.0725"),
                    "NY": Decimal("0.08")
                }
            },
            "CA": {
                "federal_income": Decimal("0.15"),
                "provincial_income": Decimal("0.10"),
                "gst": Decimal("0.05")
            }
        }
    
    async def calculate_withholding(self, transaction_type: str, amount: Decimal, metadata: Dict[str, Any]) -> Dict[str, Decimal]:
        """Calculate tax withholding for a transaction."""
        withholding = {}
        
        if self.jurisdiction == "US":
            withholding = await self._calculate_us_withholding(transaction_type, amount, metadata)
        elif self.jurisdiction == "CA":
            withholding = await self._calculate_canadian_withholding(transaction_type, amount, metadata)
        
        # Record withholding calculation on blockchain
        if withholding:
            await self._record_withholding(transaction_type, amount, withholding, metadata)
        
        return withholding
    
    async def _calculate_us_withholding(self, transaction_type: str, amount: Decimal, metadata: Dict[str, Any]) -> Dict[str, Decimal]:
        """Calculate US tax withholding."""
        withholding = {}
        state = metadata.get("state", "FL")
        
        if transaction_type == "payment":
            # Income received - calculate withholding
            rates = self.tax_rates["US"]
            
            # Self-employment tax (Social Security + Medicare)
            se_tax = amount * rates["federal_income"]["self_employed"]
            withholding["self_employment_tax"] = se_tax.quantize(Decimal("0.01"), ROUND_HALF_UP)
            
            # Estimated federal income tax
            fed_tax = amount * rates["federal_income"]["estimated"]
            withholding["federal_income_tax"] = fed_tax.quantize(Decimal("0.01"), ROUND_HALF_UP)
            
            # State income tax
            state_rate = rates["state_income"].get(state, Decimal("0.0"))
            if state_rate > 0:
                state_tax = amount * state_rate
                withholding["state_income_tax"] = state_tax.quantize(Decimal("0.01"), ROUND_HALF_UP)
        
        elif transaction_type == "invoice" and metadata.get("collect_sales_tax"):
            # Sales tax collection
            client_state = metadata.get("client_state", state)
            sales_tax_rate = self.tax_rates["US"]["sales_tax"].get(client_state, Decimal("0.0"))
            
            if sales_tax_rate > 0:
                sales_tax = amount * sales_tax_rate
                withholding["sales_tax"] = sales_tax.quantize(Decimal("0.01"), ROUND_HALF_UP)
        
        return withholding
    
    async def _calculate_canadian_withholding(self, transaction_type: str, amount: Decimal, metadata: Dict[str, Any]) -> Dict[str, Decimal]:
        """Calculate Canadian tax withholding."""
        withholding = {}
        rates = self.tax_rates["CA"]
        
        if transaction_type == "payment":
            # Income tax withholding
            fed_tax = amount * rates["federal_income"]
            prov_tax = amount * rates["provincial_income"]
            
            withholding["federal_income_tax"] = fed_tax.quantize(Decimal("0.01"), ROUND_HALF_UP)
            withholding["provincial_income_tax"] = prov_tax.quantize(Decimal("0.01"), ROUND_HALF_UP)
        
        elif transaction_type == "invoice":
            # GST/HST
            gst = amount * rates["gst"]
            withholding["gst_hst"] = gst.quantize(Decimal("0.01"), ROUND_HALF_UP)
        
        return withholding
    
    async def _record_withholding(self, transaction_type: str, amount: Decimal, withholding: Dict[str, Decimal], metadata: Dict[str, Any]) -> None:
        """Record tax withholding on blockchain."""
        withholding_id = f"withholding_{int(datetime.now().timestamp() * 1000000)}"
        
        # Convert Decimal to float for JSON serialization
        withholding_float = {k: float(v) for k, v in withholding.items()}
        
        transaction = {
            "transaction_id": withholding_id,
            "timestamp": int(datetime.now().timestamp() * 1000000),
            "transaction_type": "tax_withholding",
            "data": {
                "original_transaction_type": transaction_type,
                "gross_amount": float(amount),
                "withholdings": withholding_float,
                "total_withheld": float(sum(withholding.values())),
                "net_amount": float(amount - sum(withholding.values())),
                "jurisdiction": self.jurisdiction,
                "metadata": metadata
            }
        }
        
        await self.blockchain.add_transaction(transaction)
        
        # Store withholding record
        self.withholdings[withholding_id] = transaction["data"]
    
    async def get_tax_summary(self, start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """Get tax summary for a date range."""
        summary = {
            "period": {
                "start": start_date.isoformat(),
                "end": end_date.isoformat()
            },
            "total_income": Decimal("0"),
            "total_withheld": Decimal("0"),
            "by_category": {},
            "quarterly_estimates": {}
        }
        
        # Get all tax withholding transactions from blockchain
        all_transactions = self.blockchain.get_transaction_history("tax_withholding")
        
        for tx in all_transactions:
            tx_date = datetime.fromtimestamp(tx.timestamp / 1_000_000)
            if start_date <= tx_date <= end_date:
                data = tx.data
                
                summary["total_income"] += Decimal(str(data["gross_amount"]))
                summary["total_withheld"] += Decimal(str(data["total_withheld"]))
                
                # Categorize withholdings
                for category, amount in data["withholdings"].items():
                    if category not in summary["by_category"]:
                        summary["by_category"][category] = Decimal("0")
                    summary["by_category"][category] += Decimal(str(amount))
        
        # Calculate quarterly estimates
        quarters = [
            ("Q1", datetime(start_date.year, 1, 1), datetime(start_date.year, 3, 31)),
            ("Q2", datetime(start_date.year, 4, 1), datetime(start_date.year, 6, 30)),
            ("Q3", datetime(start_date.year, 7, 1), datetime(start_date.year, 9, 30)),
            ("Q4", datetime(start_date.year, 10, 1), datetime(start_date.year, 12, 31))
        ]
        
        for quarter_name, q_start, q_end in quarters:
            if q_start <= end_date and q_end >= start_date:
                # Calculate overlap
                overlap_start = max(start_date, q_start)
                overlap_end = min(end_date, q_end)
                
                if overlap_start <= overlap_end:
                    quarter_data = await self.get_tax_summary(overlap_start, overlap_end)
                    summary["quarterly_estimates"][quarter_name] = {
                        "income": float(quarter_data["total_income"]),
                        "withheld": float(quarter_data["total_withheld"])
                    }
        
        # Convert Decimals to float for JSON serialization
        summary["total_income"] = float(summary["total_income"])
        summary["total_withheld"] = float(summary["total_withheld"])
        summary["by_category"] = {k: float(v) for k, v in summary["by_category"].items()}
        
        return summary
    
    def get_withholding_account_balance(self) -> Decimal:
        """Get current balance in tax withholding account."""
        total = Decimal("0")
        for withholding in self.withholdings.values():
            total += Decimal(str(withholding["total_withheld"]))
        return total