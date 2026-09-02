"""add versioned fare pricing and ride snapshots

Revision ID: b7e2f4a8c1d3
Revises: a1c4e7d9b2f0
"""
from alembic import op
import sqlalchemy as sa


revision = "b7e2f4a8c1d3"
down_revision = "a1c4e7d9b2f0"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "fare_configurations",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("base_fare", sa.Numeric(10, 2), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("pricing_version", sa.String(length=40), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("pricing_version"),
    )
    op.execute(
        sa.text(
            "INSERT INTO fare_configurations "
            "(base_fare, currency, pricing_version, created_at) "
            "VALUES (:base_fare, :currency, :pricing_version, CURRENT_TIMESTAMP)"
        ).bindparams(base_fare=50, currency="INR", pricing_version="v1")
    )

    with op.batch_alter_table("bike_rides", schema=None) as batch_op:
        batch_op.add_column(sa.Column("estimated_fare", sa.Numeric(10, 2), nullable=True))
        batch_op.add_column(sa.Column("final_fare", sa.Numeric(10, 2), nullable=True))
        batch_op.add_column(sa.Column("fare_currency", sa.String(length=3), nullable=True))
        batch_op.add_column(sa.Column("pricing_version", sa.String(length=40), nullable=True))
        batch_op.add_column(sa.Column("pricing_base_fare", sa.Numeric(10, 2), nullable=True))

    op.execute(
        sa.text(
            "UPDATE bike_rides SET estimated_fare = :fare, fare_currency = :currency, "
            "pricing_version = :version, pricing_base_fare = :fare "
            "WHERE estimated_fare IS NULL"
        ).bindparams(fare=50, currency="INR", version="v1")
    )
    with op.batch_alter_table("bike_rides", schema=None) as batch_op:
        batch_op.alter_column("estimated_fare", existing_type=sa.Numeric(10, 2), nullable=False)
        batch_op.alter_column("fare_currency", existing_type=sa.String(length=3), nullable=False)
        batch_op.alter_column("pricing_version", existing_type=sa.String(length=40), nullable=False)
        batch_op.alter_column("pricing_base_fare", existing_type=sa.Numeric(10, 2), nullable=False)


def downgrade():
    with op.batch_alter_table("bike_rides", schema=None) as batch_op:
        batch_op.drop_column("pricing_base_fare")
        batch_op.drop_column("pricing_version")
        batch_op.drop_column("fare_currency")
        batch_op.drop_column("final_fare")
        batch_op.drop_column("estimated_fare")
    op.drop_table("fare_configurations")
