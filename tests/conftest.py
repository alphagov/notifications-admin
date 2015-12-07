import pytest
from _pytest.monkeypatch import monkeypatch
from sqlalchemy.schema import MetaData, DropConstraint

from app import create_app, db
from app.models import Roles


@pytest.fixture(scope='function')
def notifications_admin(request):
    app = create_app('test')
    ctx = app.app_context()
    ctx.push()

    def teardown():
        ctx.pop()

    request.addfinalizer(teardown)
    return app


@pytest.fixture(scope='function')
def notifications_admin_db(notifications_admin, request):
    metadata = MetaData(db.engine)
    metadata.reflect()
    for table in metadata.tables.values():
        for fk in table.foreign_keys:
            db.engine.execute(DropConstraint(fk.constraint))
    metadata.drop_all()

    # Create the tables based on the current model
    db.create_all()

    # Add base data here
    role = Roles(id=1, role='test_role')
    db.session.add(role)
    db.session.commit()
    db.session.flush()
    db.session.expunge_all()
    db.session.commit()
