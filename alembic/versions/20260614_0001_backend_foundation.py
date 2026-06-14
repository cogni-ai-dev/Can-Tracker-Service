"""backend foundation

Revision ID: 20260614_0001
Revises:
Create Date: 2026-06-14 00:00:00.000000

"""

from collections.abc import Sequence

revision: str = "20260614_0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
