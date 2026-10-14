"""OpenID Connect sign-in against a fake provider that signs real RS256 ID tokens."""

import json
import time
from urllib.parse import parse_qs, urlparse

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from httpx import AsyncClient

from app.services import sso_service

ISSUER = "https://idp.example.edu"
CLIENT_ID = "examsentinel-test"
_KEY = rsa.generate_private_key(public_exponent=65537, key_size=2048)
_JWK = json.loads(jwt.algorithms.RSAAlgorithm.to_jwk(_KEY.public_key()))
_JWK.update({"kid": "test-key", "use": "sig", "alg": "RS256"})


@pytest.fixture
def fake_idp(monkeypatch):
    monkeypatch.setenv("SSO_OIDC_ISSUER", ISSUER)
    monkeypatch.setenv("SSO_OIDC_CLIENT_ID", CLIENT_ID)
    monkeypatch.setenv("SSO_OIDC_CLIENT_SECRET", "secret")
    monkeypatch.setenv("SSO_OIDC_NAME", "Test University")
    monkeypatch.setenv("FRONTEND_URL", "http://app.test")
    monkeypatch.delenv("SSO_AUTO_PROVISION", raising=False)
    monkeypatch.delenv("SSO_ALLOWED_DOMAINS", raising=False)
    sso_service._discovery_cache.clear()
    sso_service._jwks_cache.clear()
    idp = {"claims": {}, "token_requests": []}

    async def fetch_json(url):
        if url.endswith("/.well-known/openid-configuration"):
            return {"issuer": ISSUER, "authorization_endpoint": f"{ISSUER}/authorize",
                    "token_endpoint": f"{ISSUER}/token", "jwks_uri": f"{ISSUER}/jwks"}
        if url == f"{ISSUER}/jwks":
            return {"keys": [_JWK]}
        raise AssertionError(url)

    async def post_form(url, data):
        idp["token_requests"].append(data)
        now = int(time.time())
        claims = {"iss": ISSUER, "aud": CLIENT_ID, "sub": "user-123", "iat": now, "exp": now + 300,
                  "nonce": idp["nonce"], "email": "candidate@sentinel.edu", "email_verified": True, "name": "Cand"}
        claims.update(idp["claims"])
        return {"id_token": jwt.encode(claims, _KEY, algorithm="RS256", headers={"kid": "test-key"})}

    monkeypatch.setattr(sso_service, "fetch_json", fetch_json)
    monkeypatch.setattr(sso_service, "post_form", post_form)
    return idp


async def _start(client: AsyncClient, idp: dict) -> tuple[str, str]:
    r = await client.get("/api/auth/sso/oidc/login", follow_redirects=False)
    assert r.status_code == 302, r.text
    query = parse_qs(urlparse(r.headers["location"]).query)
    assert query["code_challenge_method"] == ["S256"] and query["client_id"] == [CLIENT_ID]
    idp["nonce"] = query["nonce"][0]
    return query["state"][0], r.cookies.get("es_sso_state") or client.cookies.get("es_sso_state")


def _redirect_params(response) -> tuple[str, dict]:
    url = urlparse(response.headers["location"])
    return f"{url.scheme}://{url.netloc}{url.path}", parse_qs(url.query)


async def test_providers_lists_only_configured(async_client: AsyncClient, fake_idp):
    r = await async_client.get("/api/auth/sso/providers")
    assert r.json() == [{"id": "oidc", "name": "Test University"}]


async def test_full_sign_in_with_single_use_ticket(async_client: AsyncClient, seed_users, fake_idp):
    state, cookie = await _start(async_client, fake_idp)
    r = await async_client.get(f"/api/auth/sso/oidc/callback?code=abc&state={state}", cookies={"es_sso_state": cookie},
                               follow_redirects=False)
    target, params = _redirect_params(r)
    assert target == "http://app.test/auth/sso-callback", params
    assert "token" not in r.headers["location"]  # no credentials in URLs
    assert fake_idp["token_requests"][0]["code_verifier"]  # PKCE verifier sent

    ok = await async_client.post("/api/auth/sso/exchange", json={"ticket": params["ticket"][0]})
    assert ok.status_code == 200, ok.text
    assert ok.json()["user"]["email"] == "candidate@sentinel.edu" and ok.json()["access_token"]
    replay = await async_client.post("/api/auth/sso/exchange", json={"ticket": params["ticket"][0]})
    assert replay.status_code == 401


@pytest.mark.parametrize(
    ("tamper", "expected_error"),
    [
        ({"nonce": "attacker"}, "sso_token_invalid"),
        ({"aud": "another-app"}, "sso_token_invalid"),
        ({"iss": "https://evil.example"}, "sso_token_invalid"),
        ({"exp": int(time.time()) - 3600}, "sso_token_invalid"),
        ({"email_verified": False}, "sso_email_unverified"),
        ({"email": "stranger@elsewhere.edu"}, "sso_no_account"),
    ],
)
async def test_rejected_identities(async_client: AsyncClient, seed_users, fake_idp, tamper, expected_error):
    state, cookie = await _start(async_client, fake_idp)
    fake_idp["claims"] = tamper
    r = await async_client.get(f"/api/auth/sso/oidc/callback?code=abc&state={state}", cookies={"es_sso_state": cookie},
                               follow_redirects=False)
    target, params = _redirect_params(r)
    assert target == "http://app.test/auth/login"
    assert params["error"] == [expected_error]


async def test_state_mismatch_and_missing_cookie_are_rejected(async_client: AsyncClient, seed_users, fake_idp):
    state, cookie = await _start(async_client, fake_idp)
    r = await async_client.get("/api/auth/sso/oidc/callback?code=abc&state=forged", cookies={"es_sso_state": cookie},
                               follow_redirects=False)
    assert _redirect_params(r)[1]["error"] == ["sso_state_invalid"]
    async_client.cookies.clear()
    r = await async_client.get(f"/api/auth/sso/oidc/callback?code=abc&state={state}", follow_redirects=False)
    assert _redirect_params(r)[1]["error"] == ["sso_state_missing"]


async def test_auto_provision_and_domain_allow_list(async_client: AsyncClient, seed_users, fake_idp, monkeypatch):
    monkeypatch.setenv("SSO_AUTO_PROVISION", "true")
    monkeypatch.setenv("SSO_ALLOWED_DOMAINS", "uni.edu")

    state, cookie = await _start(async_client, fake_idp)
    fake_idp["claims"] = {"email": "new.student@other.edu"}
    r = await async_client.get(f"/api/auth/sso/oidc/callback?code=abc&state={state}", cookies={"es_sso_state": cookie},
                               follow_redirects=False)
    assert _redirect_params(r)[1]["error"] == ["sso_domain_not_allowed"]

    state, cookie = await _start(async_client, fake_idp)
    fake_idp["claims"] = {"email": "New.Student@uni.edu", "name": "New Student"}
    r = await async_client.get(f"/api/auth/sso/oidc/callback?code=abc&state={state}", cookies={"es_sso_state": cookie},
                               follow_redirects=False)
    ticket = _redirect_params(r)[1]["ticket"][0]
    user = (await async_client.post("/api/auth/sso/exchange", json={"ticket": ticket})).json()["user"]
    assert user["email"] == "new.student@uni.edu" and user["role"] == "candidate"


async def test_unconfigured_provider_returns_to_login(async_client: AsyncClient):
    r = await async_client.get("/api/auth/sso/google/login", follow_redirects=False)
    assert r.status_code == 302 and "error=sso_unavailable" in r.headers["location"]
