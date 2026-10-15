"""httpOnly cookie sessions for browsers.

Browsers keep the access and refresh tokens in httpOnly cookies, so page scripts
(including any injected by an XSS bug) can never read them. API clients and scripts
keep using ``Authorization: Bearer`` headers.

A browser asks for cookie mode by sending ``X-Auth-Mode: cookie`` on login, refresh
and SSO exchange; the response then sets the cookies and leaves the tokens out of
the JSON body.

CSRF: cookies are ``SameSite=Lax`` and every state-changing request authenticated by
cookie must carry the ``X-Requested-With`` header. Other sites cannot add a custom
header to a cross-origin request without passing the CORS allow-list.
"""

from typing import Optional

from fastapi import Request, Response

from app.core.config import settings

ACCESS_COOKIE = "es_access"
REFRESH_COOKIE = "es_refresh"
REFRESH_COOKIE_PATH = "/api/auth"
AUTH_MODE_HEADER = "x-auth-mode"
CSRF_HEADER = "x-requested-with"
SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}


def wants_cookie_session(request: Request) -> bool:
    return request.headers.get(AUTH_MODE_HEADER, "").lower() == "cookie"


def _secure() -> bool:
    if settings.COOKIE_SECURE is not None:
        return settings.COOKIE_SECURE
    return settings.ENVIRONMENT.lower() == "production"


def set_auth_cookies(response: Response, access_token: str, refresh_token: str) -> None:
    common = dict(httponly=True, secure=_secure(), samesite=settings.COOKIE_SAMESITE, domain=settings.COOKIE_DOMAIN)
    response.set_cookie(ACCESS_COOKIE, access_token, max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60, path="/", **common)
    response.set_cookie(
        REFRESH_COOKIE, refresh_token, max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 86400, path=REFRESH_COOKIE_PATH, **common
    )


def clear_auth_cookies(response: Response) -> None:
    common = dict(httponly=True, secure=_secure(), samesite=settings.COOKIE_SAMESITE, domain=settings.COOKIE_DOMAIN)
    response.delete_cookie(ACCESS_COOKIE, path="/", **common)
    response.delete_cookie(REFRESH_COOKIE, path=REFRESH_COOKIE_PATH, **common)


def access_token_from_cookie(request: Request) -> Optional[str]:
    return request.cookies.get(ACCESS_COOKIE) or None


def refresh_token_from_cookie(request: Request) -> Optional[str]:
    return request.cookies.get(REFRESH_COOKIE) or None


def csrf_ok(request: Request) -> bool:
    """A cookie-authenticated, state-changing request must carry the CSRF header."""
    return request.method.upper() in SAFE_METHODS or bool(request.headers.get(CSRF_HEADER))
