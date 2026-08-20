from pathlib import Path
from typing import Literal

from pydantic import SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from .security import configured_frontend_origin, normalize_origin


_ROOT_ENV = Path(__file__).resolve().parents[2] / ".env"
AppEnvironment = Literal["development", "test", "production"]


def fastapi_documentation_options(enabled: bool) -> dict[str, str | None]:
    """Return explicit FastAPI documentation routes for the selected environment."""

    return {
        "docs_url": "/docs" if enabled else None,
        "redoc_url": "/redoc" if enabled else None,
        "openapi_url": "/openapi.json" if enabled else None,
    }


class Settings(BaseSettings):
    app_env: AppEnvironment = "development"
    frontend_origin: str = "http://localhost:5173"
    carddav_base_url: str = ""
    carddav_timeout_seconds: float = 15.0
    carddav_write_enabled: bool = False
    duplicate_merge_enabled: bool = False
    session_ttl_seconds: int = 28_800
    session_cookie_name: str = "goreecloud_contacts_session"
    session_cookie_secure: bool = False
    session_store_backend: Literal["memory", "sqlite"] = "memory"
    session_db_path: str = "/data/sessions.sqlite3"
    session_encryption_keys: SecretStr = SecretStr("")
    session_encryption_keys_file: str = ""
    csrf_origin_check_enabled: bool = False
    login_throttle_max_attempts: int = 8
    login_throttle_window_seconds: int = 300

    model_config = SettingsConfigDict(
        env_file=_ROOT_ENV,
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @field_validator("app_env", mode="before")
    @classmethod
    def normalize_app_environment(cls, value: object) -> object:
        if isinstance(value, str):
            return value.strip().casefold()
        return value

    @field_validator("login_throttle_max_attempts", "login_throttle_window_seconds")
    @classmethod
    def validate_positive_security_limits(cls, value: int) -> int:
        if value < 1:
            raise ValueError("login throttle limits must be positive integers.")
        return value

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"

    @property
    def api_documentation_enabled(self) -> bool:
        return not self.is_production

    @property
    def carddav_configured(self) -> bool:
        return bool(self.carddav_base_url.strip())

    @property
    def session_encryption_key_list(self) -> list[str]:
        inline_value = self.session_encryption_keys.get_secret_value().strip()
        file_value = self.session_encryption_keys_file.strip()

        if inline_value and file_value:
            raise ValueError(
                "Configure only one of SESSION_ENCRYPTION_KEYS or SESSION_ENCRYPTION_KEYS_FILE."
            )

        raw_value = inline_value
        if file_value:
            secret_path = Path(file_value).expanduser()
            if not secret_path.is_absolute():
                raise ValueError("SESSION_ENCRYPTION_KEYS_FILE must be an absolute path.")
            try:
                raw_value = secret_path.read_text(encoding="utf-8").strip()
            except OSError as exc:
                raise ValueError(
                    "SESSION_ENCRYPTION_KEYS_FILE must reference a readable secret file."
                ) from exc

        return [value.strip() for value in raw_value.split(",") if value.strip()]

    @model_validator(mode="after")
    def validate_security_boundaries(self) -> "Settings":
        frontend_origin = configured_frontend_origin(self.frontend_origin)
        if frontend_origin is None:
            raise ValueError(
                "FRONTEND_ORIGIN must be one HTTP(S) origin without a path, query, or fragment."
            )
        self.frontend_origin = frontend_origin

        inline_keys = self.session_encryption_keys.get_secret_value().strip()
        key_file = self.session_encryption_keys_file.strip()
        if inline_keys and key_file:
            raise ValueError(
                "Configure only one of SESSION_ENCRYPTION_KEYS or SESSION_ENCRYPTION_KEYS_FILE."
            )
        if key_file and not Path(key_file).expanduser().is_absolute():
            raise ValueError("SESSION_ENCRYPTION_KEYS_FILE must be an absolute path.")

        if not self.is_production:
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

        if self.session_store_backend != "sqlite":
            raise ValueError("Production requires SESSION_STORE_BACKEND=sqlite.")
        if not self.session_encryption_key_list:
            raise ValueError(
                "Production requires SESSION_ENCRYPTION_KEYS or SESSION_ENCRYPTION_KEYS_FILE."
            )
        if not Path(self.session_db_path).expanduser().is_absolute():
            raise ValueError("Production requires SESSION_DB_PATH to be an absolute path.")

        return self


def get_settings() -> Settings:
    return Settings()
