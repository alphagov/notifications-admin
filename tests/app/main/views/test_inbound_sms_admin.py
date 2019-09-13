from bs4 import BeautifulSoup
from flask import url_for

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


def test_inbound_sms_admin(platform_admin_client, mocker):
    mocker.patch("app.inbound_number_client.get_all_inbound_sms_number_service", return_value=sample_inbound_sms)
    response = platform_admin_client.get(url_for("main.inbound_sms_admin"))
    assert response.status_code == 200

    page = BeautifulSoup(response.data.decode('utf-8'), 'html.parser')
    assert page.h1.string.strip() == "Inbound SMS"
