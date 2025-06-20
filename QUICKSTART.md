# Quick Start Guide

## 🚀 Getting Started with Freshbooks Blockchain MCP

This guide will have you up and running with blockchain-powered accounting in under 10 minutes!

## Prerequisites

1. **Freshbooks Account**: You need a Freshbooks account with API access
2. **Docker**: Install Docker Desktop from [docker.com](https://docker.com)
3. **Python 3.11+**: For initial setup scripts
4. **Claude Desktop**: With MCP support enabled

## Step 1: Clone and Setup

```bash
# Clone the repository
git clone https://github.com/SamuraiBuddha/mcp-freshbooks-blockchain.git
cd mcp-freshbooks-blockchain

# Install Python dependencies for setup
pip install -r requirements.txt

# Initialize the blockchain
python scripts/init_blockchain.py
```

## Step 2: Configure Freshbooks API

1. Go to [Freshbooks Developers](https://www.freshbooks.com/developers)
2. Create a new app to get your credentials
3. Copy `.env.example` to `.env`:

```bash
cp .env.example .env
```

4. Edit `.env` with your credentials:

```env
FRESHBOOKS_CLIENT_ID=your-client-id-here
FRESHBOOKS_CLIENT_SECRET=your-client-secret-here
FRESHBOOKS_ACCOUNT_ID=your-account-id
INSTANCE_ID=Melchior-001
```

## Step 3: First-Time Authentication

```bash
# Run the OAuth flow
docker-compose --profile auth up oauth-callback

# In another terminal, start the MCP server manually
python -m mcp_freshbooks_blockchain.server
```

Follow the authentication prompts in your browser. This only needs to be done once.

## Step 4: Add to Claude Desktop

Edit your Claude Desktop config (`%APPDATA%\Claude\claude_desktop_config.json` on Windows):

```json
{
  "mcpServers": {
    "freshbooks-blockchain": {
      "command": "docker",
      "args": ["compose", "run", "--rm", "mcp-server"],
      "cwd": "C:\\path\\to\\mcp-freshbooks-blockchain",
      "env": {
        "COMPOSE_PROJECT_NAME": "freshbooks"
      }
    }
  }
}
```

## Step 5: Start Using!

Restart Claude Desktop and try these commands:

### Basic Commands

```
"List my outstanding invoices"
"Create an invoice for Jordan Jr's tennis lessons, 10 sessions at $50 each"
"Record payment of $500 for invoice #1234"
"Record expense: $127.43 for office supplies at Staples"
"Show me my blockchain financial summary"
```

### Advanced Features

```
"Create recurring monthly invoice for $1000 for client ABC Corp"
"Get my Q2 tax summary"
"Verify transaction tx_12345..."
"Process all due recurring invoices"
```

## Optional: Migrate Existing Data

To import your existing Freshbooks data to the blockchain:

```bash
python scripts/migrate_data.py
```

This will create blockchain records for all your historical invoices, expenses, and clients.

## Docker Commands

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f mcp-server

# Stop services
docker-compose down

# Backup blockchain
python scripts/backup_blockchain.py backup

# Start blockchain explorer (optional)
docker-compose --profile explorer up -d explorer
```

## Troubleshooting

### Authentication Issues
- Token is saved in `~/.freshbooks_token.json`
- Delete this file to re-authenticate
- Check that redirect URI matches your app settings

### Blockchain Issues
- Blockchain data is in `./blockchain_data/`
- Check logs: `docker-compose logs blockchain`
- Verify chain: `python -c "from blockchain.core import BlockchainCore; bc = BlockchainCore(); print(bc.validate_chain())"`

### MCP Connection Issues
- Ensure Docker is running
- Check Claude Desktop logs
- Verify paths in config are absolute

## Architecture Overview

```
Your Computer (Melchior)
├── Claude Desktop
│   └── MCP Client → Freshbooks Blockchain MCP
│
├── Docker Containers
│   ├── Blockchain Node (Port 8545)
│   ├── MCP Server
│   └── OAuth Callback (Port 8080)
│
└── Local Storage
    ├── blockchain_data/ (Immutable ledger)
    ├── tokens/ (Auth tokens)
    └── logs/ (Application logs)
```

## What Makes This Special?

1. **Immutable Audit Trail**: Every transaction is recorded on a blockchain
2. **Smart Contracts**: Automated recurring invoices and tax calculations
3. **Cryptographic Security**: All transactions are signed and verified
4. **Compliance Ready**: SOX, GDPR, and other compliance reports
5. **AI Integration**: Natural language invoice creation and expense categorization

## Next Steps

1. **Deploy to NAS**: Use the same Docker setup on your Terramaster
2. **Multi-Node Setup**: Run Balthasar and Caspar as validator nodes
3. **Integrate with Other MCPs**: 
   - My Girl Friday for invoice delivery
   - RevitBlockchain for project billing
   - Time Precision MCP for microsecond accuracy

## Support

- GitHub Issues: [Create an issue](https://github.com/SamuraiBuddha/mcp-freshbooks-blockchain/issues)
- Documentation: Check the `/docs` folder
- Jordan & Claude: We're here to help!

---

*Welcome to the future of accounting - where every penny is blockchain verified! 🚀*
