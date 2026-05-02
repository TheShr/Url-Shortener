from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import AnyHttpUrl, BaseModel, Field, field_validator


# ── Request schemas ────────────────────────────────────────────────────────────

class ShortenRequest(BaseModel):
    url: AnyHttpUrl = Field(..., description="The URL to shorten")
    custom_alias: Optional[str] = Field(
        None,
        min_length=3,
        max_length=32,
        pattern=r"^[a-zA-Z0-9_-]+$",
        description="Optional custom short code",
    )
    expiry_days: Optional[int] = Field(
        None,
        ge=1,
        le=3650,
        description="Days until link expires (default: 365)",
    )

    @field_validator("url", mode="before")
    @classmethod
    def validate_url(cls, v: str) -> str:
        blocked_prefixes = ["localhost", "127.", "0.0.0.0", "192.168.", "10."]
        host = str(v).split("//")[-1].split("/")[0].lower()
        if any(host.startswith(p) for p in blocked_prefixes):
            raise ValueError("Private/local URLs are not allowed")
        return v


# ── Response schemas ───────────────────────────────────────────────────────────

class ShortenResponse(BaseModel):
    short_code: str
    short_url: str
    original_url: str
    expires_at: Optional[datetime]
    created_at: datetime

    model_config = {"from_attributes": True}


class AnalyticsSummary(BaseModel):
    short_code: str
    original_url: str
    total_clicks: int
    created_at: datetime
    expires_at: Optional[datetime]
    is_active: bool

    model_config = {"from_attributes": True}


class ClickDataPoint(BaseModel):
    date: str       # ISO date string YYYY-MM-DD
    clicks: int


class AnalyticsDetail(BaseModel):
    summary: AnalyticsSummary
    clicks_by_day: list[ClickDataPoint]
    top_referers: list[dict]
    recent_clicks: list[dict]


class HealthResponse(BaseModel):
    status: str
    db: str
    cache: str
    version: str = "1.0.0"
