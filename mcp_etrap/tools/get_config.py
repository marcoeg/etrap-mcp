from pydantic import BaseModel
from fastmcp import FastMCP

from mcp_etrap.mcp_config import config

class ETRAPConfigOut(BaseModel):
    organization_id: str
    network: str
    contract_id: str
    timeout: int
    cache_ttl: int
    max_retries: int
    aws_region: str
    rpc_endpoint: str | None = None
    
def register_get_config_tool(mcp: FastMCP) -> None:
    @mcp.tool(name="get_config", description="Get the current ETRAP server configuration (organization, network, contract). Use this to understand what organization and network the server is configured for.")
    async def get_config() -> ETRAPConfigOut:
        """
        Get the current ETRAP server configuration.
        
        This tells you what organization and network the MCP server is configured to use.
        The contract_id shows the actual NEAR contract address that will be queried.
        
        Returns:
            ETRAPConfigOut: Current configuration including organization, network, and contract details
        """
        # Derive contract ID from organization and network
        if config.network == "mainnet":
            contract_id = f"{config.organization_id}.near"
        else:
            contract_id = f"{config.organization_id}.{config.network}"
        
        return ETRAPConfigOut(
            organization_id=config.organization_id,
            network=config.network,
            contract_id=contract_id,
            timeout=config.timeout,
            cache_ttl=config.cache_ttl,
            max_retries=config.max_retries,
            aws_region=config.aws_region,
            rpc_endpoint=config.rpc_endpoint
        )