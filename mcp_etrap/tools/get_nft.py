from pydantic import BaseModel
from typing import Dict, Any, Optional
from fastmcp import FastMCP

from etrap_sdk import ETRAPClient, NFTInfo

class NFTInfoOut(BaseModel):
    token_id: str
    owner_id: str
    metadata: Dict[str, Any]
    minted_timestamp: str
    batch_id: str
    organization_id: str
    merkle_root: str
    blockchain_details: Dict[str, Any]

def register_get_nft_tool(mcp: FastMCP, etrap_client: ETRAPClient) -> None:
    @mcp.tool(
        name="get_nft",
        description="Get detailed NFT information for a specific batch token. Returns comprehensive NFT metadata, ownership, and blockchain details."
    )
    async def get_nft(nft_token_id: str) -> Optional[NFTInfoOut]:
        """
        Get detailed NFT information for a specific batch token.
        
        This function retrieves comprehensive NFT information including metadata,
        ownership details, and blockchain information for the ETRAP batch NFT.
        
        Args:
            nft_token_id: The NFT token identifier (same as batch_id in ETRAP)
            
        Returns:
            NFTInfoOut: Detailed NFT information, or None if NFT not found
        """
        try:
            result: Optional[NFTInfo] = await etrap_client.get_nft_info(nft_token_id)
            
            if result is None:
                return None
            
            return NFTInfoOut(
                token_id=result.token_id,
                owner_id=result.owner_id,
                metadata=result.metadata,
                minted_timestamp=result.minted_timestamp.isoformat(),
                batch_id=result.batch_id,
                organization_id=result.organization_id,
                merkle_root=result.merkle_root,
                blockchain_details=result.blockchain_details
            )
            
        except Exception as e:
            # Log error for debugging
            print(f"Error in get_nft for {nft_token_id}: {e}")
            return None