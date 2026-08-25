"""allow ride coordinates to be absent in the address-only MVP form

Revision ID: d4a9c7e1f3b5
Revises: c3f8a1d6e2b4
"""

from alembic import op
import sqlalchemy as sa


revision = "d4a9c7e1f3b5"
down_revision = "c3f8a1d6e2b4"
branch_labels = None
depends_on = None


_COORDINATE_COLUMNS = (
    "pickup_latitude",
    "pickup_longitude",
    "destination_latitude",
    "destination_longitude",
)


def upgrade():
    with op.batch_alter_table("bike_rides", schema=None) as batch_op:
        for column in _COORDINATE_COLUMNS:
            batch_op.alter_column(column, existing_type=sa.Float(), nullable=True)


def downgrade():
    bind = op.get_bind()
    predicates = " OR ".join(f"{column} IS NULL" for column in _COORDINATE_COLUMNS)
    missing = bind.execute(sa.text(f"SELECT COUNT(*) FROM bike_rides WHERE {predicates}")).scalar()
    if missing:
        raise RuntimeError(
            "Cannot downgrade ride coordinates to NOT NULL while NULL ride coordinates exist."
        )
    with op.batch_alter_table("bike_rides", schema=None) as batch_op:
        for column in _COORDINATE_COLUMNS:
            batch_op.alter_column(column, existing_type=sa.Float(), nullable=False)
