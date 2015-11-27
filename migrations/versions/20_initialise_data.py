# revision identifiers, used by Alembic.
revision = '20_initialise_data'
down_revision = None

from alembic import op

def upgrade():
    op.bulk_insert('roles',
                   [
                       {'role': 'plaform_admin'},
                       {'role': 'service_user'}
                   ])

def downgrade():
    op.drop_table('users')
    op.drop_table('roles')
