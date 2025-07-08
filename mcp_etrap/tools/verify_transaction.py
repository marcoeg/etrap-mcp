from pydantic import BaseModel, Field
from typing import Dict, Any, Optional, List, Literal
from fastmcp import FastMCP

from etrap_sdk import ETRAPClient, VerificationHints, TimeRange
from datetime import datetime

class VerificationHintsInput(BaseModel):
    batch_id: Optional[str] = Field(None, description="Specific batch ID for direct lookup (fastest method)")
    database_name: Optional[str] = Field(None, description="Database name to limit search scope")
    table_name: Optional[str] = Field(None, description="Table name to limit search scope")
    time_start: Optional[str] = Field(None, description="Start time for time range search (ISO format, e.g. '2025-06-14T00:00:00')")
    time_end: Optional[str] = Field(None, description="End time for time range search (ISO format, e.g. '2025-06-14T23:59:59')")
    expected_operation: Optional[Literal["INSERT", "UPDATE", "DELETE"]] = Field(None, description="Expected operation type to disambiguate hash collisions between different operations on the same data")

class MerkleProofOut(BaseModel):
    leaf_hash: str
    proof_path: List[str]
    sibling_positions: List[str] 
    merkle_root: str
    is_valid: bool

class SearchInfoOut(BaseModel):
    total_batches: int
    batch_position: int
    direct_lookup: Optional[bool] = None

class BatchInfoOut(BaseModel):
    database: str
    tables: List[str]
    transaction_count: int
    timestamp: datetime

class VerificationResultOut(BaseModel):
    verified: bool
    transaction_hash: str
    batch_id: Optional[str] = None
    blockchain_timestamp: Optional[datetime] = None
    error: Optional[str] = None
    search_info: Optional[SearchInfoOut] = None
    verification_method: str = "local"
    merkle_proof: Optional[MerkleProofOut] = None
    batch_info: Optional[BatchInfoOut] = None
    operation_type: Optional[str] = None
    position: Optional[int] = None
    processing_time_ms: int = 0


def register_verify_transaction_tool(mcp: FastMCP, etrap_client: ETRAPClient) -> None:
    @mcp.tool(
        name="verify_transaction",
        description="Verify a single transaction against blockchain records. Use hints to optimize performance - batch_id is fastest, time_range narrows search significantly. Use expected_operation to disambiguate between INSERT/UPDATE/DELETE operations with identical data."
    )
    async def verify_transaction(
        transaction_data: Dict[str, Any],
        hints: Optional[VerificationHintsInput] = None,
        timeout: Optional[int] = None,
        use_contract_verification: bool = False
    ) -> VerificationResultOut:
        """
        Verify a single transaction against ETRAP blockchain records.
        
        This function checks if the given transaction data has been properly recorded
        and verified in the blockchain through the ETRAP system.
        
        Args:
            transaction_data: Transaction data as a dictionary (e.g., {"id": 123, "amount": 100.0})
            hints: Optional optimization hints to speed up verification:
                - batch_id: Direct batch lookup (fastest method)
                - database_name: Limit search to specific database
                - table_name: Limit search to specific table
                - time_start/time_end: Search within time range (ISO format, e.g. "2025-06-14T00:00:00")
                - expected_operation: Expected operation type (INSERT, UPDATE, DELETE) to disambiguate
                  hash collisions when the same data appears in multiple operations
            timeout: Override default timeout for this verification
            use_contract_verification: Use blockchain-only verification (no S3)
            
        Returns:
            VerificationResultOut: Detailed verification result with proof and metadata
            
        Note:
            The expected_operation parameter is crucial when verifying transactions where
            the same data might appear in both INSERT and DELETE operations, as these
            would produce identical hashes but represent different database events.
        """
        try:
            start_time = datetime.now()
            
            # Create verification hints if provided
            verification_hints = None
            if hints:
                time_range = None
                if hints.time_start and hints.time_end:
                    time_range = TimeRange(
                        start=datetime.fromisoformat(hints.time_start.replace('Z', '+00:00')),
                        end=datetime.fromisoformat(hints.time_end.replace('Z', '+00:00'))
                    )
                
                # Only create VerificationHints if there are actual hints to use
                if any([hints.batch_id, hints.table_name, hints.database_name, time_range, hints.expected_operation]):
                    verification_hints = VerificationHints(
                        batch_id=hints.batch_id,
                        table_name=hints.table_name,
                        database_name=hints.database_name,
                        time_range=time_range,
                        expected_operation=hints.expected_operation
                    )
            
            # Use SDK directly
            result = await etrap_client.verify_transaction(
                transaction_data,
                hints=verification_hints,
                use_contract_verification=use_contract_verification
            )
            
            end_time = datetime.now()
            processing_time_ms = int((end_time - start_time).total_seconds() * 1000)
            
            # Convert to output format
            output = VerificationResultOut(
                verified=result.verified,
                transaction_hash=result.transaction_hash,
                batch_id=result.batch_id,
                blockchain_timestamp=result.blockchain_timestamp,
                error=result.error,
                verification_method='smart_contract' if use_contract_verification else 'local',
                processing_time_ms=processing_time_ms
            )
            
            # Add merkle proof if available
            if result.merkle_proof:
                output.merkle_proof = MerkleProofOut(
                    leaf_hash=result.merkle_proof.leaf_hash,
                    proof_path=result.merkle_proof.proof_path,
                    sibling_positions=result.merkle_proof.sibling_positions,
                    merkle_root=result.merkle_proof.merkle_root,
                    is_valid=result.merkle_proof.is_valid
                )
            
            # Get batch info if verified
            if result.verified and result.batch_id:
                batch = await etrap_client.get_batch(result.batch_id)
                if batch:
                    output.batch_info = BatchInfoOut(
                        database=batch.database_name,
                        tables=batch.table_names,
                        transaction_count=batch.transaction_count,
                        timestamp=batch.timestamp
                    )
            
            # Add operation type from SDK result
            output.operation_type = result.operation_type
            
            return output
            
        except Exception as e:
            # Return error result
            return VerificationResultOut(
                verified=False,
                transaction_hash="",
                error=str(e),
                processing_time_ms=0
            )