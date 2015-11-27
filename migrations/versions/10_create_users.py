"""empty message

Revision ID: create_users
Revises: None
Create Date: 2015-11-24 10:39:19.827534

"""

# revision identifiers, used by Alembic.
revision = '10_create_users'
down_revision = None

from alembic import op
import sqlalchemy as sa

def upgrade():
    op.create_table('roles',
                    sa.Column('id', sa.Integer, primary_key=True),
                    sa.Column('role', sa.String, nullable=False, unique=True)
                    )

    op.create_table('users',
                    sa.Column('id', sa.Integer, primary_key=True),
                    sa.Column('name', sa.String, nullable=False, unique=True),
                    sa.Column('email_address', sa.String(length=255), nullable=False),
                    sa.Column('password', sa.String, nullable=False),
                    sa.Column('mobile_number', sa.String, nullable=False),
                    sa.Column('created_at', sa.DateTime, nullable=False),
                    sa.Column('updated_at', sa.DateTime),
                    sa.Column('password_changed_at', sa.DateTime),
                    sa.Column('role_id', sa.Integer, nullable=False),
                    sa.Column('logged_in_at', sa.DateTime),
                    sa.Column('failed_login_count', sa.Integer, nullable=False),
                    sa.Column('state', sa.String, default='pending'),
                    sa.ForeignKeyConstraint(['role_id'], ['roles.id'])
                    )


def downgrade():
    op.drop_table('users')
    op.drop_table('roles')
