"""
Inbound webhook handlers.

  POST /webhooks/stripe  — Stripe payment events (signature-validated)

Stripe integration is currently a STUB (no live Stripe key required).
When Stripe goes live, set STRIPE_WEBHOOK_SECRET in .env and the
signature validation becomes enforcement-mode.
"""

import json

from fastapi import APIRouter, Header, HTTPException, Request, status
import structlog

from api.config import settings

logger = structlog.get_logger()
router = APIRouter()


@router.post("/stripe", status_code=status.HTTP_200_OK)
async def stripe_webhook(
    request: Request,
    stripe_signature: str = Header(None, alias="stripe-signature"),
):
    """
    Receive Stripe webhook events.

    Validates the `Stripe-Signature` header using the configured
    STRIPE_WEBHOOK_SECRET before processing any event payload.
    Rejects requests that lack a valid signature.
    """
    payload = await request.body()

    webhook_secret = getattr(settings, "STRIPE_WEBHOOK_SECRET", None)

    if webhook_secret:
        # Validate Stripe signature using the Stripe SDK
        try:
            import stripe
            event = stripe.Webhook.construct_event(
                payload, stripe_signature, webhook_secret
            )
        except ValueError:
            logger.warning("stripe_webhook_invalid_payload")
            raise HTTPException(status_code=400, detail="Invalid payload")
        except stripe.error.SignatureVerificationError:
            logger.warning(
                "stripe_webhook_signature_invalid",
                sig_header=stripe_signature,
            )
            raise HTTPException(status_code=400, detail="Invalid signature")
    else:
        # STRIPE_WEBHOOK_SECRET not configured — stub mode (dev/test only)
        if not getattr(settings, "DEBUG", False):
            logger.error("stripe_webhook_secret_not_configured")
            raise HTTPException(
                status_code=503,
                detail="Stripe webhook secret is not configured",
            )
        try:
            event = json.loads(payload)
        except json.JSONDecodeError:
            raise HTTPException(status_code=400, detail="Invalid JSON payload")
        logger.warning("stripe_webhook_stub_mode", event_type=event.get("type"))

    event_type = event.get("type") if isinstance(event, dict) else event.type

    logger.info("stripe_webhook_received", event_type=event_type)

    # Route event types to handlers
    if event_type == "payment_intent.succeeded":
        await _handle_payment_succeeded(event)
    elif event_type == "payment_intent.payment_failed":
        await _handle_payment_failed(event)
    elif event_type == "charge.dispute.created":
        await _handle_dispute_created(event)
    else:
        logger.info("stripe_webhook_unhandled_event", event_type=event_type)

    return {"received": True}


async def _handle_payment_succeeded(event: dict) -> None:
    """STUB: Handle successful payment. Wire to invoice payment confirmation when Stripe goes live."""
    obj = event.get("data", {}).get("object", {}) if isinstance(event, dict) else {}
    logger.info(
        "stripe_payment_succeeded_stub",
        payment_intent_id=obj.get("id"),
        amount=obj.get("amount"),
        currency=obj.get("currency"),
    )


async def _handle_payment_failed(event: dict) -> None:
    """STUB: Handle failed payment."""
    obj = event.get("data", {}).get("object", {}) if isinstance(event, dict) else {}
    logger.warning(
        "stripe_payment_failed_stub",
        payment_intent_id=obj.get("id"),
        last_payment_error=obj.get("last_payment_error"),
    )


async def _handle_dispute_created(event: dict) -> None:
    """STUB: Handle chargeback/dispute creation."""
    obj = event.get("data", {}).get("object", {}) if isinstance(event, dict) else {}
    logger.warning(
        "stripe_dispute_created_stub",
        dispute_id=obj.get("id"),
        amount=obj.get("amount"),
        reason=obj.get("reason"),
    )
