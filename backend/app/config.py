from pathlib import Path

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from .security import configured_frontend_origin, normalize_origin


_ROOT_ENV = Path(__file__).resolve().parents[2] / ".env"


class Settings(BaseSettings):
    app_env: str = "development"
    frontend_origin: str = "http://localhost:5173"
    carddav_base_url: str = ""
    carddav_timeout_seconds: float = 15.0
    carddav_write_enabled: bool = False
    session_ttl_seconds: int = 28_800
    session_cookie_name: str = "goreecloud_contacts_session"
    session_cookie_secure: bool = False
    csrf_origin_check_enabled: bool = False

    model_config = SettingsConfigDict(
        env_file=_ROOT_ENV,
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @property
    def carddav_configured(self) -> bool:
        return bool(self.carddav_base_url.strip())

    @model_validator(mode="after")
    def validate_security_boundaries(self) -> "Settings":
        frontend_origin = configured_frontend_origin(self.frontend_origin)
        if frontend_origin is None:
            raise ValueError(
                "FRONTEND_ORIGIN must be one HTTP(S) origin without a path, query, or fragment."
            )

        if self.app_env.strip().casefold() != "production":
            return self

        if not self.session_cookie_secure:
            raise ValueError("Production requires SESSION_COOKIE_SECURE=true.")
        if not self.csrf_origin_check_enabled:
            raise ValueError("Production requires CSRF_ORIGIN_CHECK_ENABLED=true.")
        if not frontend_origin.startswith("https://"):
            raise ValueError("Production requires an HTTPS FRONTEND_ORIGIN.")
        if not self.carddav_configured:
            raise ValueError("Production requires CARDDAV_BASE_URL to be configured.")

        carddav_origin = normalize_origin(self.carddav_base_url)
        if carddav_origin is None or not carddav_origin.startswith("https://"):
            raise ValueError("Production requires an HTTPS CARDDAV_BASE_URL.")

        return self


def get_settings() -> Settings:
    return Settings()
