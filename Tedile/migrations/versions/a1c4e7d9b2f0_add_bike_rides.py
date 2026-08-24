"""add village bike rides

Revision ID: a1c4e7d9b2f0
Revises: 9b7e3f1a2c4d
"""
from alembic import op
import sqlalchemy as sa

revision = "a1c4e7d9b2f0"
down_revision = "9b7e3f1a2c4d"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "bike_rides",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("customer_id", sa.Integer(), nullable=False),
        sa.Column("rider_id", sa.Integer(), nullable=True),
        sa.Column("pickup_address", sa.String(length=500), nullable=False),
        sa.Column("pickup_latitude", sa.Float(), nullable=False),
        sa.Column("pickup_longitude", sa.Float(), nullable=False),
        sa.Column("destination_address", sa.String(length=500), nullable=False),
        sa.Column("destination_latitude", sa.Float(), nullable=False),
        sa.Column("destination_longitude", sa.Float(), nullable=False),
        sa.Column("customer_note", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("requested_at", sa.DateTime(), nullable=False),
        sa.Column("accepted_at", sa.DateTime(), nullable=True),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.Column("cancelled_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["customer_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["rider_id"], ["riders.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_bike_rides_customer_id", "bike_rides", ["customer_id"])
    op.create_index("ix_bike_rides_rider_id", "bike_rides", ["rider_id"])
    op.create_index("ix_bike_rides_status", "bike_rides", ["status"])


def downgrade():
    op.drop_index("ix_bike_rides_status", table_name="bike_rides")
    op.drop_index("ix_bike_rides_rider_id", table_name="bike_rides")
    op.drop_index("ix_bike_rides_customer_id", table_name="bike_rides")
    op.drop_table("bike_rides")
