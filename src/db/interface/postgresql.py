from contextlib import contextmanager
import logging

from typing import Optional

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base

from src.db.interface.base import BaseDatabase
from src.schemas.database.config import PostgreSQLSettings

logger = logging.getLogger(__name__)
Base = declarative_base()


class PostgreSQLDatabase(BaseDatabase):
    """PostgreSQL database implementation."""

    def __init__(self, config: PostgreSQLSettings) -> None:
        self.config = config
        self.engine: Optional[Engine] = None
        self.session_factory: Optional[sessionmaker] = None

    def startup(self) -> None:
        """Initialize the database connection."""
        try:
            logger.info(
                f"Attempting to connect to PostgreSQL at: {self.config.database_url.split('@')[1] if '@' in self.config.database_url else 'localhost'}"
            )

            self.engine = create_engine(
                self.config.database_url,
                echo=self.config.echo_sql,
                pool_size=self.config.pool_size,
                max_overflow=self.config.max_overflow,
                pool_pre_ping=True
            )

            self.session_factory = sessionmaker(bind=self.engine)

            assert self.engine is not None

            with self.engine.connect() as conn:
                conn.execute(text("SELECT 1"))
                logger.info("Successfully connected to PostgreSQL database.")
            inspector = inspect(self.engine)
            existing_tables = inspector.get_table_names()
            Base.metadata.create_all(bind=self.engine)
            updated_tables = inspector.get_table_names()
            new_tables = set(updated_tables) - set(existing_tables)

            if new_tables:
                logger.info(f"New tables created: {', '.join(new_tables)}")
            else:
                logger.info("No new tables created.")


            logger.info("PostgreSQL database initialized successfully")
            assert self.engine is not None
            logger.info(f"Database: {self.engine.url.database}")
            logger.info(f"Total tables: {', '.join(updated_tables) if updated_tables else 'None'}")
            logger.info("Database connection established")
        except Exception as e:
            logger.error(f"Failed to initialize PostgreSQL database: {e}")
            raise

    def teardown(self) -> None:
        """Close the database connection."""
        if self.engine:
            self.engine.dispose()
            logger.info("PostgreSQL database connections closed")

    @contextmanager
    def get_session(self):
        """Get a database session."""
        if not self.session_factory:
            raise RuntimeError("database not initialized. Call startup() first.")

        session = self.session_factory()
        try:
            yield session
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()
