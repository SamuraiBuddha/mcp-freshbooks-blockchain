"""Core blockchain implementation for financial transactions."""

import json
import time
from datetime import datetime
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
import hashlib
from pathlib import Path
import asyncio
import aiofiles

from .crypto import CryptoHelper


@dataclass
class Transaction:
    """Represents a financial transaction on the blockchain."""
    
    transaction_id: str
    timestamp: int  # Microsecond precision
    transaction_type: str  # invoice, payment, expense, etc.
    data: Dict[str, Any]
    sender_signature: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert transaction to dictionary."""
        return {
            "transaction_id": self.transaction_id,
            "timestamp": self.timestamp,
            "transaction_type": self.transaction_type,
            "data": self.data,
            "sender_signature": self.sender_signature,
            "metadata": self.metadata
        }
    
    def calculate_hash(self) -> str:
        """Calculate transaction hash."""
        tx_string = json.dumps(self.to_dict(), sort_keys=True)
        return hashlib.sha256(tx_string.encode()).hexdigest()


@dataclass
class Block:
    """Represents a block in the blockchain."""
    
    index: int
    timestamp: int
    transactions: List[Transaction]
    previous_hash: str
    nonce: int = 0
    hash: Optional[str] = None
    
    def calculate_hash(self) -> str:
        """Calculate block hash."""
        block_data = {
            "index": self.index,
            "timestamp": self.timestamp,
            "transactions": [tx.to_dict() for tx in self.transactions],
            "previous_hash": self.previous_hash,
            "nonce": self.nonce
        }
        block_string = json.dumps(block_data, sort_keys=True)
        return hashlib.sha256(block_string.encode()).hexdigest()
    
    def mine_block(self, difficulty: int = 4) -> None:
        """Mine the block with proof of work."""
        target = "0" * difficulty
        while not self.calculate_hash().startswith(target):
            self.nonce += 1
        self.hash = self.calculate_hash()


class BlockchainCore:
    """Core blockchain implementation for Freshbooks transactions."""
    
    def __init__(self, data_dir: str = "./blockchain_data", difficulty: int = 4):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True)
        self.difficulty = difficulty
        self.chain: List[Block] = []
        self.pending_transactions: List[Transaction] = []
        self.crypto = CryptoHelper()
        
    async def initialize(self) -> None:
        """Initialize blockchain, load existing chain or create genesis block."""
        chain_file = self.data_dir / "chain.json"
        
        if chain_file.exists():
            await self.load_chain()
        else:
            self.create_genesis_block()
            await self.save_chain()
    
    def create_genesis_block(self) -> Block:
        """Create the genesis block."""
        genesis_tx = Transaction(
            transaction_id="genesis",
            timestamp=int(time.time() * 1_000_000),
            transaction_type="genesis",
            data={"message": "Freshbooks Blockchain Genesis - Tony Stark would be proud"}
        )
        
        genesis_block = Block(
            index=0,
            timestamp=genesis_tx.timestamp,
            transactions=[genesis_tx],
            previous_hash="0"
        )
        genesis_block.mine_block(self.difficulty)
        self.chain.append(genesis_block)
        return genesis_block
    
    def get_latest_block(self) -> Block:
        """Get the latest block in the chain."""
        return self.chain[-1]
    
    async def add_transaction(self, transaction: Transaction) -> str:
        """Add a transaction to pending transactions."""
        # Validate transaction
        if not self.validate_transaction(transaction):
            raise ValueError("Invalid transaction")
        
        self.pending_transactions.append(transaction)
        
        # Auto-mine if we have enough transactions
        if len(self.pending_transactions) >= 10:
            await self.mine_pending_transactions()
        
        return transaction.transaction_id
    
    def validate_transaction(self, transaction: Transaction) -> bool:
        """Validate a transaction."""
        # Basic validation
        if not transaction.transaction_id:
            return False
        
        if not transaction.timestamp:
            return False
        
        if transaction.transaction_type not in [
            "invoice", "payment", "expense", "credit", 
            "refund", "adjustment", "time_entry", "genesis"
        ]:
            return False
        
        # Signature validation if present
        if transaction.sender_signature:
            # Implement signature verification
            pass
        
        return True
    
    async def mine_pending_transactions(self, miner_address: str = "system") -> Optional[Block]:
        """Mine pending transactions into a new block."""
        if not self.pending_transactions:
            return None
        
        # Add mining reward transaction
        reward_tx = Transaction(
            transaction_id=f"reward_{int(time.time() * 1_000_000)}",
            timestamp=int(time.time() * 1_000_000),
            transaction_type="mining_reward",
            data={"miner": miner_address, "amount": 0.001}  # Small reward for maintaining ledger
        )
        
        transactions = self.pending_transactions + [reward_tx]
        
        new_block = Block(
            index=len(self.chain),
            timestamp=int(time.time() * 1_000_000),
            transactions=transactions,
            previous_hash=self.get_latest_block().hash
        )
        
        new_block.mine_block(self.difficulty)
        self.chain.append(new_block)
        self.pending_transactions = []
        
        await self.save_chain()
        return new_block
    
    def validate_chain(self) -> bool:
        """Validate the entire blockchain."""
        for i in range(1, len(self.chain)):
            current_block = self.chain[i]
            previous_block = self.chain[i - 1]
            
            # Check if current block's hash is valid
            if current_block.hash != current_block.calculate_hash():
                return False
            
            # Check if previous hash matches
            if current_block.previous_hash != previous_block.hash:
                return False
            
            # Check if block is properly mined
            if not current_block.hash.startswith("0" * self.difficulty):
                return False
        
        return True
    
    async def save_chain(self) -> None:
        """Save blockchain to disk."""
        chain_data = {
            "chain": [
                {
                    "index": block.index,
                    "timestamp": block.timestamp,
                    "transactions": [tx.to_dict() for tx in block.transactions],
                    "previous_hash": block.previous_hash,
                    "nonce": block.nonce,
                    "hash": block.hash
                }
                for block in self.chain
            ],
            "difficulty": self.difficulty
        }
        
        chain_file = self.data_dir / "chain.json"
        async with aiofiles.open(chain_file, "w") as f:
            await f.write(json.dumps(chain_data, indent=2))
    
    async def load_chain(self) -> None:
        """Load blockchain from disk."""
        chain_file = self.data_dir / "chain.json"
        
        async with aiofiles.open(chain_file, "r") as f:
            chain_data = json.loads(await f.read())
        
        self.difficulty = chain_data.get("difficulty", 4)
        self.chain = []
        
        for block_data in chain_data["chain"]:
            transactions = [
                Transaction(**tx_data)
                for tx_data in block_data["transactions"]
            ]
            
            block = Block(
                index=block_data["index"],
                timestamp=block_data["timestamp"],
                transactions=transactions,
                previous_hash=block_data["previous_hash"],
                nonce=block_data["nonce"],
                hash=block_data["hash"]
            )
            
            self.chain.append(block)
    
    def get_transaction_history(self, filter_type: Optional[str] = None) -> List[Transaction]:
        """Get all transactions, optionally filtered by type."""
        all_transactions = []
        
        for block in self.chain:
            for tx in block.transactions:
                if filter_type is None or tx.transaction_type == filter_type:
                    all_transactions.append(tx)
        
        return all_transactions
    
    def get_balance_sheet(self) -> Dict[str, float]:
        """Calculate current balance sheet from blockchain."""
        balance_sheet = {
            "total_invoiced": 0.0,
            "total_paid": 0.0,
            "total_expenses": 0.0,
            "outstanding": 0.0,
            "net_income": 0.0
        }
        
        for tx in self.get_transaction_history():
            if tx.transaction_type == "invoice":
                amount = tx.data.get("amount", 0)
                balance_sheet["total_invoiced"] += amount
                balance_sheet["outstanding"] += amount
            
            elif tx.transaction_type == "payment":
                amount = tx.data.get("amount", 0)
                balance_sheet["total_paid"] += amount
                balance_sheet["outstanding"] -= amount
            
            elif tx.transaction_type == "expense":
                amount = tx.data.get("amount", 0)
                balance_sheet["total_expenses"] += amount
        
        balance_sheet["net_income"] = (
            balance_sheet["total_paid"] - balance_sheet["total_expenses"]
        )
        
        return balance_sheet