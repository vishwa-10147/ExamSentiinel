from typing import Annotated, List, Optional, Union

from dotenv import load_dotenv
from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

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

    # Proxies whose X-Forwarded-For is trusted to identify the client (uvicorn
    # --forwarded-allow-ips; read by docker-entrypoint.sh). Behind an AWS ALB use the VPC CIDR,
    # e.g. "10.0.0.0/16". Never "*": the client could then choose its own IP address.
    FORWARDED_ALLOW_IPS: str = "127.0.0.1"
    # Optional single header carrying the client IP, set by a proxy that strips client copies
    # (e.g. "CF-Connecting-IP"). Leave empty behind an ALB.
    CLIENT_IP_HEADER: Optional[str] = None

    # Database connection pool (PostgreSQL), per API worker process. The total
    #   tasks x WEB_CONCURRENCY x (DB_POOL_SIZE + DB_MAX_OVERFLOW)  (+ migrations, admin tools)
    # must stay below the server's max_connections (PostgreSQL default 100; on RDS it depends on
    # the instance size). Requests hold a connection only briefly - submissions and judging do
    # not keep one while code runs - so 10 per process sustained 250 simultaneous students.
    DB_POOL_SIZE: int = 5
    DB_MAX_OVERFLOW: int = 5
    DB_POOL_TIMEOUT: int = 30
    SQL_ECHO: bool = False

    # CloudWatch Embedded Metric Format lines once a minute per process (app/core/metrics.py).
    # Default: on in production, off elsewhere.
    METRICS_ENABLED: Optional[bool] = None  # log every SQL statement (very noisy; development diagnosis only)

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5440/examsentinel"

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
    BREVO_API_KEY: str = ""
    SENDGRID_API_KEY: str = ""



    # CORS. From the environment: comma-separated ("https://a,https://b") or a JSON list.
    # NoDecode: without it pydantic-settings JSON-decodes the value first and a plain URL fails.
    CORS_ORIGINS: Annotated[List[str], NoDecode] = [
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
            problems = production_problems(self)
            if problems:
                raise ValueError("Unsafe production settings:\n- " + "\n- ".join(problems))
        return self

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )


_LOCAL_HOSTS = {"localhost", "127.0.0.1", "0.0.0.0", "::1"}


def production_problems(s: "Settings") -> list[str]:
    """Every reason these settings are unsafe for production (empty list = OK).

    Checked at start-up when ENVIRONMENT=production, so a misconfigured task fails to start
    instead of serving exams with development defaults.
    """
    import os

    problems = []
    if s.DEBUG:
        problems.append("DEBUG must be false (it exposes /docs and detailed errors)")
    if s.SECRET_KEY.startswith("examsentinel_super_secret") or len(s.SECRET_KEY) < 32:
        problems.append("SECRET_KEY must be a random value of at least 32 characters (openssl rand -hex 32)")
    if not s.CORS_ORIGINS:
        problems.append("CORS_ORIGINS must list the public frontend origin")
    from urllib.parse import urlsplit

    for origin in s.CORS_ORIGINS:
        if origin == "*" or not origin.startswith("https://") or urlsplit(origin).hostname in _LOCAL_HOSTS:
            problems.append(f"CORS_ORIGINS entry {origin!r} must be the https:// origin of the deployed frontend")
    if s.DATABASE_URL.startswith("sqlite"):
        problems.append("DATABASE_URL must point to PostgreSQL, not SQLite")
    elif "postgres:postgres@localhost" in s.DATABASE_URL:
        problems.append("DATABASE_URL still has the development default")
    if s.COOKIE_SECURE is False:
        problems.append("COOKIE_SECURE must not be false (session cookies would travel over plain HTTP)")
    if s.COOKIE_SAMESITE.lower() not in ("lax", "strict"):
        problems.append("COOKIE_SAMESITE must be lax or strict (the CSRF protection relies on it)")
    if s.FORWARDED_ALLOW_IPS.strip() == "*":
        problems.append('FORWARDED_ALLOW_IPS must list the load balancer network, not "*" (clients could fake their IP)')
    piston = os.getenv("PISTON_URL", "")
    if "emkc.org" in piston:
        problems.append("PISTON_URL must point at your own code-execution engine, not the public emkc.org API")
    return problems


settings = Settings()
