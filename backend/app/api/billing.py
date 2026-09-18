import uuid
from typing import Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
import stripe

from app.core.config import settings
from app.core.database import get_db
from app.models.user import User, UserRole
from app.models.institution import Institution
from app.api.deps import get_current_user, require_roles

router = APIRouter(prefix="/billing", tags=["Billing"])

if hasattr(settings, "STRIPE_SECRET_KEY") and settings.STRIPE_SECRET_KEY:
    stripe.api_key = settings.STRIPE_SECRET_KEY

# In a real application, you would map these to actual Stripe Price IDs
STRIPE_PRICES = {
    "pro": "price_pro_placeholder",
    "enterprise": "price_enterprise_placeholder"
}

@router.post("/create-checkout-session")
async def create_checkout_session(
    tier: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles([UserRole.ADMIN]))
):
    """
    Creates a Stripe Checkout Session for upgrading an Institution's subscription.
    Only Admins can trigger billing upgrades.
    """
    if not hasattr(settings, "STRIPE_SECRET_KEY") or not settings.STRIPE_SECRET_KEY:
        raise HTTPException(status_code=503, detail="Stripe is not configured on this server.")

    if tier.lower() not in STRIPE_PRICES:
        raise HTTPException(status_code=400, detail="Invalid subscription tier selected.")

    # Get institution
    result = await db.execute(select(Institution).where(Institution.id == current_user.institution_id))
    institution = result.scalar_one_or_none()
    
    if not institution:
        raise HTTPException(status_code=404, detail="Institution not found")

    try:
        # Create Stripe Checkout Session
        checkout_session = stripe.checkout.Session.create(
            customer=institution.stripe_customer_id if institution.stripe_customer_id else None,
            customer_email=current_user.email if not institution.stripe_customer_id else None,
            payment_method_types=['card'],
            line_items=[
                {
                    'price': STRIPE_PRICES[tier.lower()],
                    'quantity': 1,
                },
            ],
            mode='subscription',
            success_url=f"{settings.FRONTEND_URL}/admin/billing?success=true&session_id={{CHECKOUT_SESSION_ID}}",
            cancel_url=f"{settings.FRONTEND_URL}/admin/billing?canceled=true",
            metadata={
                "institution_id": str(institution.id),
                "tier": tier.lower()
            }
        )
        return {"url": checkout_session.url}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
