"""Application settings, read once from the environment."""
from functools import lru_cache
from typing import List

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# The placeholder in .env.example. A deployed instance signing tokens with a
# value that is committed to a public repository would let anyone mint an admin
# token, so `_reject_insecure_production` refuses to start on it.
DEFAULT_SECRET = "change-me"
MIN_SECRET_LENGTH = 32


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    app_name: str = "Urban Failure Memory System"
    environment: str = "development"
    debug: bool = True
    api_v1_prefix: str = "/api/v1"

    database_url: str = "mysql+pymysql://ufms:ufms@127.0.0.1:3306/ufms"
    db_echo: bool = False
    db_pool_size: int = 5
    db_max_overflow: int = 10
    db_pool_recycle: int = 1800  # Aiven drops idle connections; recycle before it does.

    secret_key: str = "change-me"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60

    cors_origins: List[str] = ["http://localhost:5173"]

    open_meteo_archive_url: str = "https://archive-api.open-meteo.com/v1/archive"

    @property
    def is_production(self) -> bool:
        return self.environment.lower() in {"production", "prod"}

    @model_validator(mode="after")
    def _reject_insecure_production(self) -> "Settings":
        """Refuse to start a production instance with a guessable secret.

        This raises at import time, so the process dies on boot rather than
        serving requests with forgeable tokens. That is the intended behaviour:
        a deploy that fails immediately with a readable message costs ten
        minutes, and one that succeeds with SECRET_KEY=change-me is an open
        admin API on a public URL.

        Development is left alone deliberately - the whole point of the default
        is that `docker compose up` and `uvicorn` work with no configuration.
        """
        if not self.is_production:
            return self

        problems: List[str] = []
        if self.secret_key == DEFAULT_SECRET:
            problems.append(
                "SECRET_KEY is still the placeholder from .env.example. Generate "
                'one with: python -c "import secrets; '
                'print(secrets.token_urlsafe(48))"'
            )
        elif len(self.secret_key) < MIN_SECRET_LENGTH:
            problems.append(
                f"SECRET_KEY is {len(self.secret_key)} characters; use at least "
                f"{MIN_SECRET_LENGTH}."
            )
        if self.debug:
            problems.append("DEBUG is true in production. Set DEBUG=false.")

        if problems:
            bullets = "".join(f"\n  - {p}" for p in problems)
            raise ValueError("refusing to start in production:" + bullets)
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
