from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Database
    database_url: str
    database_pool_size: int = 20
    database_max_overflow: int = 10

    # Redis
    redis_url: str
    redis_pool_size: int = 20
    cache_ttl_seconds: int = 3600
    rate_limit_ttl_seconds: int = 60

    # App
    base_domain: str = "http://localhost:8000"
    secret_key: str = "dev-secret"
    environment: str = "development"

    # Rate limiting
    rate_limit_shorten: str = "10/minute"
    rate_limit_redirect: str = "120/minute"

    # URL config
    default_expiry_days: int = 365
    max_custom_alias_length: int = 32
    short_code_length: int = 7

    # CORS
    allowed_origins: str = "http://localhost:3000"

    @property
    def allowed_origins_list(self) -> list[str]:
        return [o.strip() for o in self.allowed_origins.split(",")]

    @property
    def is_production(self) -> bool:
        return self.environment == "production"


@lru_cache
def get_settings() -> Settings:
    return Settings()
