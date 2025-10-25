"""change_media_group_id_to_bigint

Revision ID: e172e9fe894f
Revises: 40cbaac93134
Create Date: 2025-10-25 00:26:28.081652+00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e172e9fe894f'
down_revision: Union[str, None] = '40cbaac93134'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Change media_group_id from INTEGER to BIGINT to support large Telegram group IDs
    op.alter_column(
        'posts',
        'media_group_id',
        existing_type=sa.Integer(),
        type_=sa.BigInteger(),
        existing_nullable=True,
        existing_comment='Telegram grouped_id for media groups (albums)'
    )


def downgrade() -> None:
    # Revert media_group_id back to INTEGER
    # WARNING: This will fail if there are values > 2^31-1 in the column
    op.alter_column(
        'posts',
        'media_group_id',
        existing_type=sa.BigInteger(),
        type_=sa.Integer(),
        existing_nullable=True,
        existing_comment='Telegram grouped_id for media groups (albums)'
    )
