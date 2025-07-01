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

async def verify_transaction_sdk(
    client: ETRAPClient,
    transaction_data: Dict[str, Any],
    hints: Optional[Dict[str, Any]] = None,
    use_contract_verification: bool = False
) -> Dict[str, Any]:
    """Verify a transaction using the SDK - copied from etrap_verify_sdk.py."""
    start_time = datetime.now()
    
    # Track search statistics
    search_info = {
        'total_batches': 0,
        'batch_position': 0
    }
    
    # Create verification hints if provided
    verification_hints = None
    if hints:
        time_range = None
        if hints.get('time_start') and hints.get('time_end'):
            time_range = TimeRange(
                start=hints['time_start'],
                end=hints['time_end']
            )
        
        verification_hints = VerificationHints(
            batch_id=hints.get('batch_id'),
            table_name=hints.get('table_name'),
            database_name=hints.get('database_name'),
            time_range=time_range,
            expected_operation=hints.get('expected_operation')
        )
    
    # Track if we're using direct batch lookup
    using_batch_hint = hints and hints.get('batch_id')
    
    # Get recent batches for search statistics (unless using batch hint)
    recent_batches = []
    if not using_batch_hint:
        try:
            # Use internal method to get batch count
            recent_batches = await client._get_recent_batches(100)
            search_info['total_batches'] = len(recent_batches)
        except:
            search_info['total_batches'] = 0
    else:
        # For batch hint, we'll update statistics after verification
        search_info['total_batches'] = 1
        search_info['batch_position'] = 1
        search_info['direct_lookup'] = True
    
    # Perform verification
    result = await client.verify_transaction(
        transaction_data,
        hints=verification_hints,
        use_contract_verification=use_contract_verification
    )
    
    end_time = datetime.now()
    processing_time_ms = int((end_time - start_time).total_seconds() * 1000)
    
    # Convert to dictionary format
    response = {
        'verified': result.verified,
        'transaction_hash': result.transaction_hash,
        'batch_id': result.batch_id,
        'blockchain_timestamp': result.blockchain_timestamp,
        'error': result.error,
        'search_info': search_info,
        'verification_method': 'smart_contract' if use_contract_verification else 'local',
        'processing_time_ms': processing_time_ms
    }
    
    if result.merkle_proof:
        response['merkle_proof'] = {
            'leaf_hash': result.merkle_proof.leaf_hash,
            'proof_path': result.merkle_proof.proof_path,
            'sibling_positions': result.merkle_proof.sibling_positions,
            'merkle_root': result.merkle_proof.merkle_root,
            'is_valid': result.merkle_proof.is_valid
        }
    
    # Get batch info and position if verified
    if result.verified and result.batch_id:
        batch = await client.get_batch(result.batch_id)
        if batch:
            response['batch_info'] = {
                'database': batch.database_name,
                'tables': batch.table_names,
                'transaction_count': batch.transaction_count,
                'timestamp': batch.timestamp
            }
            
            # Find position in recent batches
            for i, b in enumerate(recent_batches):
                if b.batch_id == result.batch_id:
                    search_info['batch_position'] = i + 1
                    break
            
            # Use operation type from SDK result if available, otherwise try to get it from batch data
            if result.operation_type:
                response['operation_type'] = result.operation_type
            else:
                # Fallback: try to get operation type from batch data
                try:
                    batch_data = await client.get_batch_data(result.batch_id)
                    if batch_data:
                        # Check cached batch data for operation type
                        cache_key = f"batch_data_{result.batch_id}"
                        if cache_key in client._cache:
                            batch_json = client._cache[cache_key]
                            # Find transaction by hash
                            for tx in batch_json.get('transactions', []):
                                if tx.get('metadata', {}).get('hash') == result.transaction_hash:
                                    response['operation_type'] = tx['metadata'].get('operation_type', 'INSERT')
                                    response['position'] = int(tx['metadata']['transaction_id'].split('-')[-1])
                                    break
                except:
                    # Default to INSERT if can't determine
                    response['operation_type'] = 'INSERT'
    
    return response


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
            # Convert hints to dict format used by SDK function
            hints_dict = {}
            if hints:
                if hints.batch_id:
                    hints_dict['batch_id'] = hints.batch_id
                if hints.database_name:
                    hints_dict['database_name'] = hints.database_name
                if hints.table_name:
                    hints_dict['table_name'] = hints.table_name
                if hints.expected_operation:
                    hints_dict['expected_operation'] = hints.expected_operation
                    
                # Parse time range hints
                if hints.time_start and hints.time_end:
                    start_dt = datetime.fromisoformat(hints.time_start.replace('Z', '+00:00'))
                    end_dt = datetime.fromisoformat(hints.time_end.replace('Z', '+00:00'))
                    hints_dict['time_start'] = start_dt
                    hints_dict['time_end'] = end_dt
            
            # Use the SDK verification function
            result = await verify_transaction_sdk(
                etrap_client, 
                transaction_data, 
                hints_dict, 
                use_contract_verification
            )
            
            # Convert to output format
            output = VerificationResultOut(
                verified=result['verified'],
                transaction_hash=result['transaction_hash'],
                batch_id=result.get('batch_id'),
                blockchain_timestamp=result.get('blockchain_timestamp'),
                error=result.get('error'),
                verification_method=result.get('verification_method', 'local'),
                processing_time_ms=result.get('processing_time_ms', 0)
            )
            
            # Add search info
            if result.get('search_info'):
                si = result['search_info']
                output.search_info = SearchInfoOut(
                    total_batches=si.get('total_batches', 0),
                    batch_position=si.get('batch_position', 0),
                    direct_lookup=si.get('direct_lookup')
                )
            
            # Add merkle proof
            if result.get('merkle_proof'):
                mp = result['merkle_proof']
                output.merkle_proof = MerkleProofOut(
                    leaf_hash=mp['leaf_hash'],
                    proof_path=mp['proof_path'],
                    sibling_positions=mp['sibling_positions'],
                    merkle_root=mp['merkle_root'],
                    is_valid=mp['is_valid']
                )
            
            # Add batch info
            if result.get('batch_info'):
                bi = result['batch_info']
                output.batch_info = BatchInfoOut(
                    database=bi['database'],
                    tables=bi['tables'],
                    transaction_count=bi['transaction_count'],
                    timestamp=bi['timestamp']
                )
            
            # Add operation details
            output.operation_type = result.get('operation_type')
            output.position = result.get('position')
            
            return output
            
        except Exception as e:
            # Return error result
            return VerificationResultOut(
                verified=False,
                transaction_hash="",
                error=str(e),
                processing_time_ms=0
            )