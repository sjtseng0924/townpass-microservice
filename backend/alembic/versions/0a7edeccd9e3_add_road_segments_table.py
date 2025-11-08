"""add road_segments table

Revision ID: 0a7edeccd9e3
Revises: d49962ca0d4b
Create Date: 2025-11-08 00:00:00
"""

from alembic import op
import sqlalchemy as sa


revision = "0a7edeccd9e3"
down_revision = "1a34685c3b0f"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "road_segments",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("osmid", sa.String(length=255), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=True),
        sa.Column("highway", sa.String(length=50), nullable=True),
        sa.Column("lanes", sa.String(length=50), nullable=True),
        sa.Column("oneway", sa.Boolean(), nullable=True),
        sa.Column("length_m", sa.Float(), nullable=True),
        sa.Column("properties", sa.JSON(), nullable=True),
        sa.Column("geometry", sa.JSON(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_road_segments_highway"), "road_segments", ["highway"], unique=False)
    op.create_index(op.f("ix_road_segments_name"), "road_segments", ["name"], unique=False)
    op.create_index(op.f("ix_road_segments_osmid"), "road_segments", ["osmid"], unique=True)


def downgrade() -> None:
    op.drop_index(op.f("ix_road_segments_osmid"), table_name="road_segments")
    op.drop_index(op.f("ix_road_segments_name"), table_name="road_segments")
    op.drop_index(op.f("ix_road_segments_highway"), table_name="road_segments")
    op.drop_table("road_segments")
