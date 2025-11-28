"""Manual migration for Auditoria and Versioning

Revision ID: 957462537052
Revises: b9edd739e75c
Create Date: 2025-11-27 20:45:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '957462537052'
down_revision: Union[str, Sequence[str], None] = 'b9edd739e75c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create Auditoria table
    op.create_table('auditoria',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('usuario_id', sa.Integer(), nullable=True),
        sa.Column('accion', sa.String(length=50), nullable=False),
        sa.Column('tabla', sa.String(length=50), nullable=True),
        sa.Column('registro_id', sa.Integer(), nullable=True),
        sa.Column('detalles', sa.Text(), nullable=True),
        sa.Column('fecha', sa.DateTime(), nullable=True),
        sa.Column('ip_address', sa.String(length=50), nullable=True),
        sa.ForeignKeyConstraint(['usuario_id'], ['usuarios.id'], ),
        sa.PrimaryKeyConstraint('id')
    )

    # 2. Add version_id to productos
    with op.batch_alter_table('productos', schema=None) as batch_op:
        batch_op.add_column(sa.Column('version_id', sa.Integer(), nullable=False, server_default='1'))

    # 3. Add version_id to movimientos_stock
    with op.batch_alter_table('movimientos_stock', schema=None) as batch_op:
        batch_op.add_column(sa.Column('version_id', sa.Integer(), nullable=False, server_default='1'))


def downgrade() -> None:
    with op.batch_alter_table('movimientos_stock', schema=None) as batch_op:
        batch_op.drop_column('version_id')

    with op.batch_alter_table('productos', schema=None) as batch_op:
        batch_op.drop_column('version_id')

    op.drop_table('auditoria')
