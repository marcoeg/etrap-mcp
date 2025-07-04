# mcp_etrap/app.py
from fastmcp import FastMCP
import argparse
from starlette.responses import PlainTextResponse
from starlette.requests import Request
from dotenv import load_dotenv
import os
from pathlib import Path
import logging

MCP_SERVER_NAME = "mcp-etrap"
logger = logging.getLogger(__name__)

# load configuration variables from .env
env_path = os.path.join(os.getcwd(), ".env")
load_dotenv(env_path)
from mcp_etrap.mcp_config import config

# Initialize ETRAP client
from etrap_sdk import ETRAPClient, S3Config

def create_etrap_client() -> ETRAPClient:
    """Create and configure ETRAP client using environment configuration."""
    # Setup S3 config - always enable S3 to match SDK demo behavior
    s3_config = None
    if config.aws_access_key_id and config.aws_secret_access_key:
        s3_config = S3Config(
            region=config.aws_region,
            access_key_id=config.aws_access_key_id,
            secret_access_key=config.aws_secret_access_key
        )
    else:
        # Use default S3 config with region only (relies on AWS default credential chain)
        # This matches the SDK demo behavior and allows AWS CLI/IAM/environment credentials
        s3_config = S3Config(region=config.aws_region)
    
    return ETRAPClient(
        organization_id=config.organization_id,
        network=config.network,
        rpc_endpoint=config.rpc_endpoint,
        s3_config=s3_config,
        cache_ttl=config.cache_ttl,
        max_retries=config.max_retries,
        timeout=config.timeout
    )

# import server tools registration functions
try:
    from .tools.verify_transaction import register_verify_transaction_tool
    from .tools.verify_batch import register_verify_batch_tool
    from .tools.get_batch import register_get_batch_tool
    from .tools.get_nft import register_get_nft_tool
    from .tools.list_batches import register_list_batches_tool
    from .tools.search_batches import register_search_batches_tool
    from .tools.get_contract_info import register_get_contract_info_tool
    from .tools.get_config import register_get_config_tool
    
except ImportError:
    # Handle direct script execution
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from mcp_etrap.tools.verify_transaction import register_verify_transaction_tool
    from mcp_etrap.tools.verify_batch import register_verify_batch_tool
    from mcp_etrap.tools.get_batch import register_get_batch_tool
    from mcp_etrap.tools.get_nft import register_get_nft_tool
    from mcp_etrap.tools.list_batches import register_list_batches_tool
    from mcp_etrap.tools.search_batches import register_search_batches_tool
    from mcp_etrap.tools.get_contract_info import register_get_contract_info_tool
    from mcp_etrap.tools.get_config import register_get_config_tool

# entry point
def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--transport", default="stdio",
                    choices=["stdio", "sse", "streamable-http"])
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=8000)
    args = ap.parse_args()

    mcp = FastMCP(
        MCP_SERVER_NAME,
        instructions=f"""ETRAP MCP Server for transaction verification and audit operations.
        
        This server provides access to the ETRAP (Enterprise Transaction Recording and Audit Platform) 
        system for verifying database transactions against blockchain records.
        
        Current configuration:
        - Organization: {config.organization_id}
        - Network: {config.network}
        - Contract: {config.organization_id}.{config.network if config.network != 'mainnet' else 'near'}
        
        IMPORTANT WORKFLOW for transaction verification:
        1. Use get_config to see the server's current organization and network configuration
        2. Use verify_transaction to verify individual transactions with optional optimization hints
        3. Use verify_batch to verify multiple transactions efficiently
        4. Use list_batches or search_batches to explore available batch data
        5. Use get_batch to get detailed information about specific batches
        6. Use get_nft to get NFT metadata and blockchain details for batch tokens
        
        Optimization tips:
        - Use hints (batch_id, time_range, database, table) to speed up verification
        - Batch ID hint provides fastest verification (direct lookup)
        - Time range hints dramatically reduce search scope
        - Database and table hints help narrow down searches
        
        All operations are read-only and focus on verification and audit trail access.
        """
    )

    # connect to ETRAP
    etrap_client = create_etrap_client()
    
    # Register tools
    register_get_config_tool(mcp)  # Register this first so Claude knows the config
    register_verify_transaction_tool(mcp, etrap_client)
    register_verify_batch_tool(mcp, etrap_client)
    register_get_batch_tool(mcp, etrap_client)
    register_get_nft_tool(mcp, etrap_client)
    register_list_batches_tool(mcp, etrap_client)
    register_search_batches_tool(mcp, etrap_client)
    register_get_contract_info_tool(mcp, etrap_client)

    # Lightweight health-check for network transports
    if args.transport != "stdio":
        @mcp.custom_route("/healthz", methods=["GET"])
        async def health(_: Request) -> PlainTextResponse:
            return PlainTextResponse("ok")

    run_kwargs = {}
    if args.transport != "stdio":          # needs host/port
        run_kwargs.update(host=args.host, port=args.port)

    mcp.run(transport=args.transport, **run_kwargs)

if __name__ == "__main__":
    main()