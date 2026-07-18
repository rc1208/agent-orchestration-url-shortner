from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, HttpUrl


class CreateUrlRequest(BaseModel):
    model_config = ConfigDict(alias_generator=lambda value: "".join(
        word.capitalize() if index else word for index, word in enumerate(value.split("_"))
    ), populate_by_name=True)
    url: HttpUrl
    custom_alias: str | None = Field(None, min_length=3, max_length=32, pattern=r"^[A-Za-z0-9_-]+$")
    expires_at: datetime | None = None


class UrlResponse(BaseModel):
    shortCode: str
    originalUrl: str
    shortUrl: str
    createdAt: datetime
    expiresAt: datetime | None
    redirectCount: int
    lastAccessedAt: datetime | None
    isActive: bool


class AnalyticsResponse(BaseModel):
    shortCode: str
    redirectCount: int
    lastAccessedAt: datetime | None
    createdAt: datetime
    expiresAt: datetime | None


class CreateRunRequest(BaseModel):
    requirement: str = Field(min_length=5, max_length=12_000)
    scenario: str = Field(pattern=r"^(greenfield|brownfield|ambiguous)$")


class ApprovalRequest(BaseModel):
    action: str = Field(pattern=r"^(apply_code|rollback|release)$")
    approved: bool
    actor: str = Field(default="reviewer", min_length=1, max_length=80)


class ResumeRequest(BaseModel):
    clarification: str = Field(min_length=3, max_length=4_000)
