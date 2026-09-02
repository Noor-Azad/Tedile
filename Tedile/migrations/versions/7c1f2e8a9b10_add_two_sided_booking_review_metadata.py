"""add reviewer metadata and per-booking review uniqueness

Revision ID: 7c1f2e8a9b10
Revises: 38a8fec3c1e6
"""
from alembic import op
import sqlalchemy as sa


revision = "7c1f2e8a9b10"
down_revision = "38a8fec3c1e6"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("reviews") as batch_op:
        batch_op.add_column(sa.Column("reviewer_id", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("reviewer_role", sa.String(length=40), nullable=True))
        batch_op.create_index("ix_reviews_reviewer_id", ["reviewer_id"], unique=False)
        batch_op.create_foreign_key("fk_reviews_reviewer_id_users", "users", ["reviewer_id"], ["id"])
        batch_op.create_unique_constraint("uq_review_booking_reviewer", ["booking_id", "reviewer_id"])


def downgrade():
    with op.batch_alter_table("reviews") as batch_op:
        batch_op.drop_constraint("uq_review_booking_reviewer", type_="unique")
        batch_op.drop_constraint("fk_reviews_reviewer_id_users", type_="foreignkey")
        batch_op.drop_index("ix_reviews_reviewer_id")
        batch_op.drop_column("reviewer_role")
        batch_op.drop_column("reviewer_id")
