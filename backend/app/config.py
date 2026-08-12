from dataclasses import dataclass
import os


@dataclass(frozen=True, slots=True)
class Settings:
    app_env: str
    frontend_origin: str
    carddav_base_url: str
    carddav_addressbook_home_url: str
    carddav_username: str
    carddav_password: str
    carddav_timeout_seconds: float

    @property
    def carddav_configured(self) -> bool:
        return bool(
            self.carddav_base_url
            and self.carddav_username
            and self.carddav_password
        )


def get_settings() -> Settings:
    return Settings(
        app_env=os.getenv("APP_ENV", "development"),
        frontend_origin=os.getenv("FRONTEND_ORIGIN", "http://localhost:5173"),
        carddav_base_url=os.getenv("CARDDAV_BASE_URL", "").rstrip("/"),
        carddav_addressbook_home_url=os.getenv(
            "CARDDAV_ADDRESSBOOK_HOME_URL", ""
        ).strip(),
        carddav_username=os.getenv("CARDDAV_USERNAME", ""),
        carddav_password=os.getenv("CARDDAV_PASSWORD", ""),
        carddav_timeout_seconds=float(os.getenv("CARDDAV_TIMEOUT_SECONDS", "15")),
    )
