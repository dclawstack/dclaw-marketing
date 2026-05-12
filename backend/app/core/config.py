from functools import lru_cache

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # App identity
    app_name: str = "DClaw Marketing"
    app_env: str = "dev"
    debug: bool = True

    # Database
    database_url: str = (
        "postgresql+asyncpg://postgres:postgres@localhost:5432/dclaw_marketing"
    )

    # Redis (A2 worker, caching)
    redis_url: str = "redis://localhost:6379/0"

    # Auth — JWT lifetime + signing secret used by FastAPI-Users
    jwt_secret: str = "change-me-jwt-secret-set-in-env"
    jwt_lifetime_seconds: int = 3600  # 1h access token
    refresh_token_lifetime_seconds: int = 60 * 60 * 24 * 14  # 14d refresh token

    # Legacy single secret (kept for any non-FastAPI-Users primitives).
    secret_key: str = "change-me-in-production"
    access_token_expire_minutes: int = 60

    # Tenant secrets encryption — master key for Fernet-encrypted per-Org
    # OAuth tokens. Set via env in prod; default here is dev only.
    tenant_encryption_master_key: str = "change-me-fernet-master-key-base64=="

    # Object storage (S3 / MinIO / R2)
    s3_endpoint: str = "http://localhost:9000"
    s3_region: str = "us-east-1"
    s3_access_key: str = "minioadmin"
    s3_secret_key: str = "minioadmin"
    s3_bucket: str = "dclaw-marketing"
    s3_use_ssl: bool = False

    # Email — multi-provider (Phase 7.4)
    # Send-priority order tries: SendGrid → Postmark → Resend → stub.
    # First provider with a non-empty key wins; on transport error
    # we fall through to the next, then to the stub.
    sendgrid_api_key: str = ""
    postmark_api_key: str = ""
    resend_api_key: str = ""
    resend_from_email: str = "DClaw Marketing <noreply@dclaw.io>"

    # Email-event webhook ingest (Phase 7.4) — per-provider secrets used
    # to verify inbound webhook signatures. When a secret is empty the
    # endpoint accepts unverified payloads with a warning log (dev mode).
    resend_webhook_secret: str = ""
    postmark_webhook_secret: str = ""
    sendgrid_webhook_verify: bool = False  # ECDSA verify ships with OAuth flow

    # Newsletters (Phase 7.5+)
    # mailchimp_server_prefix is the data-centre suffix on the API key
    # (e.g. "abc123-us21" → "us21"). Both must be set for real sends.
    mailchimp_api_key: str = ""
    mailchimp_server_prefix: str = ""
    convertkit_api_secret: str = ""
    beehiiv_api_key: str = ""
    beehiiv_publication_id: str = ""

    # CRM sync — Salesforce (Phase 8.7). Both required for real calls.
    salesforce_access_token: str = ""
    salesforce_instance_url: str = ""

    # CRM sync (Phase 8.6+) — HubSpot first.
    hubspot_access_token: str = ""

    # CRM sync — Pipedrive (Phase 8.x). Pipedrive uses an api_token
    # query-param rather than OAuth bearer.
    pipedrive_api_token: str = ""

    # CRM sync — Attio (Phase 8.x). Standard OAuth bearer token.
    attio_access_token: str = ""

    # Billing — Stripe (Phase 10.6)
    stripe_secret_key: str = ""

    # Billing — QuickBooks Online (Phase 10.7). access_token rotates
    # hourly; realm_id is the company id. Both required for real calls.
    quickbooks_access_token: str = ""
    quickbooks_realm_id: str = ""

    # Ads — Meta (Facebook + Instagram). Phase 7.x.
    # The access_token is an ad-account-scoped token, not a user token.
    meta_ads_access_token: str = ""
    meta_ads_account_id: str = ""  # numeric id, no "act_" prefix

    # Ads — LinkedIn Marketing Developer Platform. Phase 7.x.
    linkedin_ads_access_token: str = ""
    linkedin_ads_account_id: str = ""  # numeric sponsored-account id

    # LLM providers
    anthropic_api_key: str = ""
    openai_api_key: str = ""  # for embeddings

    # Image generation providers (Phase 3.1)
    replicate_api_token: str = ""
    replicate_image_model: str = (
        "stability-ai/sdxl:39ed52f2a78e934b3ba6e2a89f5b1c712de7dfea535525255b1aa35c5565e08b"
    )

    # Multimodal asset generation (Phase 3.3) — video / voice / music.
    # Version hashes must be set explicitly; otherwise the adapters
    # fall back to deterministic stubs.
    replicate_video_model: str = ""
    replicate_music_model: str = ""
    elevenlabs_api_key: str = ""
    elevenlabs_default_voice: str = "21m00Tcm4TlvDq8ikWAM"  # "Rachel"

    # Mastodon (Phase 5.5) — default instance URL. Each SocialAccount
    # can override via auth_metadata_json["instance_url"].
    mastodon_default_instance: str = "https://mastodon.social"

    # Admin bootstrap — created on first run if no admin user exists
    bootstrap_admin_email: str = "admin@dclaw.io"
    bootstrap_admin_temp_password: str = "ChangeMeOnFirstLogin!"

    # Legacy AI fields (kept for backwards-compat; removed in Phase 2)
    ollama_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.1"
    openrouter_api_key: str = ""
    openrouter_model: str = "meta-llama/llama-3.1-8b-instruct"

    class Config:
        env_file = ".env"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
