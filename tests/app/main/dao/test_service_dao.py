from app.main.dao import services_dao


def test_can_insert_new_service(db_,
                                db_session,
                                mock_active_user,
                                mock_create_service,
                                mock_get_by_email):
    service_name = 'testing service'
    id_ = services_dao.insert_new_service(service_name, mock_active_user.id)
    mock_create_service.assert_called_once_with(
        service_name, False, 1000, True, mock_active_user.id)


def test_unrestrict_service_updates_the_service(db_,
                                                db_session,
                                                mock_get_service,
                                                mock_update_service,
                                                mock_get_by_email):
    service_one = mock_get_service.side_effect(123)['data']
    services_dao.unrestrict_service(service_one['id'])
    mock_update_service.assert_called_once_with(service_one['id'],
                                                service_one['name'],
                                                service_one['active'],
                                                service_one['limit'],
                                                False,
                                                service_one['users'])


def test_activate_service_update_service(db_,
                                         db_session,
                                         mock_active_user,
                                         mock_get_service,
                                         mock_update_service,
                                         mock_get_by_email):
    service_one = mock_get_service.side_effect(123)['data']
    services_dao.activate_service(service_one['id'])
    mock_update_service.assert_called_once_with(service_one['id'],
                                                service_one['name'],
                                                True,
                                                service_one['limit'],
                                                service_one['restricted'],
                                                service_one['users'])


def test_get_service_returns_none_if_service_does_not_exist(db_, db_session, mock_get_service):
    mock_get_service.side_effect = lambda x: None
    service = services_dao.get_service_by_id(1)
    assert service is None


def test_find_by_service_name_returns_right_service(db_, db_session, mock_get_services):
    service_name = "service_one"
    service = services_dao.find_service_by_service_name(service_name)
    assert mock_get_services.called
    assert service['name'] == service_name


def test_should_return_list_of_service_names(db_, db_session, mock_api_user, mock_get_services):
    expected = ['service_one', 'service_two']
    actual = services_dao.find_all_service_names(mock_api_user.id)
    assert mock_get_services.called
    assert actual == expected
