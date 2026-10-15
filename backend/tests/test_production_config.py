"""Production start-up refuses unsafe settings, and client IPs cannot be faked with headers."""

from types import SimpleNamespace

import pytest

from app.api import deps
from app.api.deps import extract_client_ip
from app.core.config import Settings, production_problems

GOOD = dict(
    ENVIRONMENT="production",
    DEBUG=False,
    SECRET_KEY="0123456789abcdef0123456789abcdef0123456789abcdef",
    CORS_ORIGINS=["https://exam.example.edu"],
    DATABASE_URL="postgresql+asyncpg://app:secret@db.internal:5432/examsentinel",
    FORWARDED_ALLOW_IPS="10.0.0.0/16",
)


def test_a_complete_production_configuration_starts(monkeypatch):
    monkeypatch.setenv("PISTON_URL", "http://piston.internal:2000/api/v2/execute")
    settings = Settings(**GOOD)
    assert production_problems(settings) == []


@pytest.mark.parametrize("override, fragment", [
    ({"DEBUG": True}, "DEBUG"),
    ({"SECRET_KEY": "examsentinel_super_secret_jwt_key_for_dev_change_in_production_987654321"}, "SECRET_KEY"),
    ({"SECRET_KEY": "short"}, "SECRET_KEY"),
    ({"CORS_ORIGINS": ["http://localhost:3000"]}, "CORS_ORIGINS"),
    ({"CORS_ORIGINS": ["http://exam.example.edu"]}, "CORS_ORIGINS"),
    ({"CORS_ORIGINS": ["*"]}, "CORS_ORIGINS"),
    ({"CORS_ORIGINS": ["https://localhost:3000"]}, "CORS_ORIGINS"),
    ({"CORS_ORIGINS": ["https://127.0.0.1"]}, "CORS_ORIGINS"),
    ({"DATABASE_URL": "sqlite+aiosqlite:///./prod.db"}, "SQLite"),
    ({"DATABASE_URL": "postgresql+asyncpg://postgres:postgres@localhost:5440/examsentinel"}, "development default"),
    ({"COOKIE_SECURE": False}, "COOKIE_SECURE"),
    ({"COOKIE_SAMESITE": "none"}, "COOKIE_SAMESITE"),
    ({"FORWARDED_ALLOW_IPS": "*"}, "FORWARDED_ALLOW_IPS"),
])
def test_unsafe_production_settings_are_refused(override, fragment):
    with pytest.raises(ValueError) as error:
        Settings(**{**GOOD, **override})
    assert fragment in str(error.value)


def test_the_public_piston_api_is_refused(monkeypatch):
    monkeypatch.setenv("PISTON_URL", "https://emkc.org/api/v2/piston/execute")
    with pytest.raises(ValueError, match="emkc.org"):
        Settings(**GOOD)


def test_all_problems_are_reported_together():
    with pytest.raises(ValueError) as error:
        Settings(ENVIRONMENT="production", DATABASE_URL="sqlite:///x.db", CORS_ORIGINS=["http://localhost:3000"])
    message = str(error.value)
    assert all(word in message for word in ("DEBUG", "SECRET_KEY", "CORS_ORIGINS", "SQLite"))


def test_development_defaults_still_start():
    assert Settings(ENVIRONMENT="development", DATABASE_URL="sqlite+aiosqlite:///./dev.db").DEBUG is True


def _request(client_host: str, headers: dict) -> SimpleNamespace:
    return SimpleNamespace(client=SimpleNamespace(host=client_host), headers=headers)


def test_client_supplied_ip_headers_are_ignored(monkeypatch):
    monkeypatch.setattr(deps.settings, "CLIENT_IP_HEADER", None)
    spoofed = {"X-Forwarded-For": "203.0.113.9", "X-Real-IP": "198.51.100.7", "CF-Connecting-IP": "192.0.2.1",
               "True-Client-IP": "192.0.2.2"}
    # request.client is what uvicorn resolved, trusting only FORWARDED_ALLOW_IPS proxies.
    assert extract_client_ip(_request("172.16.0.5", spoofed)) == "172.16.0.5"


def test_a_configured_proxy_header_is_used(monkeypatch):
    monkeypatch.setattr(deps.settings, "CLIENT_IP_HEADER", "CF-Connecting-IP")
    assert extract_client_ip(_request("10.0.0.2", {"CF-Connecting-IP": "203.0.113.50"})) == "203.0.113.50"
    assert extract_client_ip(_request("10.0.0.2", {})) == "10.0.0.2"


def test_uvicorn_resolves_the_client_behind_a_trusted_load_balancer():
    """What production runs: --proxy-headers --forwarded-allow-ips=<VPC CIDR>."""
    from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware

    seen = {}

    async def app(scope, receive, send):
        seen["client"] = scope["client"][0]

    async def resolve(peer, forwarded_for, trusted):
        scope = {"type": "http", "client": (peer, 1234), "headers": [(b"x-forwarded-for", forwarded_for.encode())]}
        await ProxyHeadersMiddleware(app, trusted_hosts=trusted)(scope, None, None)
        return seen["client"]

    import asyncio

    # The ALB (10.0.3.4) appended the real client; the attacker prepended a fake one.
    assert asyncio.run(resolve("10.0.3.4", "1.2.3.4, 203.0.113.77", "10.0.0.0/16")) == "203.0.113.77"
    # A request that does not come through the load balancer cannot set its address at all.
    assert asyncio.run(resolve("203.0.113.77", "1.2.3.4", "10.0.0.0/16")) == "203.0.113.77"
    # With "*" (the old setting) the client picks its own address - why production refuses it.
    assert asyncio.run(resolve("10.0.3.4", "1.2.3.4, 203.0.113.77", "*")) == "1.2.3.4"


@pytest.mark.parametrize("raw, expected", [
    ("https://exam.example.edu", ["https://exam.example.edu"]),  # the documented format
    ("https://a.example.edu, https://b.example.edu", ["https://a.example.edu", "https://b.example.edu"]),
    ('["https://a.example.edu"]', ["https://a.example.edu"]),
])
def test_cors_origins_from_the_environment(monkeypatch, raw, expected):
    """A plain URL in CORS_ORIGINS used to crash start-up (pydantic-settings JSON-decoded it)."""
    monkeypatch.setenv("CORS_ORIGINS", raw)
    assert Settings().CORS_ORIGINS == expected
