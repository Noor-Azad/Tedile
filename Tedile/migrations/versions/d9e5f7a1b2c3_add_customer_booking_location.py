"""store optional customer booking location for provider directions

Revision ID: d9e5f7a1b2c3
Revises: c8d4e6f1a2b3
"""
from alembic import op
import sqlalchemy as sa

revision = "d9e5f7a1b2c3"
down_revision = "c8d4e6f1a2b3"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("bookings") as batch_op:
        batch_op.add_column(sa.Column("customer_latitude", sa.Float(), nullable=True))
        batch_op.add_column(sa.Column("customer_longitude", sa.Float(), nullable=True))
        batch_op.add_column(sa.Column("customer_location_label", sa.String(length=160), nullable=True))


def downgrade():
    with op.batch_alter_table("bookings") as batch_op:
        batch_op.drop_column("customer_location_label")
        batch_op.drop_column("customer_longitude")
        batch_op.drop_column("customer_latitude")
