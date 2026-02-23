from pydantic_settings import BaseSettings
from functools import lru_cache
from typing import Optional


class Settings(BaseSettings):
    APP_NAME: str = "SVPMS"
    APP_VERSION: str = "1.0.0"
    ENVIRONMENT: str = "development"
    DEBUG: bool = False
    LOG_LEVEL: str = "INFO"
    PORT: int = 8000

    DATABASE_URL: str = ""
    DATABASE_SYNC_URL: str = ""
    DB_POOL_SIZE: int = 5
    DB_MAX_OVERFLOW: int = 5
    DB_POOL_RECYCLE: int = 300

    UPSTASH_REDIS_REST_URL: str = ""
    UPSTASH_REDIS_REST_TOKEN: str = ""

    R2_ACCOUNT_ID: str = ""
    R2_ACCESS_KEY_ID: str = ""
    R2_SECRET_ACCESS_KEY: str = ""
    R2_BUCKET_NAME: str = "svpms-documents"
    R2_ENDPOINT_URL: str = ""

    JWT_PRIVATE_KEY_PATH: Optional[str] = "keys/private.pem"
    JWT_PUBLIC_KEY_PATH: Optional[str] = "keys/public.pem"
    JWT_ALGORITHM: str = "RS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    ENCRYPTION_KEY: str = ""

    FIREBASE_CREDENTIALS_PATH: Optional[str] = None
    FIREBASE_PROJECT_ID: Optional[str] = None
    GCP_PROJECT_ID: str = ""
    DOCUMENT_AI_PROCESSOR: Optional[str] = None
    USE_SECRET_MANAGER: bool = False

    BREVO_API_KEY: Optional[str] = None
    EMAIL_FROM_ADDRESS: str = "noreply@svpms.example.com"
    STRIPE_SECRET_KEY: Optional[str] = None
    STRIPE_WEBHOOK_SECRET: Optional[str] = None
    INTERNAL_JOB_SECRET: Optional[str] = None  # Required in production for /internal/jobs/* auth
    CORS_ORIGINS: str = "http://localhost:3000"
    CORS_ORIGIN_REGEX: Optional[str] = None

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",")]

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT == "production"

    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "ignore"


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
