from pydantic import BaseModel
from typing import Dict, Any, Optional, List
from fastmcp import FastMCP

from etrap_sdk import ETRAPClient, BatchInfo

class BatchInfoOut(BaseModel):
    batch_id: str
    timestamp: str
    database_name: str
    table_names: List[str]
    transaction_count: int
    merkle_root: str
    s3_location: Optional[Dict[str, str]] = None
    size_bytes: Optional[int] = None
    operation_counts: Optional[Dict[str, int]] = None
    contract_address: str
    nft_token_id: Optional[str] = None

def register_get_batch_tool(mcp: FastMCP, etrap_client: ETRAPClient) -> None:
    @mcp.tool(
        name="get_batch",
        description="Get detailed information about a specific batch by batch ID. Returns comprehensive batch metadata including Merkle root and storage details."
    )
    async def get_batch(batch_id: str) -> Optional[BatchInfoOut]:
        """
        Get detailed information about a specific batch.
        
        This function retrieves comprehensive information about a batch including
        its metadata, transaction count, Merkle root, and storage details.
        
        Args:
            batch_id: The batch identifier (e.g., "BATCH-2025-06-14-abc123")
            
        Returns:
            BatchInfoOut: Detailed batch information, or None if batch not found
        """
        try:
            result: Optional[BatchInfo] = await etrap_client.get_batch(batch_id)
            
            if result is None:
                return None
            
            # Convert S3 location if available
            s3_location = None
            if result.s3_location:
                s3_location = {
                    "bucket": result.s3_location.bucket,
                    "key": result.s3_location.key,
                    "region": result.s3_location.region
                }
            
            return BatchInfoOut(
                batch_id=result.batch_id,
                timestamp=result.timestamp.isoformat(),
                database_name=result.database_name,
                table_names=result.table_names,
                transaction_count=result.transaction_count,
                merkle_root=result.merkle_root,
                s3_location=s3_location,
                size_bytes=result.size_bytes,
                operation_counts=result.operation_counts,
                contract_address=result.contract_address,
                nft_token_id=result.nft_token_id
            )
            
        except Exception as e:
            # Log error but return None to indicate batch not found
            # In a real implementation, you might want to distinguish between
            # "not found" and "error occurred"
            return None