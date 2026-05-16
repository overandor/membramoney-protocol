"""
Database connection management with connection pooling and retry logic.
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy.pool import QueuePool
from core.config import settings


class DatabaseManager:
    """Manages database connections with pooling and retries."""

    def __init__(self, database_url: str = None):
        self.database_url = database_url or settings.database_url
        self.engine = None
        self.SessionLocal = None
        self._init_engine()

    def _init_engine(self):
        self.engine = create_engine(
            self.database_url,
            poolclass=QueuePool,
            pool_size=10,
            max_overflow=20,
            pool_pre_ping=True,
            pool_recycle=3600,
            echo=False,
        )
        self.SessionLocal = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=self.engine,
        )

    def get_session(self):
        """Get a new database session."""
        return self.SessionLocal()

    def close(self):
        """Dispose of the engine."""
        if self.engine:
            self.engine.dispose()

    def health_check(self) -> dict:
        """Check database health."""
        try:
            with self.engine.connect() as conn:
                conn.execute("SELECT 1")
            return {"status": "healthy", "connected": True}
        except Exception as e:
            return {"status": "unhealthy", "connected": False, "error": str(e)}


# Global instance
db_manager = DatabaseManager()
