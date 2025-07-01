from pydantic import BaseModel
from typing import Dict, Any, Optional, List
from fastmcp import FastMCP

from etrap_sdk import ETRAPClient, BatchFilter, BatchList
from datetime import datetime

class BatchFilterInput(BaseModel):
    database_name: Optional[str] = None
    table_name: Optional[str] = None
    time_start: Optional[str] = None  # ISO format datetime string
    time_end: Optional[str] = None    # ISO format datetime string
    min_transaction_count: Optional[int] = None
    max_transaction_count: Optional[int] = None

class BatchSummary(BaseModel):
    batch_id: str
    timestamp: str
    database_name: str
    table_names: List[str]
    transaction_count: int
    merkle_root: str
    size_bytes: Optional[int] = None

class BatchListOut(BaseModel):
    batches: List[BatchSummary]
    total_count: int
    offset: int
    limit: int
    has_more: bool
    filter_applied: Optional[Dict[str, Any]] = None

def register_list_batches_tool(mcp: FastMCP, etrap_client: ETRAPClient) -> None:
    @mcp.tool(
        name="list_batches", 
        description="List batches with optional filtering and pagination. Use filters to narrow down results by database, table, time range, or transaction count."
    )
    async def list_batches(
        filter: Optional[BatchFilterInput] = None,
        limit: int = 100,
        offset: int = 0,
        order_by: str = "timestamp_desc"
    ) -> BatchListOut:
        """
        List batches with optional filtering and pagination.
        
        This function retrieves a list of batches with support for various filters
        and pagination. Results are sorted by timestamp (newest first) by default.
        
        Args:
            filter: Optional filter criteria:
                - database_name: Filter by specific database
                - table_name: Filter by specific table
                - time_start/time_end: Filter by time range (ISO format)
                - min_transaction_count/max_transaction_count: Filter by transaction count range
            limit: Maximum number of batches to return (default: 100, max: 1000)
            offset: Number of batches to skip for pagination (default: 0)
            order_by: Sort order - "timestamp_desc", "timestamp_asc", "count_desc", "count_asc" (default: timestamp_desc)
            
        Returns:
            BatchListOut: List of batches with pagination info and filter details
        """
        try:
            # Validate limit
            if limit > 1000:
                limit = 1000
            
            # Convert filter if provided
            batch_filter = None
            if filter:
                # Convert time strings to datetime objects
                time_start = None
                time_end = None
                if filter.time_start:
                    time_start = datetime.fromisoformat(filter.time_start.replace('Z', '+00:00'))
                if filter.time_end:
                    time_end = datetime.fromisoformat(filter.time_end.replace('Z', '+00:00'))
                
                batch_filter = BatchFilter(
                    database_name=filter.database_name,
                    table_name=filter.table_name,
                    time_start=time_start,
                    time_end=time_end,
                    min_transaction_count=filter.min_transaction_count,
                    max_transaction_count=filter.max_transaction_count
                )
            
            # Perform list operation
            result: BatchList = await etrap_client.list_batches(
                filter=batch_filter,
                limit=limit,
                offset=offset,
                order_by=order_by
            )
            
            # Convert batches to output format
            batch_summaries = []
            for batch_info in result.batches:
                batch_summaries.append(BatchSummary(
                    batch_id=batch_info.batch_id,
                    timestamp=batch_info.timestamp.isoformat(),
                    database_name=batch_info.database_name,
                    table_names=batch_info.table_names,
                    transaction_count=batch_info.transaction_count,
                    merkle_root=batch_info.merkle_root,
                    size_bytes=batch_info.size_bytes
                ))
            
            # Build filter summary for response
            filter_applied = None
            if filter:
                filter_applied = {
                    "database_name": filter.database_name,
                    "table_name": filter.table_name,
                    "time_start": filter.time_start,
                    "time_end": filter.time_end,
                    "min_transaction_count": filter.min_transaction_count,
                    "max_transaction_count": filter.max_transaction_count
                }
            
            return BatchListOut(
                batches=batch_summaries,
                total_count=result.total_count,
                offset=offset,
                limit=limit,
                has_more=result.has_more,
                filter_applied=filter_applied
            )
            
        except Exception as e:
            # Return empty result with error indication
            return BatchListOut(
                batches=[],
                total_count=0,
                offset=offset,
                limit=limit,
                has_more=False,
                filter_applied={"error": str(e)}
            )