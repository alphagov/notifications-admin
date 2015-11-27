# revision identifiers, used by Alembic.
revision = '20_initialise_data'
down_revision = '10_create_users'
from app.models import Roles
from alembic import op

def upgrade():
    op.execute("insert into roles(role) values('platform_admin')")
    op.execute("insert into roles(role) values('service_user')")


def downgrade():
    op.drop_table('users')
    op.drop_table('roles')
