import uuid
from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class URL(Base):
    __tablename__ = "urls"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    short_code: Mapped[str] = mapped_column(
        String(32), unique=True, nullable=False, index=True
    )
    original_url: Mapped[str] = mapped_column(Text, nullable=False)
    # Optional custom alias set by user
    custom_alias: Mapped[Optional[str]] = mapped_column(String(32), unique=True, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )
    expires_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Denormalised click count for fast reads — kept eventually consistent
    click_count: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)

    # Optional owner (future auth extension)
    owner_ip: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)

    clicks: Mapped[List["Click"]] = relationship(
        "Click", back_populates="url", cascade="all, delete-orphan", lazy="dynamic"
    )

    __table_args__ = (
        # Composite index for expiration sweeps
        Index("ix_urls_expires_at_is_active", "expires_at", "is_active"),
        # Partial index — only index active URLs
        Index(
            "ix_urls_short_code_active",
            "short_code",
            postgresql_where="is_active = true",
        ),
    )

    @property
    def is_expired(self) -> bool:
        if self.expires_at is None:
            return False
        return datetime.now(timezone.utc) > self.expires_at

    def __repr__(self) -> str:
        return f"<URL short_code={self.short_code!r}>"


class Click(Base):
    """
    Each row represents one redirect event.
    Batch-inserted by the background worker from the Redis queue.
    """
    __tablename__ = "clicks"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    url_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("urls.id", ondelete="CASCADE"), nullable=False
    )
    clicked_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )
    # Analytics metadata
    ip_address: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    referer: Mapped[Optional[str]] = mapped_column(String(2048), nullable=True)
    country: Mapped[Optional[str]] = mapped_column(String(2), nullable=True)

    url: Mapped["URL"] = relationship("URL", back_populates="clicks")

    __table_args__ = (
        # Range partition key candidate — time-series queries
        Index("ix_clicks_url_id_clicked_at", "url_id", "clicked_at"),
        Index("ix_clicks_clicked_at", "clicked_at"),
    )
