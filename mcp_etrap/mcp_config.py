"""
Environment configuration for the ETRAP MCP server.

This module handles all environment variables configuration with sensible defaults
and types conversion.
"""

from dataclasses import dataclass
import os

@dataclass
class ETRAPConfig:
    """Configuration for ETRAP connection settings.

    This class handles all environment variable configuration related to
    the ETRAP connection. 

    Required environment variables:
        "ETRAP_ORGANIZATION": The organization identifier (e.g., 'acme')

    Optional environment variables:
        "ETRAP_NETWORK": The NEAR network to use (testnet/mainnet, default: testnet)
        "ETRAP_RPC_ENDPOINT": Custom NEAR RPC endpoint (optional)
        "ETRAP_TIMEOUT": Request timeout in seconds (default: 30)
        "ETRAP_CACHE_TTL": Cache TTL in seconds (default: 300)
        "ETRAP_MAX_RETRIES": Max retry attempts (default: 3)
        
    AWS S3 configuration (optional):
        "AWS_ACCESS_KEY_ID": S3 access key
        "AWS_SECRET_ACCESS_KEY": S3 secret key  
        "AWS_DEFAULT_REGION": S3 region (default: us-west-2)
    """

    def __init__(self):
        """Initialize the configuration from environment variables."""
        self._validate_required_vars()

    @property
    def organization_id(self) -> str:
        """Get the ETRAP organization ID"""
        return os.environ["ETRAP_ORGANIZATION"]

    @property
    def network(self) -> str:
        """Get the NEAR network.
        
        Default: testnet
        """
        return os.getenv("ETRAP_NETWORK", "testnet")

    @property
    def rpc_endpoint(self) -> str | None:
        """Get the custom NEAR RPC endpoint.
        
        Returns None to use default endpoint for the network.
        """
        return os.getenv("ETRAP_RPC_ENDPOINT")

    @property
    def timeout(self) -> int:
        """Get the request timeout in seconds.

        Default: 30 seconds.
        """
        return int(os.getenv("ETRAP_TIMEOUT", "30"))

    @property
    def cache_ttl(self) -> int:
        """Get the cache TTL in seconds.

        Default: 300 seconds (5 minutes).
        """
        return int(os.getenv("ETRAP_CACHE_TTL", "300"))

    @property
    def max_retries(self) -> int:
        """Get the maximum retry attempts.

        Default: 3 retries.
        """
        return int(os.getenv("ETRAP_MAX_RETRIES", "3"))

    @property
    def aws_access_key_id(self) -> str | None:
        """Get the AWS access key ID for S3 access."""
        return os.getenv("AWS_ACCESS_KEY_ID")

    @property
    def aws_secret_access_key(self) -> str | None:
        """Get the AWS secret access key for S3 access."""
        return os.getenv("AWS_SECRET_ACCESS_KEY")

    @property
    def aws_region(self) -> str:
        """Get the AWS region for S3 access.
        
        Default: us-west-2
        """
        return os.getenv("AWS_DEFAULT_REGION", "us-west-2")

    def _validate_required_vars(self) -> None:
        """Validate that all required environment variables are set.

        Raises:
            ValueError: If any required environment variable is missing.
        """
        missing_vars = []
        for var in ["ETRAP_ORGANIZATION"]:
            if var not in os.environ:
                missing_vars.append(var)

        if missing_vars:
            raise ValueError(
                f"Missing required environment variables: {', '.join(missing_vars)}"
            )

# Global instance for easy access
config = ETRAPConfig()