import os

import pytest
from alembic.command import upgrade
from alembic.config import Config
from flask.ext.migrate import Migrate, MigrateCommand
from flask.ext.script import Manager
from sqlalchemy.schema import MetaData

from app import create_app, db


@pytest.fixture(scope='session')
def notifications_admin(request):
    app = create_app('test')

    ctx = app.app_context()
    ctx.push()

    def teardown():
        ctx.pop()

    request.addfinalizer(teardown)
    return app


@pytest.fixture(scope='session')
def notifications_admin_db(notifications_admin, request):
    Migrate(notifications_admin, db)
    Manager(db, MigrateCommand)
    BASE_DIR = os.path.dirname(os.path.dirname(__file__))
    ALEMBIC_CONFIG = os.path.join(BASE_DIR, 'migrations')
    config = Config(ALEMBIC_CONFIG + '/alembic.ini')
    config.set_main_option("script_location", ALEMBIC_CONFIG)

    with notifications_admin.app_context():
        upgrade(config, 'head')

    def teardown():
        db.session.remove()
        db.drop_all()
        db.engine.execute("drop table alembic_version")
        db.get_engine(notifications_admin).dispose()

    request.addfinalizer(teardown)


@pytest.fixture(scope='function')
def notify_db_session(request):
    def teardown():
        db.session.remove()
        for tbl in reversed(meta.sorted_tables):
            if tbl.fullname not in ['roles']:
                db.engine.execute(tbl.delete())

    meta = MetaData(bind=db.engine, reflect=True)
    request.addfinalizer(teardown)
