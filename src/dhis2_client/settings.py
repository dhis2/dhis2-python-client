# src/dhis2_client/settings.py
from __future__ import annotations

from typing import Optional

from pydantic import SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # --- connection ---
    base_url: Optional[str] = None
    verify_ssl: bool = True
    timeout: int = 30

    # --- auth ---
    username: Optional[str] = None
    password: Optional[SecretStr] = None
    token: Optional[SecretStr] = None

    # pydantic-settings config
    model_config = SettingsConfigDict(
        env_prefix="DHIS2_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",  # ignore unexpected env vars
    )

    # Always coerce raw env/CLI strings into SecretStr
    @field_validator("password", "token", mode="before")
    @classmethod
    def _coerce_secret(cls, v):
        if v is None or isinstance(v, SecretStr):
            return v
        return SecretStr(str(v))

    # Convenience accessors (optional)
    def password_value(self) -> Optional[str]:
        return self.password.get_secret_value() if self.password else None

    def token_value(self) -> Optional[str]:
        return self.token.get_secret_value() if self.token else None
