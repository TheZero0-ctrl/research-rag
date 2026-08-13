from src.db.interface.base import BaseDatabase
from src.config import settings
from src.db.interface.postgresql import PostgreSQLDatabase
from src.schemas.database.config import PostgreSQLSettings


def make_database() -> BaseDatabase:
    """
    Factory method to create a database instance
    :return: an instance of database
    :rtype: BaseDatabase
    """

    config = PostgreSQLSettings(
        database_url=settings.postgres_database_url,
        echo_sql=settings.postgres_echo_sql,
        pool_size=settings.postgres_pool_size,
        max_overflow=settings.postgres_max_overflow
    )

    database = PostgreSQLDatabase(config=config)
    database.startup()
    return database
