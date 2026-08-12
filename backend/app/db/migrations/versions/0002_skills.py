"""create skills and user skills tables

Revision ID: 0002_skills
Revises: 0001_users
Create Date: 2026-08-12
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002_skills"
down_revision: str | None = "0001_users"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "skills",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("normalized_name", sa.String(length=120), nullable=False),
        sa.Column("created_by_user_id", sa.Integer(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_skills_normalized_name", "skills", ["normalized_name"], unique=True)

    op.create_table(
        "user_skills",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("skill_id", sa.Integer(), nullable=False),
        sa.Column(
            "intent",
            sa.Enum("TEACH", "LEARN", name="skill_intent"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["skill_id"], ["skills.id"], ondelete="RESTRICT"),
        sa.UniqueConstraint("user_id", "skill_id", "intent", name="uq_user_skill_intent"),
    )
    op.create_index("ix_user_skills_user_id", "user_skills", ["user_id"])
    op.create_index("ix_user_skills_skill_id", "user_skills", ["skill_id"])


def downgrade() -> None:
    op.drop_index("ix_user_skills_skill_id", table_name="user_skills")
    op.drop_index("ix_user_skills_user_id", table_name="user_skills")
    op.drop_table("user_skills")
    op.drop_index("ix_skills_normalized_name", table_name="skills")
    op.drop_table("skills")
    sa.Enum(name="skill_intent").drop(op.get_bind(), checkfirst=True)
