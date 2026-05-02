"""Initial schema

Revision ID: 001_initial
Revises:
Create Date: 2024-01-01 00:00:00
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "urls",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("short_code", sa.String(32), nullable=False),
        sa.Column("original_url", sa.Text, nullable=False),
        sa.Column("custom_alias", sa.String(32), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("click_count", sa.BigInteger, nullable=False, server_default="0"),
        sa.Column("owner_ip", sa.String(45), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("short_code"),
        sa.UniqueConstraint("custom_alias"),
    )
    op.create_index("ix_urls_short_code", "urls", ["short_code"])
    op.create_index("ix_urls_expires_at_is_active", "urls", ["expires_at", "is_active"])
    op.create_index(
        "ix_urls_short_code_active",
        "urls",
        ["short_code"],
        postgresql_where=sa.text("is_active = true"),
    )

    op.create_table(
        "clicks",
        sa.Column("id", sa.BigInteger, autoincrement=True, nullable=False),
        sa.Column("url_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("clicked_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.Column("ip_address", sa.String(45), nullable=True),
        sa.Column("user_agent", sa.String(512), nullable=True),
        sa.Column("referer", sa.String(2048), nullable=True),
        sa.Column("country", sa.String(2), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["url_id"], ["urls.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_clicks_url_id_clicked_at", "clicks", ["url_id", "clicked_at"])
    op.create_index("ix_clicks_clicked_at", "clicks", ["clicked_at"])


def downgrade() -> None:
    op.drop_table("clicks")
    op.drop_table("urls")
