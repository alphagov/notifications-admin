sample_inbound_sms = {'data': [{"id": "activated",
                                "number": "0784121212",
                                "provider": "provider_one",
                                "service": {"id": "123234", "name": "Service One"},
                                "active": True,
                                "created_at": "2017-08-15T13:30:30.12312",
                                "updated_at": "2017-08-15T13:30:30.12312"},
                               {"id": "available",
                                "number": "0784131313",
                                "provider": "provider_one",
                                "service": None,
                                "active": True,
                                "created_at": "2017-08-15T13:30:30.12312",
                                "updated_at": None},
                               {"id": "deactivated",
                                "number": "0784131313",
                                "provider": "provider_one",
                                "service": None,
                                "active": True,
                                "created_at": "2017-08-15T13:30:30.12312",
                                "updated_at": None}
                               ]}


def test_inbound_sms_admin(
    client_request,
    platform_admin_user,
    mocker,
):
    mocker.patch("app.inbound_number_client.get_all_inbound_sms_number_service", return_value=sample_inbound_sms)
    client_request.login(platform_admin_user)
    page = client_request.get("main.inbound_sms_admin")
    assert page.h1.string.strip() == "Inbound SMS"
