"""Merge onboarding and admin migration heads

Revision ID: 38a8fec3c1e6
Revises: 4f6b8f2a1c9d, ba7363c1399b
Create Date: 2026-08-19 18:39:55.444504

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '38a8fec3c1e6'
down_revision = ('4f6b8f2a1c9d', 'ba7363c1399b')
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    pass
