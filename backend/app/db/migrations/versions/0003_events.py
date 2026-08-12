"""create events scheduling tables

Revision ID: 0003_events
Revises: 0002_skills
Create Date: 2026-08-12
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0003_events"
down_revision: str | None = "0002_skills"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    event_status = sa.Enum("SCHEDULING", "CONFIRMED", "COMPLETED", "CANCELLED", name="event_status")
    participant_role = sa.Enum("TEACHER", "LEARNER", name="event_participant_role")
    event_status.create(op.get_bind(), checkfirst=True)
    participant_role.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("creator_id", sa.Integer(), nullable=False),
        sa.Column("teacher_id", sa.Integer(), nullable=False),
        sa.Column("skill_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=160), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("status", event_status, nullable=False, server_default="SCHEDULING"),
        sa.Column("confirmed_time_option_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["creator_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["teacher_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["skill_id"], ["skills.id"], ondelete="RESTRICT"),
    )
    op.create_index("ix_events_creator_id", "events", ["creator_id"])
    op.create_index("ix_events_teacher_id", "events", ["teacher_id"])
    op.create_index("ix_events_skill_id", "events", ["skill_id"])

    op.create_table(
        "event_participants",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("event_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("role", participant_role, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["event_id"], ["events.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("event_id", "user_id", name="uq_event_participant"),
    )
    op.create_index("ix_event_participants_event_id", "event_participants", ["event_id"])
    op.create_index("ix_event_participants_user_id", "event_participants", ["user_id"])

    op.create_table(
        "event_time_options",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("event_id", sa.Integer(), nullable=False),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["event_id"], ["events.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_event_time_options_event_id", "event_time_options", ["event_id"])
    op.create_index("ix_event_time_options_starts_at", "event_time_options", ["starts_at"])

    op.create_foreign_key(
        "fk_events_confirmed_time_option_id",
        "events",
        "event_time_options",
        ["confirmed_time_option_id"],
        ["id"],
        ondelete="SET NULL",
    )

    op.create_table(
        "event_time_votes",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("time_option_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["time_option_id"], ["event_time_options.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("time_option_id", "user_id", name="uq_event_time_vote"),
    )
    op.create_index("ix_event_time_votes_time_option_id", "event_time_votes", ["time_option_id"])
    op.create_index("ix_event_time_votes_user_id", "event_time_votes", ["user_id"])


def downgrade() -> None:
    op.drop_table("event_time_votes")
    op.drop_constraint("fk_events_confirmed_time_option_id", "events", type_="foreignkey")
    op.drop_table("event_time_options")
    op.drop_table("event_participants")
    op.drop_table("events")
    sa.Enum(name="event_participant_role").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="event_status").drop(op.get_bind(), checkfirst=True)
