from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

class BaseConfigSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
        frozen=True,
        env_nested_delimiter="__",
        case_sensitive=False,
        env_file_encoding="utf-8",
    )


class ArxivSettings(BaseConfigSettings):
    model_config = SettingsConfigDict(
        env_file=[".env"],
        env_prefix="ARXIV__",
        extra="ignore",
        frozen=True,
        case_sensitive=False,
    )
    base_url: str = "https://export.arxiv.org/api/query"
    pdf_cache_dir: str = "./data/arxiv_pdfs"
    rate_limit_delay: float = 3.0
    timeout_seconds: int = 30
    max_results: int = 15
    search_category: str = "cs.AI"
    download_max_retries: int = 3
    download_retry_delay_base: float = 5.0
    max_concurrent_downloads: int = 5
    max_concurrent_parsing: int = 1

    namespaces: dict = {
        "atom": "http://www.w3.org/2005/Atom",
        "opensearch": "http://a9.com/-/spec/opensearch/1.1/",
        "arxiv": "http://arxiv.org/schemas/atom",
    }


class Settings(BaseConfigSettings):
    database_url: str = "postgresql+psycopg://rag_user:rag_password@localhost:5432/rag_db"

    arxiv: ArxivSettings = Field(default_factory=ArxivSettings)

settings = Settings() # type: ignore[call-arg] # Loaded from .env file
