#!/usr/bin/env python3
"""Initialize the blockchain for Freshbooks MCP."""

import asyncio
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from blockchain.core import BlockchainCore
from blockchain.crypto import CryptoHelper


async def main():
    """Initialize blockchain."""
    load_dotenv()
    
    print("Initializing Freshbooks Blockchain...")
    
    # Create blockchain instance
    blockchain = BlockchainCore(
        data_dir=os.getenv("BLOCKCHAIN_DATA_DIR", "./blockchain_data"),
        difficulty=int(os.getenv("BLOCKCHAIN_DIFFICULTY", "4"))
    )
    
    # Initialize (creates genesis block)
    await blockchain.initialize()
    
    print(f"✓ Blockchain initialized with {len(blockchain.chain)} blocks")
    print(f"✓ Genesis block hash: {blockchain.chain[0].hash}")
    
    # Generate keypair for signing
    crypto = CryptoHelper()
    private_key, public_key = crypto.generate_keypair()
    
    # Save keys
    keys_dir = Path("./keys")
    keys_dir.mkdir(exist_ok=True)
    
    with open(keys_dir / "private_key.pem", "w") as f:
        f.write(private_key)
    
    with open(keys_dir / "public_key.pem", "w") as f:
        f.write(public_key)
    
    os.chmod(keys_dir / "private_key.pem", 0o600)
    
    print("✓ Cryptographic keys generated")
    print("\nBlockchain is ready for use!")
    print("\nNext steps:")
    print("1. Configure your .env file with Freshbooks credentials")
    print("2. Run 'docker-compose up -d' to start the services")
    print("3. Add the MCP server to your Claude Desktop config")


if __name__ == "__main__":
    asyncio.run(main())