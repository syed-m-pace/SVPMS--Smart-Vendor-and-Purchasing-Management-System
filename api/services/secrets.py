from google.cloud import secretmanager
from functools import lru_cache
from api.config import settings

_client = None


def _get_client():
    global _client
    if _client is None:
        _client = secretmanager.SecretManagerServiceClient()
    return _client


@lru_cache(maxsize=20)
def get_secret(secret_id: str) -> str:
    """Secrets: jwt-private-key, jwt-public-key, encryption-key, neon-database-url,
    upstash-redis-token, brevo-api-key, stripe-secret-key, r2-secret-key,
    firebase-service-account-json"""
    client = _get_client()
    name = f"projects/{settings.GCP_PROJECT_ID}/secrets/{secret_id}/versions/latest"
    return client.access_secret_version(name=name).payload.data.decode("UTF-8")


def load_production_secrets():
    import os

    if not settings.USE_SECRET_MANAGER:
        return
    os.environ["DATABASE_URL"] = get_secret("neon-database-url")
    os.environ["DATABASE_SYNC_URL"] = get_secret("neon-database-sync-url")
    os.environ["UPSTASH_REDIS_REST_TOKEN"] = get_secret("upstash-redis-token")
    os.environ["BREVO_API_KEY"] = get_secret("brevo-api-key")
    os.environ["STRIPE_SECRET_KEY"] = get_secret("stripe-secret-key")
    os.environ["ENCRYPTION_KEY"] = get_secret("encryption-key")
