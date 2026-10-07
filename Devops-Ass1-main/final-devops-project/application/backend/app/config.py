"""Runtime settings. Every value can be overridden with an environment variable."""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "TicketHub"
    app_env: str = "development"
    database_url: str = "postgresql+psycopg://tickethub:tickethub@localhost:5432/tickethub"
    cors_origins: str = "*"


settings = Settings()
