"""Add paid subscriber tiers

Revision ID: 0002_add_paid_subscriber_tiers
Revises: 0001_initial_schema
Create Date: 2026-10-19 02:43:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0002_add_paid_subscriber_tiers'
down_revision: Union[str, None] = '0001_initial_schema'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    
    # Check if is_paid exists in telegram_subscribers
    tg_cols = [c["name"] for c in sa.inspect(conn).get_columns("telegram_subscribers")]
    if "is_paid" not in tg_cols:
        op.add_column("telegram_subscribers", sa.Column("is_paid", sa.Integer(), server_default="0", nullable=True))

    # Check if is_paid exists in viber_subscribers
    vb_cols = [c["name"] for c in sa.inspect(conn).get_columns("viber_subscribers")]
    if "is_paid" not in vb_cols:
        op.add_column("viber_subscribers", sa.Column("is_paid", sa.Integer(), server_default="0", nullable=True))


def downgrade() -> None:
    op.drop_column("viber_subscribers", "is_paid")
    op.drop_column("telegram_subscribers", "is_paid")
