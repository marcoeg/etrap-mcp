from pydantic import BaseModel, Field
from typing import Dict, Any, List, Optional, Callable, Literal
from fastmcp import FastMCP

from etrap_sdk import ETRAPClient, BatchVerificationResult, VerificationHints, TimeRange
from datetime import datetime


class BatchVerificationHintsInput(BaseModel):
    batch_id: Optional[str] = Field(None, description="Specific batch ID for direct lookup (fastest method)")
    database_name: Optional[str] = Field(None, description="Database name to limit search scope")
    table_name: Optional[str] = Field(None, description="Table name to limit search scope")
    time_start: Optional[str] = Field(None, description="Start time for time range search (ISO format, e.g. '2025-06-14T00:00:00')")
    time_end: Optional[str] = Field(None, description="End time for time range search (ISO format, e.g. '2025-06-14T23:59:59')")
    expected_operation: Optional[Literal["INSERT", "UPDATE", "DELETE"]] = Field(None, description="Expected operation type to disambiguate hash collisions between different operations on the same data")

class BatchVerificationResultOut(BaseModel):
    total_transactions: int
    verified_count: int
    failed_count: int
    processing_time_ms: int
    verification_timestamp: str
    individual_results: List[Dict[str, Any]]
    summary: Dict[str, Any]

def register_verify_batch_tool(mcp: FastMCP, etrap_client: ETRAPClient) -> None:
    @mcp.tool(
        name="verify_batch",
        description="Verify multiple transactions efficiently in parallel. Use hints to optimize performance - batch_id is fastest, time_range narrows search significantly. Use expected_operation to disambiguate between INSERT/UPDATE/DELETE operations with identical data."
    )
    async def verify_batch(
        transactions: List[Dict[str, Any]],
        hints: Optional[BatchVerificationHintsInput] = None,
        parallel: bool = True,
        fail_fast: bool = False,
        progress_callback: bool = False
    ) -> BatchVerificationResultOut:
        """
        Verify multiple transactions against ETRAP blockchain records.
        
        This function efficiently verifies a batch of transactions, with options
        for parallel processing and early termination on failures.
        
        Args:
            transactions: List of transaction data dictionaries
            hints: Optional optimization hints to speed up verification:
                - batch_id: Direct batch lookup (fastest method)
                - database_name: Limit search to specific database
                - table_name: Limit search to specific table
                - time_start/time_end: Search within time range (ISO format, e.g. "2025-06-14T00:00:00")
                - expected_operation: Expected operation type (INSERT, UPDATE, DELETE) to disambiguate
                  hash collisions when the same data appears in multiple operations
            parallel: Whether to process transactions in parallel (default: True)
            fail_fast: Stop processing on first failure (default: False)
            progress_callback: Whether to enable progress tracking (default: False)
            
        Returns:
            BatchVerificationResultOut: Comprehensive results including individual results and summary
            
        Note:
            The expected_operation parameter is crucial when verifying transactions where
            the same data might appear in both INSERT and DELETE operations, as these
            would produce identical hashes but represent different database events.
        """
        try:
            start_time = datetime.now()
            
            # Convert hints to VerificationHints if provided
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
            
            # Setup progress callback if requested
            callback: Optional[Callable] = None
            if progress_callback:
                def progress_cb(completed: int, total: int) -> None:
                    # Note: In MCP context, we can't really send progress updates
                    # This is just a placeholder for the interface
                    pass
                callback = progress_cb
            
            # Use SDK's verify_batch method
            result: BatchVerificationResult = await etrap_client.verify_batch(
                transactions=transactions,
                hints=verification_hints,
                parallel=parallel,
                fail_fast=fail_fast,
                progress_callback=callback
            )
            
            end_time = datetime.now()
            processing_time_ms = int((end_time - start_time).total_seconds() * 1000)
            
            # Convert individual results to dict format
            individual_results = []
            for individual_result in result.results:
                individual_results.append({
                    "verified": individual_result.verified,
                    "transaction_hash": individual_result.transaction_hash,
                    "batch_id": individual_result.batch_id,
                    "blockchain_timestamp": individual_result.blockchain_timestamp.isoformat() if individual_result.blockchain_timestamp else None,
                    "operation_type": individual_result.operation_type,
                    "error": individual_result.error
                })
            
            # Build summary
            summary = {
                "success_rate": result.summary.success_rate,
                "average_verification_time_ms": result.summary.average_verification_time_ms,
                "blockchain_confirmations": result.summary.blockchain_confirmations,
                "parallel_processing": parallel,
                "fail_fast_mode": fail_fast,
                "hints_used": hints is not None
            }
            
            return BatchVerificationResultOut(
                total_transactions=result.total,
                verified_count=result.verified,
                failed_count=result.failed,
                processing_time_ms=processing_time_ms,
                verification_timestamp=start_time.isoformat(),
                individual_results=individual_results,
                summary=summary
            )
            
        except Exception as e:
            # Return error result
            return BatchVerificationResultOut(
                total_transactions=len(transactions),
                verified_count=0,
                failed_count=len(transactions),
                processing_time_ms=0,
                verification_timestamp=datetime.now().isoformat(),
                individual_results=[],
                summary={
                    "error": str(e),
                    "success_rate": 0.0,
                    "parallel_processing": parallel,
                    "fail_fast_mode": fail_fast
                }
            )