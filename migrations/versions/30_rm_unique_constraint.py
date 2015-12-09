from alembic import op

revision = '30_rm_unique_constraint'
down_revision = '20_initialise_data'


def upgrade():
    op.drop_constraint("users_name_key", "users")


def downgrade():
    op.create_unique_constraint("users_name_key", "users", ["name"])