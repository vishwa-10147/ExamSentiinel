"""httpOnly cookie sessions for browsers, CSRF protection, and login rate limits without Redis."""

from types import SimpleNamespace

from httpx import ASGITransport, AsyncClient

from app.api import monitoring
from app.core.auth_cookies import ACCESS_COOKIE, REFRESH_COOKIE
from app.core.config import settings
from app.main import app

COOKIE_MODE = {"X-Auth-Mode": "cookie", "X-Requested-With": "ExamSentinel"}
ADMIN = {"email": "admin@sentinel.edu", "password": "AdminPass123!"}


def _set_cookies(response) -> dict[str, str]:
    return {c.split("=", 1)[0]: c for c in response.headers.get_list("set-cookie")}


async def test_cookie_login_keeps_tokens_out_of_javascript(async_client: AsyncClient, seed_users):
    r = await async_client.post("/api/auth/login", json=ADMIN, headers=COOKIE_MODE)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["access_token"] is None and body["refresh_token"] is None, "tokens must not be readable by page scripts"
    assert body["user"]["email"] == ADMIN["email"]

    cookies = _set_cookies(r)
    access, refresh = cookies[ACCESS_COOKIE].lower(), cookies[REFRESH_COOKIE].lower()
    for header in (access, refresh):
        assert "httponly" in header and "samesite=lax" in header
    assert "path=/;" in access or access.endswith("path=/")
    assert "path=/api/auth" in refresh, "the refresh token is only sent to auth endpoints"

    # The cookie alone authenticates reads.
    me = await async_client.get("/api/auth/me")
    assert me.status_code == 200 and me.json()["email"] == ADMIN["email"]


async def test_cookie_requests_that_change_state_need_the_csrf_header(async_client: AsyncClient, seed_users):
    await async_client.post("/api/auth/login", json=ADMIN, headers=COOKIE_MODE)
    blocked = await async_client.post("/api/auth/logout")
    assert blocked.status_code == 403 and "X-Requested-With" in blocked.json()["detail"]
    allowed = await async_client.post("/api/auth/logout", headers={"X-Requested-With": "ExamSentinel"})
    assert allowed.status_code == 200
    cleared = _set_cookies(allowed)
    assert ACCESS_COOKIE in cleared and REFRESH_COOKIE in cleared  # deleted (expired) cookies


async def test_cookie_refresh_rotates_without_exposing_tokens(async_client: AsyncClient, seed_users):
    login = await async_client.post("/api/auth/login", json=ADMIN, headers=COOKIE_MODE)
    old_access = login.cookies.get(ACCESS_COOKIE)
    r = await async_client.post("/api/auth/refresh", headers=COOKIE_MODE)
    assert r.status_code == 200, r.text
    assert r.json()["access_token"] is None
    assert r.cookies.get(ACCESS_COOKIE) and r.cookies.get(ACCESS_COOKIE) != old_access
    assert (await async_client.get("/api/auth/me")).status_code == 200


async def test_bearer_clients_are_unchanged(seed_users):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        r = await client.post("/api/auth/login", json=ADMIN)
        assert r.status_code == 200
        body = r.json()
        assert body["access_token"] and body["refresh_token"]
        assert not r.headers.get_list("set-cookie"), "API clients do not get cookies"
        me = await client.get("/api/auth/me", headers={"Authorization": f"Bearer {body['access_token']}"})
        assert me.status_code == 200
        # Bearer requests need no CSRF header.
        out = await client.post("/api/auth/logout", headers={"Authorization": f"Bearer {body['access_token']}"})
        assert out.status_code == 200
        refreshed = await client.post("/api/auth/refresh", json={"refresh_token": body["refresh_token"]})
        assert refreshed.status_code == 401  # logout revoked it


async def test_failed_logins_are_throttled_per_account_without_redis(async_client: AsyncClient, seed_users):
    wrong = {"email": ADMIN["email"], "password": "not-the-password"}
    codes = [(await async_client.post("/api/auth/login", json=wrong)).status_code for _ in range(6)]
    assert codes[:5] == [401] * 5 and codes[5] == 429
    # Even the right password is refused while the account is throttled.
    assert (await async_client.post("/api/auth/login", json=ADMIN)).status_code == 429
    # Another account from the same IP is not locked out by that.
    other = await async_client.post("/api/auth/login", json={"email": "proctor@sentinel.edu", "password": "x"})
    assert other.status_code == 401


async def test_successful_logins_are_not_throttled(async_client: AsyncClient, seed_users):
    codes = [(await async_client.post("/api/auth/login", json=ADMIN)).status_code for _ in range(8)]
    assert codes == [200] * 8


class _FakeWebSocket:
    def __init__(self, cookies, origin):
        self.query_params, self.cookies, self.headers = {}, cookies, {"origin": origin} if origin else {}
        self.closed = None

    async def close(self, code, reason=""):
        self.closed = (code, reason)


async def test_websocket_cookie_auth_requires_an_allowed_origin(async_client: AsyncClient, seed_users, monkeypatch):
    from tests.conftest import test_async_session_maker

    # Look the user up in the test database, not the app's configured one.
    monkeypatch.setattr(monitoring, "async_session_maker", test_async_session_maker)
    login = await async_client.post("/api/auth/login", json=ADMIN, headers=COOKIE_MODE)
    token = login.cookies.get(ACCESS_COOKIE)

    evil = _FakeWebSocket({ACCESS_COOKIE: token}, "https://evil.example")
    assert await monitoring._authenticate_ws(evil) is None
    assert evil.closed and "Origin" in evil.closed[1]

    missing = _FakeWebSocket({ACCESS_COOKIE: token}, None)
    assert await monitoring._authenticate_ws(missing) is None

    allowed_origin = settings.CORS_ORIGINS[0]
    ok = _FakeWebSocket({ACCESS_COOKIE: token}, allowed_origin)
    # Origin passes; the rest of authentication proceeds (it may still close for DB/session reasons,
    # but never for the origin).
    await monitoring._authenticate_ws(ok)
    assert not (ok.closed and "Origin" in ok.closed[1])


async def test_guessing_from_many_ips_hits_the_per_account_limit(async_client: AsyncClient, seed_users, monkeypatch):
    """Rotating IP addresses (a botnet, or a proxy trusted too widely) must not allow unlimited
    guesses at one account."""
    from app.api import deps

    import itertools

    counter = itertools.count()  # a different address every time the API asks
    monkeypatch.setattr(deps, "extract_client_ip", lambda request: f"203.0.{next(counter) % 250}.{next(counter) % 250}")
    wrong = {"email": ADMIN["email"], "password": "not-the-password"}
    codes = [(await async_client.post("/api/auth/login", json=wrong)).status_code for _ in range(31)]
    assert codes[:30] == [401] * 30 and codes[30] == 429
    assert "this account" in (await async_client.post("/api/auth/login", json=ADMIN)).json()["detail"]
    # Other accounts are unaffected.
    assert (await async_client.post("/api/auth/login", json={"email": "proctor@sentinel.edu", "password": "x"})).status_code == 401

    # The owner can get back in at once by resetting the password.
    await deps.failed_login_throttle.clear_account(ADMIN["email"])
    assert (await async_client.post("/api/auth/login", json=ADMIN)).status_code == 200
