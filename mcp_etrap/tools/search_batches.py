from pydantic import BaseModel
from typing import Dict, Any, Optional, List
from fastmcp import FastMCP

from etrap_sdk import ETRAPClient, SearchCriteria, SearchResults
from datetime import datetime

class SearchCriteriaInput(BaseModel):
    transaction_hash: Optional[str] = None
    database_name: Optional[str] = None
    table_name: Optional[str] = None
    time_start: Optional[str] = None  # ISO format datetime string
    time_end: Optional[str] = None    # ISO format datetime string
    merkle_root: Optional[str] = None
    min_transaction_count: Optional[int] = None
    batch_id_pattern: Optional[str] = None  # Partial batch ID for pattern matching

class SearchMatch(BaseModel):
    batch_id: str
    timestamp: str
    database_name: str
    table_names: List[str]
    transaction_count: int
    merkle_root: str
    match_reason: str  # Why this batch matched the search criteria
    relevance_score: Optional[float] = None

class SearchResultsOut(BaseModel):
    matches: List[SearchMatch]
    total_matches: int
    search_time_ms: int
    search_criteria: Dict[str, Any]
    suggestions: Optional[List[str]] = None  # Search suggestions if no matches

def register_search_batches_tool(mcp: FastMCP, etrap_client: ETRAPClient) -> None:
    @mcp.tool(
        name="search_batches",
        description="Search batches using flexible criteria including transaction hashes, patterns, and metadata. More powerful than list_batches for complex queries."
    )
    async def search_batches(
        criteria: SearchCriteriaInput,
        max_results: int = 50
    ) -> SearchResultsOut:
        """
        Search batches using flexible criteria.
        
        This function provides advanced search capabilities beyond simple filtering,
        including transaction hash lookup, pattern matching, and relevance scoring.
        
        Args:
            criteria: Search criteria:
                - transaction_hash: Find batch containing specific transaction
                - database_name: Search within specific database
                - table_name: Search batches affecting specific table
                - time_start/time_end: Search within time range (ISO format)
                - merkle_root: Find batch with specific Merkle root
                - min_transaction_count: Minimum number of transactions
                - batch_id_pattern: Partial batch ID for pattern matching
            max_results: Maximum number of results to return (default: 50, max: 200)
            
        Returns:
            SearchResultsOut: Search results with matches, relevance scoring, and suggestions
        """
        try:
            # Validate max_results
            if max_results > 200:
                max_results = 200
            
            # Convert time strings to datetime objects
            time_start = None
            time_end = None
            if criteria.time_start:
                time_start = datetime.fromisoformat(criteria.time_start.replace('Z', '+00:00'))
            if criteria.time_end:
                time_end = datetime.fromisoformat(criteria.time_end.replace('Z', '+00:00'))
            
            # Build search criteria
            search_criteria = SearchCriteria(
                transaction_hash=criteria.transaction_hash,
                database_name=criteria.database_name,
                table_name=criteria.table_name,
                time_start=time_start,
                time_end=time_end,
                merkle_root=criteria.merkle_root,
                min_transaction_count=criteria.min_transaction_count,
                batch_id_pattern=criteria.batch_id_pattern
            )
            
            start_time = datetime.now()
            
            # Perform search
            result: SearchResults = await etrap_client.search_batches(
                criteria=search_criteria,
                max_results=max_results
            )
            
            end_time = datetime.now()
            search_time_ms = int((end_time - start_time).total_seconds() * 1000)
            
            # Convert matches to output format
            search_matches = []
            for match in result.matches:
                search_matches.append(SearchMatch(
                    batch_id=match.batch_id,
                    timestamp=match.timestamp.isoformat(),
                    database_name=match.database_name,
                    table_names=match.table_names,
                    transaction_count=match.transaction_count,
                    merkle_root=match.merkle_root,
                    match_reason=match.match_reason,
                    relevance_score=match.relevance_score
                ))
            
            # Build criteria summary
            criteria_dict = {
                "transaction_hash": criteria.transaction_hash,
                "database_name": criteria.database_name,
                "table_name": criteria.table_name,
                "time_start": criteria.time_start,
                "time_end": criteria.time_end,
                "merkle_root": criteria.merkle_root,
                "min_transaction_count": criteria.min_transaction_count,
                "batch_id_pattern": criteria.batch_id_pattern
            }
            
            # Generate suggestions if no matches
            suggestions = None
            if len(search_matches) == 0:
                suggestions = [
                    "Try expanding the time range if searching by date",
                    "Check if the database or table name is spelled correctly", 
                    "Use list_batches to see all available batches",
                    "Try searching without specific criteria to see recent batches"
                ]
            
            return SearchResultsOut(
                matches=search_matches,
                total_matches=len(search_matches),
                search_time_ms=search_time_ms,
                search_criteria=criteria_dict,
                suggestions=suggestions
            )
            
        except Exception as e:
            return SearchResultsOut(
                matches=[],
                total_matches=0,
                search_time_ms=0,
                search_criteria={"error": str(e)},
                suggestions=["An error occurred during search. Check your search criteria and try again."]
            )