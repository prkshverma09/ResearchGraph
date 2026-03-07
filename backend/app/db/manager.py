"""Global database manager instance."""

from app.db.connection import SurrealDBManager

# Global DB manager instance
db_manager: SurrealDBManager | None = None
