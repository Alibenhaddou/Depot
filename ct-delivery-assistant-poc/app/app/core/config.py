from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import field_validator
from typing import Any, Literal


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    atlassian_client_id: str
    atlassian_client_secret: str
    atlassian_redirect_uri: str
    atlassian_scopes: str

    app_secret_key: str

    # Sessions / cookies
    session_max_age_seconds: int = 60 * 60 * 8  # 8h
    cookie_secure: bool = False  # True en prod (HTTPS)
    cookie_samesite: Literal["lax", "strict", "none"] = "lax"  # "lax" ou "none"

    openai_api_key: str | None = None
    openai_model: str = "gpt-4.1-mini"

    env: str = "dev"  # dev / prod
    enable_debug_routes: bool = False
    enable_poc_ui: bool = True

    llm_provider: str = "ollama"
    llm_base_url: str = "http://localhost:11434"
    llm_model: str = "qwen2.5:3b"
    llm_timeout: int = 600

    @field_validator("cookie_samesite", mode="before")
    @classmethod
    def _validate_samesite(cls, v: Any) -> str:
        vv = str(v).strip().lower()
        if vv not in {"lax", "strict", "none"}:
            raise ValueError("cookie_samesite must be one of: lax, strict, none")
        return vv

    @field_validator("cookie_secure")
    @classmethod
    def _validate_cookie_secure(cls, v: bool, info: Any) -> bool:
        # Si SameSite=None => Secure doit être True (exigence navigateur)
        samesite = (info.data.get("cookie_samesite") or "").strip().lower()
        if samesite == "none" and v is not True:
            raise ValueError("cookie_secure must be True when cookie_samesite='none'")
        return v


settings = Settings()  # type: ignore[call-arg]
