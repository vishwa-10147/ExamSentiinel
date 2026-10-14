"""OpenID Connect single sign-on (Authorization Code flow with PKCE).

Providers are configured with environment variables; only configured ones are
offered to users:

    SSO_GOOGLE_CLIENT_ID / SSO_GOOGLE_CLIENT_SECRET
    SSO_MICROSOFT_CLIENT_ID / SSO_MICROSOFT_CLIENT_SECRET / SSO_MICROSOFT_TENANT (default "organizations")
    SSO_OIDC_ISSUER / SSO_OIDC_CLIENT_ID / SSO_OIDC_CLIENT_SECRET / SSO_OIDC_NAME   (any OIDC provider,
                                                                                   e.g. a university IdP)

Policy:
    SSO_ALLOWED_DOMAINS   comma-separated email domains allowed to sign in (empty = any)
    SSO_AUTO_PROVISION    "true" creates a candidate account on first sign-in; default: only
                          accounts an admin already created can sign in.
    PUBLIC_API_URL        public base URL of this API (for redirect_uri); default: the request's base URL
    FRONTEND_URL          where the browser returns after sign-in; default: first CORS origin
"""

from __future__ import annotations

import base64
import hashlib
import os
import secrets
import time
from dataclasses import dataclass
from typing import Any, Optional
from urllib.parse import urlencode

import httpx
import jwt

from app.core.config import settings

STATE_TTL_SECONDS = 600
_discovery_cache: dict[str, tuple[float, dict]] = {}
_jwks_cache: dict[str, tuple[float, dict]] = {}
_CACHE_SECONDS = 3600


class SSOError(Exception):
    """Sign-in failed; ``code`` is safe to show in the login URL."""

    def __init__(self, code: str, detail: str = ""):
        super().__init__(detail or code)
        self.code = code


@dataclass(frozen=True)
class Provider:
    id: str
    name: str
    issuer: str
    client_id: str
    client_secret: str
    scopes: str = "openid email profile"
    # Microsoft's multi-tenant endpoints issue tokens whose "iss" contains the real tenant id.
    issuer_is_template: bool = False


def configured_providers() -> dict[str, Provider]:
    providers: dict[str, Provider] = {}
    if os.getenv("SSO_GOOGLE_CLIENT_ID"):
        providers["google"] = Provider(
            "google", "Google", "https://accounts.google.com",
            os.environ["SSO_GOOGLE_CLIENT_ID"], os.getenv("SSO_GOOGLE_CLIENT_SECRET", ""),
        )
    if os.getenv("SSO_MICROSOFT_CLIENT_ID"):
        tenant = os.getenv("SSO_MICROSOFT_TENANT", "organizations")
        providers["microsoft"] = Provider(
            "microsoft", "Microsoft", f"https://login.microsoftonline.com/{tenant}/v2.0",
            os.environ["SSO_MICROSOFT_CLIENT_ID"], os.getenv("SSO_MICROSOFT_CLIENT_SECRET", ""),
            issuer_is_template=tenant in ("organizations", "common", "consumers"),
        )
    if os.getenv("SSO_OIDC_ISSUER") and os.getenv("SSO_OIDC_CLIENT_ID"):
        providers["oidc"] = Provider(
            "oidc", os.getenv("SSO_OIDC_NAME", "Institution SSO"), os.environ["SSO_OIDC_ISSUER"].rstrip("/"),
            os.environ["SSO_OIDC_CLIENT_ID"], os.getenv("SSO_OIDC_CLIENT_SECRET", ""),
        )
    return providers


def get_provider(provider_id: str) -> Provider:
    provider = configured_providers().get(provider_id)
    if provider is None:
        raise SSOError("sso_unavailable", f"SSO provider '{provider_id}' is not configured")
    return provider


def allowed_domains() -> set[str]:
    return {d.strip().lower().lstrip("@") for d in os.getenv("SSO_ALLOWED_DOMAINS", "").split(",") if d.strip()}


def auto_provision() -> bool:
    return os.getenv("SSO_AUTO_PROVISION", "false").lower() == "true"


def frontend_url() -> str:
    explicit = os.getenv("FRONTEND_URL", "").rstrip("/")
    if explicit:
        return explicit
    # The API's own origin may also be listed in CORS_ORIGINS; skip it.
    return next((o.rstrip("/") for o in settings.CORS_ORIGINS if not o.rstrip("/").endswith(":8000")), "http://localhost:3000")


# ---------------------------------------------------------------------------
# Network (patched in tests)
# ---------------------------------------------------------------------------

async def fetch_json(url: str) -> dict:
    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.get(url)
        response.raise_for_status()
        return response.json()


async def post_form(url: str, data: dict) -> dict:
    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.post(url, data=data, headers={"Accept": "application/json"})
        if response.status_code >= 400:
            raise SSOError("sso_exchange_failed", f"Token endpoint returned {response.status_code}")
        return response.json()


async def _cached(cache: dict, url: str) -> dict:
    hit = cache.get(url)
    if hit and hit[0] > time.monotonic():
        return hit[1]
    value = await fetch_json(url)
    cache[url] = (time.monotonic() + _CACHE_SECONDS, value)
    return value


