from __future__ import annotations

from typing import Optional, Dict
from base64 import b64encode

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
    token: Optional[SecretStr] = None  # DHIS2 Personal Access Token (PAT)

    # pydantic-settings config
    model_config = SettingsConfigDict(
        env_prefix="DHIS2_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Always coerce raw env/CLI strings into SecretStr
    @field_validator("password", "token", mode="before")
    @classmethod
    def _coerce_secret(cls, v):
        if v is None or isinstance(v, SecretStr):
            return v
        return SecretStr(str(v))

    # ---- robust accessors that tolerate str | SecretStr | None
    @staticmethod
    def _reveal(value: Optional[object]) -> Optional[str]:
        if value is None:
            return None
        return value.get_secret_value() if hasattr(value, "get_secret_value") else str(value)

    def password_value(self) -> Optional[str]:
        return self._reveal(self.password)

    def token_value(self) -> Optional[str]:
        return self._reveal(self.token)

    @property
    def auth_header(self) -> Dict[str, str]:
        """
        Build an Authorization header for DHIS2:
        - If a PAT token is provided -> 'Authorization: ApiToken <token>'
        - Else if username/password -> 'Authorization: Basic <base64(user:pass)>'
        - Else -> {}
        """
        tok = self.token_value()
        if tok:
            return {"Authorization": f"ApiToken {tok}"}
        if self.username and self.password_value():
            userpass = f"{self.username}:{self.password_value()}".encode("utf-8")
            return {"Authorization": "Basic " + b64encode(userpass).decode("ascii")}
        return {}
