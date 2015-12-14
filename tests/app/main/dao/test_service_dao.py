from app.main.dao import services_dao
from tests.app.main import create_test_user


def test_can_insert_and_retrieve_new_service(notifications_admin, notifications_admin_db, notify_db_session):
    user = create_test_user()

    id = services_dao.insert_new_service('testing service', user)
    saved_service = services_dao.get_service_by_id(id)
    assert id == saved_service.id
    assert saved_service.users == [user]
    assert saved_service.name == 'testing service'


def test_unrestrict_service_updates_the_service(notifications_admin, notifications_admin_db, notify_db_session):
    user = create_test_user()
    id = services_dao.insert_new_service('unrestricted service', user)
    saved_service = services_dao.get_service_by_id(id)
    assert saved_service.restricted is True
    services_dao.unrestrict_service(id)
    unrestricted_service = services_dao.get_service_by_id(id)
    assert unrestricted_service.restricted is False


def test_activate_service_update_service(notifications_admin, notifications_admin_db, notify_db_session):
    user = create_test_user()
    id = services_dao.insert_new_service('activated service', user)
    service = services_dao.get_service_by_id(id)
    assert service.active is False
    services_dao.activate_service(id)
    activated_service = services_dao.get_service_by_id(id)
    assert activated_service.active is True


def test_get_service_returns_none_if_service_does_not_exist(notifications_admin,
                                                            notifications_admin_db,
                                                            notify_db_session):
    service = services_dao.get_service_by_id(1)
    assert service is None
