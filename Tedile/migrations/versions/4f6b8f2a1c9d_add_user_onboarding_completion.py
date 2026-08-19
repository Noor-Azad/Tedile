"""add user onboarding completion state

Revision ID: 4f6b8f2a1c9d
Revises: cd032e1dc91d
"""
from alembic import op
import sqlalchemy as sa

revision = "4f6b8f2a1c9d"
down_revision = "cd032e1dc91d"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("users", schema=None) as batch_op:
        batch_op.add_column(sa.Column("onboarding_completed", sa.Boolean(), nullable=False, server_default=sa.false()))


def downgrade():
    with op.batch_alter_table("users", schema=None) as batch_op:
        batch_op.drop_column("onboarding_completed")
