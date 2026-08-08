"""add reviews, review findings, review configs, and workspace members

Revision ID: e5f4a3b2c1d0
Revises: f6e5d4c3b2a1
Create Date: 2026-08-08 13:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'e5f4a3b2c1d0'
down_revision = 'f6e5d4c3b2a1'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('reviews',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('project_id', sa.Integer(), nullable=True),
    sa.Column('source', sa.String(length=20), nullable=False),
    sa.Column('kind', sa.String(length=30), nullable=False),
    sa.Column('status', sa.String(length=20), nullable=False),
    sa.Column('error_message', sa.Text(), nullable=True),
    sa.Column('owner', sa.String(length=100), nullable=True),
    sa.Column('repo', sa.String(length=100), nullable=True),
    sa.Column('pr_number', sa.Integer(), nullable=True),
    sa.Column('pr_title', sa.String(length=500), nullable=True),
    sa.Column('base_ref', sa.String(length=200), nullable=True),
    sa.Column('head_ref', sa.String(length=200), nullable=True),
    sa.Column('summary', sa.Text(), nullable=True),
    sa.Column('config', sa.Text(), nullable=True),
    sa.Column('findings_count', sa.Integer(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('reviews', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_reviews_project_id'), ['project_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_reviews_user_id'), ['user_id'], unique=False)

    op.create_table('review_findings',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('review_id', sa.Integer(), nullable=False),
    sa.Column('file', sa.String(length=2000), nullable=True),
    sa.Column('line', sa.Integer(), nullable=True),
    sa.Column('severity', sa.String(length=20), nullable=False),
    sa.Column('category', sa.String(length=50), nullable=False),
    sa.Column('explanation', sa.Text(), nullable=False),
    sa.Column('recommendation', sa.Text(), nullable=True),
    sa.Column('confidence', sa.String(length=20), nullable=False),
    sa.Column('addressed', sa.Boolean(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['review_id'], ['reviews.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('review_findings', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_review_findings_review_id'), ['review_id'], unique=False)

    op.create_table('review_configs',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('project_id', sa.Integer(), nullable=False),
    sa.Column('kinds', sa.String(length=200), nullable=True),
    sa.Column('severity_threshold', sa.String(length=20), nullable=True),
    sa.Column('languages', sa.String(length=500), nullable=True),
    sa.Column('testing_focus', sa.Boolean(), nullable=False),
    sa.Column('security_focus', sa.Boolean(), nullable=False),
    sa.Column('performance_focus', sa.Boolean(), nullable=False),
    sa.Column('max_files', sa.Integer(), nullable=True),
    sa.Column('max_context_chars', sa.Integer(), nullable=True),
    sa.Column('enabled', sa.Boolean(), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('user_id', 'project_id', name='uq_review_configs_user_project')
    )
    with op.batch_alter_table('review_configs', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_review_configs_project_id'), ['project_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_review_configs_user_id'), ['user_id'], unique=False)

    op.create_table('workspace_members',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('workspace_id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('role', sa.String(length=20), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['workspace_id'], ['workspaces.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('workspace_id', 'user_id', name='uq_workspace_members_ws_user')
    )
    with op.batch_alter_table('workspace_members', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_workspace_members_user_id'), ['user_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_workspace_members_workspace_id'), ['workspace_id'], unique=False)


def downgrade():
    with op.batch_alter_table('workspace_members', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_workspace_members_workspace_id'))
        batch_op.drop_index(batch_op.f('ix_workspace_members_user_id'))

    op.drop_table('workspace_members')

    with op.batch_alter_table('review_configs', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_review_configs_user_id'))
        batch_op.drop_index(batch_op.f('ix_review_configs_project_id'))

    op.drop_table('review_configs')

    with op.batch_alter_table('review_findings', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_review_findings_review_id'))

    op.drop_table('review_findings')

    with op.batch_alter_table('reviews', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_reviews_user_id'))
        batch_op.drop_index(batch_op.f('ix_reviews_project_id'))

    op.drop_table('reviews')
