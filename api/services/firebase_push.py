import firebase_admin
from firebase_admin import credentials
from api.config import settings
from api.services.secrets import get_secret
import json
import structlog

logger = structlog.get_logger()
_initialized = False


def init_firebase():
    """Called once at startup from main.py lifespan."""
    global _initialized
    if _initialized:
        return
    try:
        if settings.USE_SECRET_MANAGER:
            cred = credentials.Certificate(
                json.loads(get_secret("firebase-service-account-json"))
            )
        elif settings.FIREBASE_CREDENTIALS_PATH:
            cred = credentials.Certificate(settings.FIREBASE_CREDENTIALS_PATH)
        else:
            logger.warning("firebase_not_configured")
            return
        firebase_admin.initialize_app(cred)
        _initialized = True
        logger.info("firebase_initialized")
    except Exception as e:
        logger.error("firebase_init_failed", error=str(e))
