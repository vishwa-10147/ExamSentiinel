"""Credentials passed in URLs (WebSocket ?token=, SSO ?ticket=/?code=) never reach the logs."""

import logging

from app.core.logging import RedactSecretsFilter


def _render(msg, args=None) -> str:
    record = logging.LogRecord("uvicorn.error", logging.INFO, __file__, 1, msg, args, None)
    RedactSecretsFilter().filter(record)
    return record.getMessage()


def test_websocket_token_is_redacted():
    line = _render('%s - "WebSocket %s" [accepted]', ("127.0.0.1:5000", "/api/ws/dashboard?token=eyJhbGciOi.payload.sig"))
    assert "eyJ" not in line and "?token=[REDACTED]" in line


def test_other_query_secrets_are_redacted_and_the_rest_kept():
    line = _render("GET /api/auth/sso/google/callback?code=abc123&state=xyz HTTP/1.1")
    assert "abc123" not in line and "code=[REDACTED]&state=xyz" in line
    assert _render("GET /auth/sso-callback?ticket=T0pS3cret") == "GET /auth/sso-callback?ticket=[REDACTED]"


def test_lines_without_secrets_are_untouched():
    assert _render("GET /api/practice/problems?topic=Graphs&sort=number") == "GET /api/practice/problems?topic=Graphs&sort=number"


def test_uvicorn_loggers_carry_the_filter():
    from app.core.logging import setup_logging

    setup_logging()
    for name in ("uvicorn.access", "uvicorn.error"):
        assert any(isinstance(f, RedactSecretsFilter) for f in logging.getLogger(name).filters)
