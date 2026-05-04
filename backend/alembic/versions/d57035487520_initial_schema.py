"""initial_schema

Revision ID: d57035487520
Revises:
Create Date: 2026-03-11 10:00:45.727766

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd57035487520'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'users',
        sa.Column('user_id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('password', sa.String(length=255), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='1'),
        sa.Column('is_admin', sa.Boolean(), nullable=False, server_default='0'),
        sa.Column('must_change_password', sa.Boolean(), nullable=False, server_default='0'),
        sa.Column('theme', sa.String(length=10), nullable=False, server_default='system'),
        sa.Column('language', sa.String(length=10), nullable=False, server_default='en'),
        sa.PrimaryKeyConstraint('user_id'),
        sa.UniqueConstraint('name'),
    )
    op.create_table(
        'roles',
        sa.Column('role_id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.PrimaryKeyConstraint('role_id'),
        sa.UniqueConstraint('name'),
    )
    op.create_table(
        'permissions',
        sa.Column('perm_id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('mod', sa.String(length=100), nullable=False),
        sa.Column('act', sa.String(length=100), nullable=False),
        sa.Column('obj', sa.String(length=200), nullable=False, server_default='*'),
        sa.PrimaryKeyConstraint('perm_id'),
        sa.UniqueConstraint('mod', 'act', 'obj', name='uq_perm_triplet'),
    )
    op.create_table(
        'users2roles',
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('role_id', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['role_id'], ['roles.role_id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.user_id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('user_id', 'role_id'),
    )
    op.create_table(
        'roles2perms',
        sa.Column('role_id', sa.Integer(), nullable=False),
        sa.Column('perm_id', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['perm_id'], ['permissions.perm_id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['role_id'], ['roles.role_id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('role_id', 'perm_id'),
    )


def downgrade() -> None:
    op.drop_table('roles2perms')
    op.drop_table('users2roles')
    op.drop_table('permissions')
    op.drop_table('roles')
    op.drop_table('users')
