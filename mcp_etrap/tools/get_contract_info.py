from pydantic import BaseModel
from typing import Dict, Any, Optional, List
from fastmcp import FastMCP

from etrap_sdk import ETRAPClient, ContractInfo, ContractStats

class ContractInfoOut(BaseModel):
    contract_address: str
    organization_id: str
    network: str
    total_batches: int
    total_transactions: int
    oldest_batch_timestamp: Optional[str] = None
    newest_batch_timestamp: Optional[str] = None
    databases: List[str]
    contract_version: Optional[str] = None
    treasury_address: Optional[str] = None

def register_get_contract_info_tool(mcp: FastMCP, etrap_client: ETRAPClient) -> None:
    @mcp.tool(
        name="get_contract_info",
        description="Get comprehensive information about the ETRAP smart contract including statistics, databases, and configuration."
    )
    async def get_contract_info() -> ContractInfoOut:
        """
        Get comprehensive information about the ETRAP smart contract.
        
        This function retrieves overall statistics and configuration information
        about the organization's ETRAP smart contract, including total batches,
        databases being tracked, and contract settings.
        
        Returns:
            ContractInfoOut: Complete contract information including stats and configuration
        """
        try:
            # Get contract info and stats
            # Note: These methods may not all exist in the current SDK
            # This is a demonstration of what the interface would look like
            
            contract_info: Optional[ContractInfo] = await etrap_client.get_contract_info()
            contract_stats: Optional[ContractStats] = await etrap_client.get_contract_stats()
            
            # Build response from available data
            if contract_info:
                return ContractInfoOut(
                    contract_address=contract_info.contract_id,
                    organization_id=etrap_client.organization_id,
                    network=etrap_client.network,
                    total_batches=contract_info.total_batches,
                    total_transactions=contract_info.total_transactions,
                    oldest_batch_timestamp=contract_info.earliest_batch.isoformat() if contract_info.earliest_batch else None,
                    newest_batch_timestamp=contract_info.latest_batch.isoformat() if contract_info.latest_batch else None,
                    databases=contract_info.supported_databases,
                    contract_version=None,
                    treasury_address=None
                )
            else:
                # Fallback: build basic info from client configuration
                # Derive contract address
                org_id = etrap_client.organization_id
                network = etrap_client.network
                
                if network == "mainnet":
                    contract_address = f"{org_id}.near"
                else:
                    contract_address = f"{org_id}.{network}"
                
                return ContractInfoOut(
                    contract_address=contract_address,
                    organization_id=org_id,
                    network=network,
                    total_batches=0,
                    total_transactions=0,
                    databases=[],
                    contract_version=None,
                    treasury_address=None
                )
                
        except Exception as e:
            # Return basic info even if detailed stats fail
            org_id = etrap_client.organization_id
            network = etrap_client.network
            
            if network == "mainnet":
                contract_address = f"{org_id}.near"
            else:
                contract_address = f"{org_id}.{network}"
            
            return ContractInfoOut(
                contract_address=contract_address,
                organization_id=org_id,
                network=network,
                total_batches=0,
                total_transactions=0,
                databases=[],
                contract_version=f"Error: {str(e)}",
                treasury_address=None
            )