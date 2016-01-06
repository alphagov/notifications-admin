import os

import pytest
from alembic.command import upgrade
from alembic.config import Config
from flask import url_for
from flask.ext.migrate import Migrate, MigrateCommand
from flask.ext.script import Manager
from flask_login import login_user
from sqlalchemy.schema import MetaData
from flask.testing import FlaskClient
from app.main.dao import verify_codes_dao

from app import create_app, db

class TestClient(FlaskClient):
    def login(self, user):
        # Skipping authentication here and just log them in
        with self.session_transaction() as session:
            session['user_id'] = user.id
        verify_codes_dao.add_code(user_id=user.id, code='12345', code_type='sms')
        response = self.post('/two-factor',
                               data={'sms_code': '12345'})

    def logout(self, user):
        self.get(url_for("main.logout"))


@pytest.fixture(scope='session')
def notifications_admin(request):
    app = create_app('test')

    ctx = app.app_context()
    ctx.push()

    def teardown():
        ctx.pop()

    request.addfinalizer(teardown)
    app.test_client_class = TestClient
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
