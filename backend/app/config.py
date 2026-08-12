from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


_ROOT_ENV = Path(__file__).resolve().parents[2] / ".env"


class Settings(BaseSettings):
    app_env: str = "development"
    frontend_origin: str = "http://localhost:5173"
    carddav_base_url: str = ""
    carddav_addressbook_home_url: str = ""
    carddav_username: str = ""
    carddav_password: str = ""
    carddav_timeout_seconds: float = 15.0

    model_config = SettingsConfigDict(
        env_file=_ROOT_ENV,
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @property
    def carddav_configured(self) -> bool:
        return bool(
            self.carddav_base_url.strip()
            and self.carddav_username
            and self.carddav_password
        )


def get_settings() -> Settings:
    return Settings()
