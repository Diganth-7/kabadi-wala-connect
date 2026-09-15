"""
config.py
---------
Central place where we read settings (secrets, DB URL, JWT config, etc.)
from environment variables (the .env file).

Why do this instead of hard-coding values?
- Secrets (passwords, JWT keys) should NEVER be written directly in code.
- Different environments (dev/staging/production) can have different
  values without changing any code — just change the .env file.

We use `pydantic-settings`, which:
1. Automatically reads variables from a `.env` file.
2. Validates their types (e.g. makes sure a port number is an int).
3. Gives us one `settings` object we can import anywhere in the app.
"""

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # --- Database ---
    DATABASE_URL: str

    # --- JWT / Auth ---
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440  # 24 hours by default

    # --- CORS ---
    # Comma separated string in .env, e.g. "http://localhost:5173,http://localhost:3000"
    CORS_ORIGINS: str = "http://localhost:5173"

    # --- App environment ---
    ENVIRONMENT: str = "development"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
    )

    @model_validator(mode="after")
    def validate_production_security(self):
        """Reject unsafe secret/CORS settings when running in production."""
        if self.is_production:
            if len(self.JWT_SECRET_KEY) < 32 or self.JWT_SECRET_KEY == "change-this-to-a-long-random-secret-string":
                raise ValueError("JWT_SECRET_KEY must be at least 32 characters in production.")

            if "*" in self.CORS_ORIGINS.split(","):
                raise ValueError("CORS_ORIGINS cannot contain '*' in production.")

        return self

    @property
    def cors_origins_list(self) -> list[str]:
        """Turns 'http://a.com,http://b.com' into ['http://a.com', 'http://b.com']."""
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT.lower() == "production"


# A single, shared Settings instance used across the whole app.
# Importing `settings` from this file always gives you the same loaded config.
settings = Settings()
