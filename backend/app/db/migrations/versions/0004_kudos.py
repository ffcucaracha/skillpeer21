"""create kudos table

Revision ID: 0004_kudos
Revises: 0003_events
Create Date: 2026-08-12
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0004_kudos"
down_revision: str | None = "0003_events"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "kudos",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("event_id", sa.Integer(), nullable=False),
        sa.Column("sender_id", sa.Integer(), nullable=False),
        sa.Column("recipient_id", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(["event_id"], ["events.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["sender_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["recipient_id"], ["users.id"], ondelete="CASCADE"),
        sa.UniqueConstraint(
            "event_id",
            "sender_id",
            "recipient_id",
            name="uq_kudos_event_sender_recipient",
        ),
    )
    op.create_index("ix_kudos_event_id", "kudos", ["event_id"])
    op.create_index("ix_kudos_sender_id", "kudos", ["sender_id"])
    op.create_index("ix_kudos_recipient_id", "kudos", ["recipient_id"])


def downgrade() -> None:
    op.drop_index("ix_kudos_recipient_id", table_name="kudos")
    op.drop_index("ix_kudos_sender_id", table_name="kudos")
    op.drop_index("ix_kudos_event_id", table_name="kudos")
    op.drop_table("kudos")
