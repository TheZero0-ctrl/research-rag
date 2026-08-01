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

class Settings(BaseConfigSettings):
    database_url: str = "postgresql+psycopg://rag_user:rag_password@localhost:5432/rag_db"


settings = Settings() # type: ignore[call-arg] # Loaded from .env file
