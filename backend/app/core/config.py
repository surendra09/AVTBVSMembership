"""Application configuration loaded from environment variables.

Nothing secret is hard-coded here: every credential must come from the
environment (or a .env file that is never committed).
"""
from functools import lru_cache
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # --- General -----------------------------------------------------------
    APP_NAME: str = "AVTBVS Membership"
    ENVIRONMENT: Literal["development", "test", "production"] = "development"
    DEBUG: bool = False
    PUBLIC_APP_URL: str = "http://localhost:5173"  # used in email links
    API_PREFIX: str = "/api"

    # --- Organisation details (from the official form; configurable) -------
    ORG_FULL_NAME: str = "Ayira Vaisyar Telugu Beri Vysya Sabha"
    ORG_ABBREVIATION: str = "AVTBVS"
    ORG_TELUGU_NAME: str = "ఆయిర వైశ్యర్ తెలుగు బేరి వైశ్య సభ"
    ORG_FORMERLY_KNOWN_AS: str = "Telugu Beri Vysya Kulabhimana Sabha"
    ORG_REGISTRATION: str = "Regd. No. 101/1955"
    ORG_ADDRESS: str = "28, (Old No. 4), Kalappachari Street, Park Town, Chennai - 600 003"
    ORG_PHONE: str = "044-25330821"
    ORG_EMAIL: str = "avtbvsabha.1955@gmail.com"
    ORG_COMMUNITY_NAME: str = "Ayira Vaisyar Telugu Beri Vysya Chetty Community"

    # --- Database ----------------------------------------------------------
    DATABASE_URL: str = "mysql+pymysql://avtbvs:devpassword@127.0.0.1:3306/avtbvs?charset=utf8mb4"
    DB_POOL_SIZE: int = 10
    DB_ECHO: bool = False

    # --- Security ----------------------------------------------------------
    SECRET_KEY: str = Field(default="dev-insecure-change-me-0123456789abcdef", min_length=32)
    # Fernet key (urlsafe base64, 32 bytes) used to encrypt Aadhaar numbers.
    DATA_ENCRYPTION_KEY: str = "ZGV2LW9ubHktZGF0YS1rZXktY2hhbmdlLW1lLTEyMzQ="
    # Separate key for deterministic lookup hashes (HMAC) of Aadhaar numbers.
    DATA_HASH_KEY: str = "dev-only-hash-key-change-me"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    JWT_ALGORITHM: str = "HS256"
    COOKIE_SECURE: bool = False  # MUST be true in production (HTTPS)
    COOKIE_SAMESITE: Literal["lax", "strict", "none"] = "lax"
    COOKIE_DOMAIN: str | None = None
    CORS_ORIGINS: str = "http://localhost:5173"
    OTP_EXPIRE_MINUTES: int = 10
    OTP_MAX_ATTEMPTS: int = 5
    PASSWORD_RESET_EXPIRE_MINUTES: int = 30
    ADMIN_INVITE_EXPIRE_HOURS: int = 48

    # --- Rate limiting -----------------------------------------------------
    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_LOGIN: str = "10/300"  # requests/seconds per IP+identifier
    RATE_LIMIT_OTP: str = "5/600"
    RATE_LIMIT_PASSWORD_RESET: str = "5/900"
    RATE_LIMIT_REGISTER: str = "10/3600"

    # --- Membership business rules ----------------------------------------
    MINIMUM_AGE_YEARS: int = 18
    EDIT_PERMISSION_HOURS: int = 24
    # Membership number format. Placeholders: {seq}, {year}, {yy}, {prefix}.
    # Python format spec is allowed, e.g. "{prefix}{seq:05d}".
    # The organisation's real format MUST be configured before go-live.
    MEMBERSHIP_NUMBER_TEMPLATE: str = "{seq}"
    MEMBERSHIP_NUMBER_PREFIX: str = ""
    MEMBERSHIP_SEQUENCE_START: int = 1
    MEMBERSHIP_SEQUENCE_PER_YEAR: bool = False
    APPLICATION_NUMBER_PREFIX: str = "APP"
    REQUIRE_INTRODUCER_SIGNATURE: bool = False
    INTRODUCER_MUST_BE_REGISTERED: bool = False
    REQUIRE_VERIFIED_CONTACT_FOR_SUBMISSION: bool = True

    # --- File storage ------------------------------------------------------
    PRIVATE_STORAGE_DIR: str = "./storage/private"
    MAX_PHOTO_BYTES: int = 2 * 1024 * 1024
    MAX_DOCUMENT_BYTES: int = 5 * 1024 * 1024

    # --- Notifications -----------------------------------------------------
    EMAIL_PROVIDER: Literal["console", "smtp"] = "console"
    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USERNAME: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_USE_TLS: bool = True
    SMTP_USE_SSL: bool = False
    EMAIL_FROM: str = "AVTBVS Membership <no-reply@example.org>"

    SMS_PROVIDER: Literal["console", "twilio", "msg91"] = "console"
    TWILIO_ACCOUNT_SID: str = ""
    TWILIO_AUTH_TOKEN: str = ""
    TWILIO_FROM_NUMBER: str = ""
    MSG91_AUTH_KEY: str = ""
    MSG91_SENDER_ID: str = ""
    MSG91_FLOW_ID: str = ""
    SMS_DEFAULT_COUNTRY_CODE: str = "+91"

    NOTIFICATION_WORKER_ENABLED: bool = True  # in-process background worker
    NOTIFICATION_WORKER_INTERVAL_SECONDS: int = 5
    NOTIFICATION_MAX_ATTEMPTS: int = 5
    CONSOLE_OUTBOX_FILE: str = "./storage/outbox.log"  # dev-mode delivery log

    @field_validator("CORS_ORIGINS")
    @classmethod
    def _strip(cls, v: str) -> str:
        return v.strip()

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT == "production"

    def validate_production(self) -> list[str]:
        """Return a list of configuration problems that must block production start."""
        problems = []
        if "dev-" in self.SECRET_KEY or len(self.SECRET_KEY) < 48:
            problems.append("SECRET_KEY must be a long random value")
        if self.DATA_ENCRYPTION_KEY.startswith("ZGV2"):
            problems.append("DATA_ENCRYPTION_KEY must be a freshly generated Fernet key")
        if self.DATA_HASH_KEY.startswith("dev-"):
            problems.append("DATA_HASH_KEY must be a long random value")
        if not self.COOKIE_SECURE:
            problems.append("COOKIE_SECURE must be true (HTTPS) in production")
        if "devpassword" in self.DATABASE_URL:
            problems.append("DATABASE_URL uses the development password")
        return problems


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
