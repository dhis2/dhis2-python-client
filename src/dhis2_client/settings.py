from __future__ import annotations

from typing import Dict, Optional

from pydantic import AnyHttpUrl, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration loaded from environment / .env (DHIS2_* prefix)."""

    base_url: AnyHttpUrl
    username: Optional[str] = None
    password: Optional[SecretStr] = None
    token: Optional[SecretStr] = None
    timeout: float = 30.0
    verify_ssl: bool = True

    model_config = SettingsConfigDict(
        env_prefix="DHIS2_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    def auth_header(self) -> Dict[str, str]:
        """Return Authorization header when using token auth (preferred in DHIS2 2.40+)."""
        if self.token is not None:
            return {"Authorization": f"ApiToken {self.token.get_secret_value()}"}
        return {}
