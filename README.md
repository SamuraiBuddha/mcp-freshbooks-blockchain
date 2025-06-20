# MCP Freshbooks Blockchain

> 🚀 The world's first blockchain-powered accounting MCP. Every invoice, payment, and expense creates an immutable blockchain record.

## Overview

This MCP integrates Freshbooks accounting software with blockchain technology to create an unprecedented level of financial transparency and auditability. Built following the patterns from mcp-memory-blockchain and inspired by Tony Stark-level innovation.

## Features

### 🔐 Blockchain Audit Trail
- Every financial transaction creates an immutable blockchain record
- Cryptographic signatures on all operations
- Distributed validation across MAGI nodes (when deployed)
- Smart contracts for accounting rules and compliance

### 💰 Freshbooks Integration
- **Invoicing**: Create, send, track, and manage invoices
- **Payments**: Record payments with blockchain receipts
- **Expenses**: Track expenses with receipt attachments
- **Time Tracking**: Log billable hours with blockchain timestamps
- **Clients**: Manage client relationships and balances
- **Reports**: Generate blockchain-verified financial reports

### 🤖 AI-Powered Features
- Natural language invoice creation
- Automatic expense categorization
- Smart payment reminders
- Tax optimization suggestions
- Anomaly detection for fraud prevention

### 🔍 Advanced Capabilities
- Multi-currency support with real-time conversion tracking
- Recurring invoice automation via smart contracts
- Integration with mcp-time-precision for microsecond accuracy
- Export blockchain proofs for audits
- Compliance reporting (SOX, GDPR, etc.)

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     MCP Freshbooks Blockchain                │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌─────────────┐    ┌──────────────┐    ┌───────────────┐  │
│  │   MCP       │    │  Freshbooks  │    │  Blockchain   │  │
│  │  Server     │◄──►│     API      │◄──►│    Core       │  │
│  └─────────────┘    └──────────────┘    └───────────────┘  │
│         ▲                                         │          │
│         │                                         ▼          │
│  ┌─────────────┐                        ┌───────────────┐  │
│  │   Claude    │                        │ Smart         │  │
│  │  Desktop    │                        │ Contracts     │  │
│  └─────────────┘                        └───────────────┘  │
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

## Quick Start

### Prerequisites
- Python 3.11+
- Node.js 18+ (for blockchain components)
- Freshbooks account with API credentials
- Docker (optional, for deployment)

### Installation

1. Clone the repository:
```bash
git clone https://github.com/SamuraiBuddha/mcp-freshbooks-blockchain.git
cd mcp-freshbooks-blockchain
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Configure environment:
```bash
cp .env.example .env
# Edit .env with your Freshbooks credentials
```

4. Initialize blockchain:
```bash
python scripts/init_blockchain.py
```

5. Add to Claude Desktop config:
```json
{
  "mcpServers": {
    "freshbooks-blockchain": {
      "command": "python",
      "args": ["-m", "mcp_freshbooks_blockchain.server"],
      "env": {
        "FRESHBOOKS_CLIENT_ID": "your-client-id",
        "FRESHBOOKS_CLIENT_SECRET": "your-client-secret",
        "FRESHBOOKS_REDIRECT_URI": "http://localhost:8080/callback",
        "BLOCKCHAIN_NODE_URL": "http://localhost:8545"
      }
    }
  }
}
```

## Usage Examples

### Creating an Invoice with Blockchain Record
```
"Create an invoice for Jordan Jr's tennis lessons, 10 sessions at $50 each, due in 30 days"
```

### Recording an Expense
```
"Record expense: $127.43 for office supplies at Staples, attach receipt"
```

### Generating Blockchain-Verified Reports
```
"Generate Q2 profit and loss report with blockchain verification"
```

## Smart Contracts

### Recurring Invoice Contract
Automatically generates and sends invoices based on predefined schedules with blockchain proof of delivery.

### Tax Withholding Contract
Automatically calculates and sets aside tax obligations based on income and jurisdiction.

### Audit Trail Contract
Enforces immutability and provides cryptographic proof of all financial records.

## Security

- OAuth2 authentication with Freshbooks
- All blockchain transactions signed with private keys
- Encrypted storage of sensitive data
- Role-based access control
- Audit logging of all operations

## Integration Points

- **mcp-time-precision**: Microsecond timestamps for all transactions
- **mcp-memory-blockchain**: Shared blockchain infrastructure
- **My Girl Friday**: Invoice delivery via email
- **RevitBlockchain**: Project-based billing integration

## Development

### Project Structure
```
mcp-freshbooks-blockchain/
├── blockchain/
│   ├── core.py           # Blockchain implementation
│   ├── contracts/        # Smart contracts
│   └── validators/       # Transaction validators
├── freshbooks/
│   ├── client.py         # Freshbooks API client
│   ├── auth.py           # OAuth2 implementation
│   └── models.py         # Data models
├── mcp_freshbooks_blockchain/
│   ├── __init__.py
│   ├── server.py         # MCP server
│   └── tools.py          # MCP tool implementations
├── scripts/
│   ├── init_blockchain.py
│   └── migrate_data.py
├── docker-compose.yml
├── requirements.txt
└── .env.example
```

## Future Enhancements

- Mobile app for receipt scanning
- Integration with banking APIs
- AI-powered financial advisor
- Multi-business support
- Cryptocurrency payment processing
- International tax compliance

## Contributing

This is a Jordan & Claude collaboration. Feel free to fork and extend!

## License

MIT - Because financial transparency should be open source.

---

*Built with ❤️ by Jordan & Claude, because Tony Stark would absolutely blockchain his accounting.*
