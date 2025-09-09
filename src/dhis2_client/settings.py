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

    model_config = SettingsConfigDict(
        env_prefix="DHIS2_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @field_validator("password", "token", mode="before")
    @classmethod
    def _coerce_secret(cls, v):
        if v is None or isinstance(v, SecretStr):
            return v
        return SecretStr(str(v))

    # --- convenience accessors
    def password_value(self) -> Optional[str]:
        return self.password.get_secret_value() if self.password else None

    def token_value(self) -> Optional[str]:
        return self.token.get_secret_value() if self.token else None

    @property
    def auth_header(self) -> Dict[str, str]:
        """
        Build an Authorization header for DHIS2:
        - If a PAT token is provided -> 'Authorization: ApiToken <token>'
        - Else if username/password -> 'Authorization: Basic <base64(user:pass)>'
        - Else -> empty dict
        """
        tok = self.token_value()
        if tok:
            # DHIS2 Personal Access Token format
            # Ref: DHIS2 docs — Authorization: ApiToken <token>
            return {"Authorization": f"ApiToken {tok}"}

        user = self.username
        pwd = self.password_value()
        if user and pwd:
            userpass = f"{user}:{pwd}".encode("utf-8")
            return {"Authorization": "Basic " + b64encode(userpass).decode("ascii")}

        return {}
