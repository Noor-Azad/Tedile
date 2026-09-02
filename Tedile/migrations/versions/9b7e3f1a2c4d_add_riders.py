"""add rider applications

Revision ID: 9b7e3f1a2c4d
Revises: 38a8fec3c1e6
"""

from alembic import op
import sqlalchemy as sa


revision = "9b7e3f1a2c4d"
down_revision = "38a8fec3c1e6"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "riders",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("bike_make_model", sa.String(length=160), nullable=False),
        sa.Column("bike_registration_number", sa.Text(), nullable=False),
        sa.Column("license_number", sa.Text(), nullable=False),
        sa.Column("license_expiry_date", sa.Date(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="PENDING"),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id"),
    )
    op.create_index("ix_riders_user_id", "riders", ["user_id"], unique=False)
    op.create_index("ix_riders_status", "riders", ["status"], unique=False)


def downgrade():
    op.drop_index("ix_riders_status", table_name="riders")
    op.drop_index("ix_riders_user_id", table_name="riders")
    op.drop_table("riders")