async def discovery(provider: Provider) -> dict:
    return await _cached(_discovery_cache, f"{provider.issuer}/.well-known/openid-configuration")


# ---------------------------------------------------------------------------
# Flow
# ---------------------------------------------------------------------------

def _b64url(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()


def new_flow_state(provider_id: str) -> dict:
    verifier = _b64url(secrets.token_bytes(48))
    return {
        "provider": provider_id,
        "state": secrets.token_urlsafe(24),
        "nonce": secrets.token_urlsafe(24),
        "verifier": verifier,
        "challenge": _b64url(hashlib.sha256(verifier.encode()).digest()),
    }


def seal_state(flow: dict) -> str:
    """Signed, short-lived cookie value carrying the flow secrets."""
    payload = {k: flow[k] for k in ("provider", "state", "nonce", "verifier")}
    payload["exp"] = int(time.time()) + STATE_TTL_SECONDS
    payload["typ"] = "sso_state"
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def open_state(cookie: Optional[str]) -> dict:
    if not cookie:
        raise SSOError("sso_state_missing", "Sign-in session expired; please try again")
    try:
        data = jwt.decode(cookie, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    except jwt.InvalidTokenError as exc:
        raise SSOError("sso_state_invalid", str(exc)) from exc
    if data.get("typ") != "sso_state":
        raise SSOError("sso_state_invalid")
    return data


async def authorization_url(provider: Provider, flow: dict, redirect_uri: str) -> str:
    meta = await discovery(provider)
    query = {
        "response_type": "code",
        "client_id": provider.client_id,
        "redirect_uri": redirect_uri,
        "scope": provider.scopes,
        "state": flow["state"],
        "nonce": flow["nonce"],
        "code_challenge": flow["challenge"],
        "code_challenge_method": "S256",
        "prompt": "select_account",
    }
    return f"{meta['authorization_endpoint']}?{urlencode(query)}"


async def verify_id_token(provider: Provider, id_token: str, nonce: str) -> dict[str, Any]:
    meta = await discovery(provider)
    jwks = await _cached(_jwks_cache, meta["jwks_uri"])
    try:
        kid = jwt.get_unverified_header(id_token).get("kid")
    except jwt.InvalidTokenError as exc:
        raise SSOError("sso_token_invalid", str(exc)) from exc
    keys = [k for k in jwks.get("keys", []) if kid is None or k.get("kid") == kid]
    if not keys:
        # Keys may have rotated since we cached them.
        _jwks_cache.pop(meta["jwks_uri"], None)
        jwks = await _cached(_jwks_cache, meta["jwks_uri"])
        keys = [k for k in jwks.get("keys", []) if kid is None or k.get("kid") == kid]
    if not keys:
        raise SSOError("sso_token_invalid", "Signing key not found")
    signing_key = jwt.PyJWK(keys[0])
    try:
        claims = jwt.decode(
            id_token,
            signing_key.key,
            algorithms=["RS256", "RS384", "RS512", "ES256", "ES384", "PS256"],
            audience=provider.client_id,
            # Microsoft multi-tenant issuers vary per tenant; checked below instead.
            issuer=None if provider.issuer_is_template else meta.get("issuer", provider.issuer),
            options={"require": ["exp", "iat", "sub"], "verify_iss": not provider.issuer_is_template},
            leeway=60,
        )
    except jwt.InvalidTokenError as exc:
        raise SSOError("sso_token_invalid", str(exc)) from exc
    if provider.issuer_is_template:
        tid = claims.get("tid", "")
        if claims.get("iss") != f"https://login.microsoftonline.com/{tid}/v2.0":
            raise SSOError("sso_token_invalid", "Unexpected issuer")
    if claims.get("nonce") != nonce:
        raise SSOError("sso_token_invalid", "Nonce mismatch")
    return claims


async def exchange_code(provider: Provider, code: str, verifier: str, redirect_uri: str, nonce: str) -> dict[str, Any]:
    meta = await discovery(provider)
    tokens = await post_form(meta["token_endpoint"], {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": redirect_uri,
        "client_id": provider.client_id,
        "client_secret": provider.client_secret,
        "code_verifier": verifier,
    })
    id_token = tokens.get("id_token")
    if not id_token:
        raise SSOError("sso_exchange_failed", "No id_token returned")
    claims = await verify_id_token(provider, id_token, nonce)

    email = (claims.get("email") or claims.get("preferred_username") or "").strip().lower()
    if not email or "@" not in email:
        raise SSOError("sso_no_email", "The identity provider did not return an email address")
    # Google and most IdPs say whether the address is verified; trust it only when it is.
    if claims.get("email_verified") is False:
        raise SSOError("sso_email_unverified")
    domains = allowed_domains()
    if domains and email.rsplit("@", 1)[1] not in domains:
        raise SSOError("sso_domain_not_allowed")
    return {"email": email, "name": claims.get("name") or email.split("@")[0], "subject": claims["sub"]}
