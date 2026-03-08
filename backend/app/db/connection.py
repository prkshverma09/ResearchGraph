"""SurrealDB connection management."""

import asyncio
import logging
from typing import Optional, Any, Dict, List
from surrealdb import AsyncSurreal
from app.config import settings

logger = logging.getLogger(__name__)


class SurrealDBManager:
    """Manages SurrealDB connection with retry logic and health checks."""
    
    def __init__(
        self,
        url: Optional[str] = None,
        user: Optional[str] = None,
        password: Optional[str] = None,
        namespace: Optional[str] = None,
        database: Optional[str] = None,
    ):
        """Initialize SurrealDB manager.
        
        Args:
            url: SurrealDB connection URL (defaults to settings)
            user: SurrealDB user (defaults to settings)
            password: SurrealDB password (defaults to settings)
            namespace: SurrealDB namespace (defaults to settings)
            database: SurrealDB database (defaults to settings)
        """
        self.url = url or settings.surrealdb_url
        self.user = user or settings.surrealdb_user
        self.password = password or settings.surrealdb_password
        self.namespace = namespace or settings.surrealdb_namespace
        self.database = database or settings.surrealdb_database
        self.client: Optional[AsyncSurreal] = None
        self._connected = False
    
    async def connect(self, max_retries: int = 3, retry_delay: float = 1.0) -> None:
        """Connect to SurrealDB with retry logic.
        
        Args:
            max_retries: Maximum number of connection retries
            retry_delay: Initial delay between retries (exponential backoff)
        """
        for attempt in range(max_retries):
            try:
                self.client = AsyncSurreal(self.url)
                await self.client.connect()
                await self.client.signin({
                    "username": self.user,
                    "password": self.password,
                })
                await self.client.use(self.namespace, self.database)
                self._connected = True
                logger.info(
                    f"Connected to SurrealDB at {self.url} "
                    f"(namespace: {self.namespace}, database: {self.database})"
                )
                return
            except Exception as e:
                if attempt < max_retries - 1:
                    delay = retry_delay * (2 ** attempt)
                    logger.warning(
                        f"Connection attempt {attempt + 1} failed: {e}. "
                        f"Retrying in {delay}s..."
                    )
                    await asyncio.sleep(delay)
                else:
                    logger.error(f"Failed to connect to SurrealDB after {max_retries} attempts")
                    raise
    
    async def disconnect(self) -> None:
        """Disconnect from SurrealDB."""
        if self.client and self._connected:
            try:
                await self.client.close()
                self._connected = False
                logger.info("Disconnected from SurrealDB")
            except Exception as e:
                logger.error(f"Error disconnecting from SurrealDB: {e}")
    
    async def health_check(self) -> bool:
        """Check if SurrealDB connection is healthy.
        
        Returns:
            True if connection is healthy, False otherwise
        """
        if not self._connected or not self.client:
            return False
        
        try:
            # Simple query to check connection - use INFO which is always available
            result = await self.client.query("INFO FOR DB")
            return result is not None
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return False
    
    async def execute(
        self,
        query: str,
        params: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """Execute a SurrealQL query.
        
        Args:
            query: SurrealQL query string
            params: Optional query parameters
        
        Returns:
            List of result dictionaries
        """
        if not self._connected or not self.client:
            raise RuntimeError("Not connected to SurrealDB. Call connect() first.")
        
        try:
            if params:
                result = await self.client.query(query, params)
            else:
                result = await self.client.query(query)

            if isinstance(result, str):
                raise Exception(result)
            
            # Extract results from SurrealDB response format.
            # SDK responses may be:
            # - list[{"result": [...]}]
            # - {"result": [...]} or {"result": {...}}
            # - plain list of rows
            if isinstance(result, dict):
                if "error" in result and result["error"]:
                    raise Exception(result["error"])
                if "result" in result:
                    value = result["result"]
                    if isinstance(value, list):
                        return value
                    if isinstance(value, dict):
                        return [value]
                    return []
                return [result]
            if isinstance(result, list) and len(result) > 0:
                first = result[0]
                if isinstance(first, dict) and "error" in first and first["error"]:
                    raise Exception(first["error"])
                if isinstance(first, dict) and "result" in first:
                    value = first["result"]
                    if isinstance(value, list):
                        return value
                    if isinstance(value, dict):
                        return [value]
                    return []
                return result
            return []
        except Exception as e:
            logger.error(f"Query execution failed: {e}")
            raise
    
    async def query(
        self,
        query: str,
        params: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """Alias for execute() method for convenience.
        
        Args:
            query: SurrealQL query string
            params: Optional query parameters
        
        Returns:
            List of result dictionaries
        """
        return await self.execute(query, params)

    async def query_raw(
        self,
        query: str,
        params: Optional[Dict[str, Any]] = None,
    ) -> Any:
        """Execute a SurrealQL query and return the raw client response."""
        if not self._connected or not self.client:
            raise RuntimeError("Not connected to SurrealDB. Call connect() first.")
        if params:
            return await self.client.query(query, params)
        return await self.client.query(query)
    
    async def __aenter__(self):
        """Async context manager entry."""
        await self.connect()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.disconnect()
