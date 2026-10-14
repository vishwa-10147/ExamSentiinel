"""Single sign-on routes (OpenID Connect). See app/services/sso_service.py for configuration.

Browser flow:
  1. SPA links to  GET /api/auth/sso/{provider}/login      → 302 to the provider (state in an HttpOnly cookie)
  2. Provider calls GET /api/auth/sso/{provider}/callback  → verify, find the user, 302 to
     {FRONTEND_URL}/auth/sso-callback?ticket=…              (single-use, 60 s; never a token in a URL)
  3. SPA calls      POST /api/auth/sso/exchange {ticket}    → the same token response as password login
"""

import os
import secrets
import uuid
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import issue_login_session
from app.api.deps import RateLimiter, log_audit_event
from app.core.config import settings
from app.core.database import get_db
from app.core.logging import logger
from app.core.security import get_password_hash
from app.models.user import User, UserRole
from app.schemas.auth import TokenResponse
from app.services import sso_service
from app.services.otp_store import sso_tickets
from app.services.sso_service import SSOError

router = APIRouter(prefix="/auth/sso", tags=["Single Sign-On"])
STATE_COOKIE = "es_sso_state"


class SSOExchangeRequest(BaseModel):
    ticket: str = Field(min_length=16, max_length=128)


def _redirect_uri(request: Request, provider_id: str) -> str:
    base = os.getenv("PUBLIC_API_URL", "").rstrip("/") or str(request.base_url).rstrip("/")
    return f"{base}/api/auth/sso/{provider_id}/callback"


def _to_frontend(path: str, **params: str) -> RedirectResponse:
    response = RedirectResponse(f"{sso_service.frontend_url()}{path}?{urlencode(params)}", status_code=status.HTTP_302_FOUND)
    response.delete_cookie(STATE_COOKIE, path="/api/auth/sso")
    return response


@router.get("/providers")
async def list_providers():
    """Configured providers, for rendering sign-in buttons."""
    return [{"id": p.id, "name": p.name} for p in sso_service.configured_providers().values()]


@router.get("/{provider_id}/login", dependencies=[Depends(RateLimiter(calls=20, period=60))])
async def sso_login(provider_id: str, request: Request):
    try:
        provider = sso_service.get_provider(provider_id)
        flow = sso_service.new_flow_state(provider_id)
        url = await sso_service.authorization_url(provider, flow, _redirect_uri(request, provider_id))
    except SSOError as exc:
        return _to_frontend("/auth/login", error=exc.code)
    except Exception as exc:  # discovery document unreachable, etc.
        logger.error("sso.login_failed", provider=provider_id, error=str(exc))
        return _to_frontend("/auth/login", error="sso_unavailable")

    response = RedirectResponse(url, status_code=status.HTTP_302_FOUND)
    response.set_cookie(
        STATE_COOKIE,
        sso_service.seal_state(flow),
        max_age=sso_service.STATE_TTL_SECONDS,
        httponly=True,
        secure=settings.ENVIRONMENT.lower() == "production",
        samesite="lax",  # sent on the provider's top-level redirect back to us
        path="/api/auth/sso",
    )
    return response


@router.get("/{provider_id}/callback")
async def sso_callback(provider_id: str, request: Request, db: AsyncSession = Depends(get_db)):
    params = request.query_params
    if params.get("error"):
        # User cancelled or the provider refused.
        return _to_frontend("/auth/login", error="sso_cancelled")
    try:
        flow = sso_service.open_state(request.cookies.get(STATE_COOKIE))
        if flow["provider"] != provider_id or not secrets.compare_digest(flow["state"], params.get("state", "")):
            raise SSOError("sso_state_invalid", "State mismatch")
        provider = sso_service.get_provider(provider_id)
        identity = await sso_service.exchange_code(
            provider, params.get("code", ""), flow["verifier"], _redirect_uri(request, provider_id), flow["nonce"]
        )
        user = (await db.execute(select(User).where(User.email == identity["email"]))).scalar_one_or_none()
        if user is None:
            if not sso_service.auto_provision():
                raise SSOError("sso_no_account", f"No account for {identity['email']}")
            user = User(
                email=identity["email"],
                full_name=identity["name"][:255],
                # Unusable random password: this account signs in through SSO
                # (or via password reset, which proves control of the mailbox).
                hashed_password=get_password_hash(secrets.token_urlsafe(32)),
                role=UserRole.CANDIDATE,
                is_active=True,
                is_verified=True,
            )
            db.add(user)
            await db.flush()
            await log_audit_event(db=db, action="USER_PROVISIONED_BY_SSO", resource_type="user", resource_id=str(user.id),
                                  details={"email": user.email, "provider": provider_id}, user_id=user.id,
                                  institution_id=None, request=request)
        if not user.is_active:
            raise SSOError("sso_account_inactive")
        await db.commit()
        ticket = await sso_tickets.issue(f"{user.id}|{provider_id}")
        return _to_frontend("/auth/sso-callback", ticket=ticket)
    except SSOError as exc:
        logger.warning("sso.callback_rejected", provider=provider_id, code=exc.code, detail=str(exc))
        await log_audit_event(db=db, action="SSO_LOGIN_FAILED", resource_type="auth", resource_id=provider_id,
                              details={"reason": exc.code}, user_id=None, institution_id=None, request=request)
        await db.commit()
        return _to_frontend("/auth/login", error=exc.code)
    except Exception as exc:
        logger.error("sso.callback_failed", provider=provider_id, error=str(exc))
        return _to_frontend("/auth/login", error="sso_failed")


@router.post("/exchange", response_model=TokenResponse, dependencies=[Depends(RateLimiter(calls=20, period=60))])
async def sso_exchange(payload: SSOExchangeRequest, request: Request, db: AsyncSession = Depends(get_db)):
    """Trade the single-use ticket from the callback redirect for a normal login session."""
    value = await sso_tickets.redeem(payload.ticket)
    if not value:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Sign-in link expired or already used")
    user_id, provider_id = value.split("|", 1)
    user = await db.get(User, uuid.UUID(user_id))
    if user is None or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Account unavailable")
    return await issue_login_session(db, user, request, method=f"sso:{provider_id}")
