from typing import List, Optional, Union

from dotenv import load_dotenv
from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Several services read optional integrations straight from os.environ
# (PISTON_URL, AWS_*, SMTP_*, *_API_KEY). Load .env into the process
# environment so they see the same values as Settings. Real environment
# variables (ECS task definitions, Secrets Manager) still take precedence.
load_dotenv(".env", override=False)


class Settings(BaseSettings):
    PROJECT_NAME: str = "ExamSentinel"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    LOG_LEVEL: str = "INFO"

    # Security & JWT
    SECRET_KEY: str = "examsentinel_super_secret_jwt_key_for_dev_change_in_production_987654321"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # Browser sessions use httpOnly cookies (see app/core/auth_cookies.py).
    # COOKIE_SECURE defaults to True in production; COOKIE_DOMAIN is only needed when the
    # frontend must see the cookie on a sibling subdomain (it normally does not).
    COOKIE_SECURE: Optional[bool] = None
    COOKIE_SAMESITE: str = "lax"
    COOKIE_DOMAIN: Optional[str] = None

    # Sign-ins per minute from one IP. A whole exam lab can share one NAT address, so this is
    # generous; guessing one account's password is throttled separately (5 failures/minute).
    LOGIN_RATE_LIMIT_PER_IP: int = 300

    # Database connection pool (PostgreSQL). Each API worker process holds up to
    # DB_POOL_SIZE + DB_MAX_OVERFLOW connections; size them against Postgres max_connections.
    DB_POOL_SIZE: int = 10
    DB_MAX_OVERFLOW: int = 20
    DB_POOL_TIMEOUT: int = 30
    SQL_ECHO: bool = False  # log every SQL statement (very noisy; development diagnosis only)

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5440/examsentinel"
    SYNC_DATABASE_URL: str = "postgresql://postgres:postgres@localhost:5440/examsentinel"

    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def assemble_db_connection(cls, v):
        if isinstance(v, str):
            if v.startswith("postgres://"):
                return v.replace("postgres://", "postgresql+asyncpg://", 1)
            if v.startswith("postgresql://") and not v.startswith("postgresql+asyncpg://"):
                return v.replace("postgresql://", "postgresql+asyncpg://", 1)
        return v


    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # Email API Keys (HTTPS Port 443 Providers)
    RESEND_API_KEY: str = ""
    BREVO_API_KEY: str = ""
    SENDGRID_API_KEY: str = ""



    # CORS
    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:8000", "https://examsentinel-frontend.onrender.com", 
    ]

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str):
            if v.startswith("[") and v.endswith("]"):
                import json
                try:
                    return json.loads(v)
                except Exception:
                    pass
            return [i.strip() for i in v.split(",") if i.strip()]
        return v

    @model_validator(mode="after")
    def validate_production_security(self):
        if self.ENVIRONMENT.lower() == "production":
            if self.DEBUG:
                raise ValueError("DEBUG must be false in production")
            if self.SECRET_KEY.startswith("examsentinel_super_secret"):
                raise ValueError("SECRET_KEY must be replaced in production")
            if not self.CORS_ORIGINS:
                raise ValueError("CORS_ORIGINS must contain the deployed frontend origin")
        return self

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )


settings = Settings()
