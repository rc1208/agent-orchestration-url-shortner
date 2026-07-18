from pathlib import Path
from typing import Literal

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="AGENTIC_", env_file=".env", extra="ignore")

    database_path: Path = Path("agentic.db")
    workspace_root: Path = Path("workspace/runs")
    provider: Literal["mock", "openai"] = "mock"
    openai_model: str | None = None
    max_retries: int = Field(default=2, ge=0, le=5)
    test_timeout_seconds: int = Field(default=30, ge=1, le=300)

    @model_validator(mode="after")
    def validate_openai(self) -> "Settings":
        if self.provider == "openai" and not self.openai_model:
            raise ValueError("AGENTIC_OPENAI_MODEL is required when provider=openai")
        return self

