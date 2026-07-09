from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260709_0012"
down_revision: str | None = "20260709_0011"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("members", sa.Column("nominee_name", sa.String(length=200), nullable=True))
    op.create_index("ix_members_nominee_name", "members", ["nominee_name"])


def downgrade() -> None:
    op.drop_index("ix_members_nominee_name", table_name="members")
    op.drop_column("members", "nominee_name")
