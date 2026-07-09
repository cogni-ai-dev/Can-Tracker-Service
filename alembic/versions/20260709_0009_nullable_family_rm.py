"""nullable family rm

Revision ID: 20260709_0009
Revises: 20260709_0008
Create Date: 2026-07-09 00:00:00.000000

"""

from collections.abc import Sequence

from alembic import op
from app.models.base import GUID

revision: str = "20260709_0009"
down_revision: str | None = "20260709_0008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("families") as batch_op:
        batch_op.alter_column("primary_rm_id", existing_type=GUID(), nullable=True)


def downgrade() -> None:
    with op.batch_alter_table("families") as batch_op:
        batch_op.alter_column("primary_rm_id", existing_type=GUID(), nullable=False)
