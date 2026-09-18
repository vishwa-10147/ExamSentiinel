import uuid
import logging
from typing import Optional
from fastapi import APIRouter, Depends, Header, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
import stripe

from app.core.config import settings
from app.core.database import get_db
from app.models.institution import Institution

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webhooks", tags=["Webhooks"])

# Initialize stripe API key if available
if hasattr(settings, "STRIPE_SECRET_KEY") and settings.STRIPE_SECRET_KEY:
    stripe.api_key = settings.STRIPE_SECRET_KEY

@router.post("/stripe")
async def stripe_webhook(
    request: Request,
    stripe_signature: str = Header(None),
    db: AsyncSession = Depends(get_db)
):
    """
    Stripe Webhook Endpoint
    Listens for subscription updates to automatically upgrade/downgrade institutions.
    """
    if not hasattr(settings, "STRIPE_WEBHOOK_SECRET") or not settings.STRIPE_WEBHOOK_SECRET:
        logger.warning("Stripe webhook received but STRIPE_WEBHOOK_SECRET is not configured.")
        return {"status": "ignored", "reason": "stripe_not_configured"}

    payload = await request.body()

    try:
        event = stripe.Webhook.construct_event(
            payload, stripe_signature, settings.STRIPE_WEBHOOK_SECRET
        )
    except ValueError as e:
        # Invalid payload
        raise HTTPException(status_code=400, detail="Invalid payload")
    except stripe.error.SignatureVerificationError as e:
        # Invalid signature
        raise HTTPException(status_code=400, detail="Invalid signature")

    # Handle the event
    if event['type'] == 'customer.subscription.created' or event['type'] == 'customer.subscription.updated':
        subscription = event['data']['object']
        customer_id = subscription.get('customer')
        status = subscription.get('status') # active, past_due, canceled, etc.
        
        # Get the product ID to determine the tier (in a real app, this maps to your plans)
        # Assuming metadata contains the tier name for simplicity, or we default to PRO
        tier_name = subscription.get('metadata', {}).get('tier', 'pro').lower()

        # Update institution
        result = await db.execute(select(Institution).where(Institution.stripe_customer_id == customer_id))
        institution = result.scalar_one_or_none()
        
        if institution:
            institution.subscription_status = status
            if status == 'active':
                institution.subscription_tier = tier_name
            elif status in ['canceled', 'unpaid']:
                institution.subscription_tier = 'free'
            
            await db.commit()
            logger.info(f"Updated institution {institution.id} tier to {institution.subscription_tier} via Stripe Webhook")
        else:
            logger.warning(f"Stripe Webhook: Could not find institution with customer_id {customer_id}")

    elif event['type'] == 'customer.subscription.deleted':
        subscription = event['data']['object']
        customer_id = subscription.get('customer')
        
        result = await db.execute(select(Institution).where(Institution.stripe_customer_id == customer_id))
        institution = result.scalar_one_or_none()
        
        if institution:
            institution.subscription_status = 'canceled'
            institution.subscription_tier = 'free'
            await db.commit()
            logger.info(f"Institution {institution.id} subscription canceled via Stripe Webhook")

    return {"status": "success"}
