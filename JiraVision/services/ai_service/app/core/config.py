from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import field_validator
from typing import Any, Literal


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    openai_api_key: str | None = None
    openai_model: str = "gpt-4.1-mini"

    llm_provider: str = "ollama"
    llm_base_url: str = "http://localhost:11434"
    llm_model: str = "qwen2.5:3b"
    llm_timeout: int = 600


settings = Settings()  # type: ignore[call-arg]
