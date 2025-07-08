# ETRAP MCP Server

A Model Context Protocol (MCP) server for the ETRAP (Enterprise Transaction Recording and Audit Platform) system. This server provides tools for verifying database transactions against blockchain records stored on NEAR Protocol.

## Features

- **Transaction Verification**: Verify individual transactions against blockchain records
- **Batch Verification**: Efficiently verify multiple transactions in parallel
- **Batch Management**: List, search, and inspect batches of transactions
- **NFT Asset Information**: Access blockchain NFT metadata and ownership details
- **Contract Information**: Get details about ETRAP smart contracts
- **Multi-Transport Support**: stdio, SSE, and streamable-HTTP transports

## Installation

This project uses [uv](https://github.com/astral-sh/uv) for dependency management and virtual environment setup.

### Option 1: Using UV Virtual Environment (Recommended)

```bash
# Create and activate virtual environment
uv venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install the project with dependencies
uv pip install -e .

# Run the server
python -m mcp_etrap.app
```

### Option 2: Using UV Run (Alternative)

```bash
# Install dependencies
uv sync

# Run the server directly with uv
uv run python -m mcp_etrap.app
```

## Configuration

Configure the server using environment variables:

**Required:**
- `ETRAP_ORGANIZATION`: Organization identifier (e.g., 'acme')

**Optional:**
- `ETRAP_NETWORK`: NEAR network (testnet/mainnet, default: testnet)
- `ETRAP_RPC_ENDPOINT`: Custom NEAR RPC endpoint
- `ETRAP_TIMEOUT`: Request timeout in seconds (default: 30)
- `ETRAP_CACHE_TTL`: Cache TTL in seconds (default: 300)
- `ETRAP_MAX_RETRIES`: Max retry attempts (default: 3)

**AWS S3:**
- `AWS_ACCESS_KEY_ID`: S3 access key
- `AWS_SECRET_ACCESS_KEY`: S3 secret key
- `AWS_DEFAULT_REGION`: S3 region (default: us-west-2)

## Usage

### Basic Usage

**With Virtual Environment:**
```bash
# Start with stdio transport (default for MCP)
ETRAP_ORGANIZATION=myorg python -m mcp_etrap.app

# Start with HTTP transport  
ETRAP_ORGANIZATION=myorg python -m mcp_etrap.app --transport sse --port 8000
```

**With UV Run:**
```bash
# Start with stdio transport (default for MCP)
ETRAP_ORGANIZATION=myorg uv run python -m mcp_etrap.app

# Start with HTTP transport  
ETRAP_ORGANIZATION=myorg uv run python -m mcp_etrap.app --transport sse --port 8000
```

### Available Tools

- `get_config`: Get current server configuration
- `verify_transaction`: Verify a single transaction with optional hints
- `verify_batch`: Verify multiple transactions efficiently
- `get_batch`: Get detailed batch information by ID
- `get_nft`: Get NFT metadata and blockchain details for batch tokens
- `list_batches`: List batches with filtering and pagination
- `search_batches`: Advanced batch search with criteria
- `get_contract_info`: Get contract statistics and information

### Optimization Hints

All verification tools support optional hints as JSON objects to improve performance:

#### Time Range Hints
```json
{
  "time_start": "2025-07-01T09:54:00",
  "time_end": "2025-07-01T09:56:00"
}
```

#### Batch ID Hint (Fastest)
```json
{
  "batch_id": "BATCH-2025-07-01-abc123"
}
```

#### Database/Table Hints
```json
{
  "database_name": "production",
  "table_name": "financial_transactions"
}
```

#### Operation Disambiguation
```json
{
  "expected_operation": "INSERT"
}
```

#### Combined Hints
```json
{
  "time_start": "2025-07-01T09:54:00",
  "time_end": "2025-07-01T09:56:00",
  "expected_operation": "INSERT",
  "database_name": "production"
}
```

**Important**: Time ranges refer to **blockchain batch creation time**, not database transaction time. When you provide a time range, you're searching for batches that were minted on the blockchain during that period. This is different from when the original database transactions occurred. Blockchain timestamps are always in UTC.

### NFT Tools

#### get_nft - NFT Metadata and Blockchain Asset Information

The `get_nft` tool retrieves comprehensive NFT information for ETRAP batch tokens. In ETRAP, each batch creates a unique NFT on the NEAR blockchain that represents ownership of the audit record.

**Input**: NFT token ID (same as batch ID)
```json
{
  "nft_token_id": "BATCH-2025-07-01-c9de5968"
}
```

**Output**: Complete NFT metadata and blockchain details
```json
{
  "token_id": "BATCH-2025-07-01-c9de5968",
  "owner_id": "lunaris.testnet",
  "metadata": {
    "title": "ETRAP Batch BATCH-2025-07-01-c9de5968",
    "description": "Integrity certificate for 4 transactions from table financial_transactions",
    "reference": "https://s3.amazonaws.com/etrap-lunaris/BATCH-2025-07-01-c9de5968/batch-data.json",
    "issued_at": "1751388910475",
    "copies": 1
  },
  "minted_timestamp": "2025-07-01T09:55:10.475000",
  "batch_id": "BATCH-2025-07-01-c9de5968",
  "organization_id": "lunaris",
  "merkle_root": "b1e52265e4fd5afaf673454fe7351cbc516bea056c08f99e3d0876217b0aacab",
  "blockchain_details": {
    "contract_id": "lunaris.testnet",
    "network": "testnet",
    "token_standard": "NEP-171",
    "approved_account_ids": {}
  }
}
```

**Key Features**:
- **NEP-171 Compliant**: Full NEAR NFT standard compliance
- **Ownership Information**: Current owner and approved accounts
- **Rich Metadata**: Title, description, and S3 reference
- **Blockchain Asset Data**: Contract details and minting information
- **Cryptographic Integrity**: Merkle root for verification

**Use Cases**:
- **Asset Ownership**: Determine who owns the audit record NFT
- **Metadata Access**: Get human-readable information about the batch
- **Blockchain Integration**: Access NFT data for marketplace or transfer operations
- **Compliance Documentation**: Generate certificates of audit record ownership

#### Tool Comparison: get_batch vs get_nft

**`get_batch`** - Audit Record Data:
- Transaction details and operation counts
- S3 storage information and batch statistics  
- Database and table information
- **Focus**: Audit trail and verification data

**`get_nft`** - Blockchain Asset Data:
- NFT ownership and metadata
- Blockchain asset information
- Minting timestamps and contract details
- **Focus**: Digital asset and ownership information

Both tools complement each other to provide complete visibility into ETRAP's tamper-proof audit system.

### Example

**With Virtual Environment:**
```bash
# Set environment
export ETRAP_ORGANIZATION=lunaris
export ETRAP_NETWORK=testnet

# Activate environment and start the server
source .venv/bin/activate
python -m mcp_etrap.app
```

**With UV Run:**
```bash
# Set environment
export ETRAP_ORGANIZATION=lunaris
export ETRAP_NETWORK=testnet

# Start the server
uv run python -m mcp_etrap.app
```

The server will connect to the `lunaris.testnet` NEAR contract and provide transaction verification capabilities.

## Architecture

- **FastMCP**: Modern MCP server framework with multi-transport support
- **ETRAP SDK**: Python SDK for NEAR blockchain interaction and S3 data access
- **Pydantic**: Type-safe data models and validation
- **UV**: Fast dependency resolution with conflict override capabilities

## Development

### Rebuilding After SDK Changes

**IMPORTANT**: When the ETRAP SDK is updated, you must rebuild the MCP server to incorporate the changes:

```bash
# Method 1: Force reinstall the SDK package
uv sync --reinstall-package etrap-sdk

# Method 2: Complete reinstall (if needed)
uv pip uninstall etrap-sdk
uv sync

# Restart the server after rebuilding
ETRAP_ORGANIZATION=myorg uv run python -m mcp_etrap.app
```

The MCP server uses a direct file reference to the local ETRAP SDK (`etrap-sdk @ file:///path/to/etrap-sdk`), so rebuilding ensures the latest SDK changes are incorporated.

### Development Workflow

#### With Virtual Environment

```bash
# Create and activate environment
uv venv
source .venv/bin/activate

# Install project with dev dependencies
uv pip install -e ".[dev]"

# Run tests
pytest

# Lint code
ruff check .
```

#### With UV Run

```bash
# Install development dependencies
uv sync --group dev

# Run tests
uv run pytest

# Lint code
uv run ruff check .
```

### Testing

#### MCP Server Testing
Test the complete MCP server functionality:

**Using stdio transport (recommended):**
```bash
# Run comprehensive MCP server test
uv run python test_mcp_stdio.py
```

This test validates:
- MCP server initialization and tool listing
- Individual transaction verification with time range hints
- Batch verification with optimization hints
- End-to-end MCP → SDK → Blockchain flow

**Test Coverage:**
- ✅ Time range hints (critical for performance)
- ✅ Operation disambiguation (INSERT/UPDATE/DELETE)
- ✅ Batch ID hints (fastest verification method)
- ✅ Combined hint scenarios

## Dependencies

The server resolves a complex dependency conflict between FastMCP and py-near by using UV's override capabilities:

- FastMCP 2.9.x requires `httpx>=0.28.1`
- py-near 1.1.52 requires `httpx==0.26.0`
- UV override forces `httpx>=0.28.1` for compatibility

## Build Configuration

The project uses Hatchling as the build backend with specific configurations for:

- **Direct References**: `tool.hatch.metadata.allow-direct-references = true` enables local ETRAP SDK dependency
- **Package Discovery**: `tool.hatch.build.targets.wheel.packages = ["mcp_etrap"]` specifies the package location
- **Dependency Override**: UV's override feature ensures httpx compatibility

This approach ensures we get the latest MCP features while maintaining ETRAP SDK functionality.



## 🪪 License

MIT. See `./LICENSE`


## 📄 Copyright

Copyright (c) 2025 Graziano Labs Corp. All rights reserved.


## 📧 Contact

For questions or support, please open an issue in the GitHub repository.

---