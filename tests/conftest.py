import copy
import json
import os
from contextlib import contextmanager
from datetime import date, datetime, timedelta
from unittest import mock
from unittest.mock import Mock, PropertyMock
from uuid import UUID, uuid4

import html5lib
import pytest
from flask import Flask, current_app, url_for
from notifications_python_client.errors import HTTPError
from notifications_utils.url_safe_token import generate_token

from app import create_app, reset_memos, webauthn_server
from app.constants import REPORT_REQUEST_STORED, LetterLanguageOptions

from . import (
    NotifyBeautifulSoup,
    TestClient,
    api_key_json,
    assert_url_expected,
    contact_list_json,
    generate_uuid,
    inbound_sms_json,
    invite_json,
    job_json,
    notification_json,
    org_invite_json,
    organisation_json,
    sample_uuid,
    service_json,
    template_json,
    template_version_json,
    user_json,
)
from .utils import check_render_template_forms

html5parser = html5lib.HTMLParser()


class ElementNotFound(Exception):
    pass


@pytest.fixture(scope="session")
def notify_admin_without_context():
    """
    You probably won't need to use this fixture, unless you need to use the flask.appcontext_pushed hook. Possibly if
    you're patching something on `g`. https://flask.palletsprojects.com/en/1.1.x/testing/#faking-resources-and-context
    """
    app = Flask("app")
    create_app(app)
    app.test_client_class = TestClient

    return app


@pytest.fixture
def notify_admin(notify_admin_without_context):
    reset_memos()

    with notify_admin_without_context.app_context():
        yield notify_admin_without_context

    reset_memos()


@pytest.fixture(scope="function")
def service_one(api_user_active):
    return service_json(SERVICE_ONE_ID, "service one", [api_user_active["id"]])


@pytest.fixture(scope="function")
def service_two(api_user_active):
    return service_json(SERVICE_TWO_ID, "service two", [api_user_active["id"]])


@pytest.fixture(scope="function")
def multiple_reply_to_email_addresses(mocker):
    def _get(service_id):
        return [
            {
                "id": "1234",
                "service_id": service_id,
                "email_address": "test@example.com",
                "is_default": True,
                "created_at": datetime.utcnow(),
                "updated_at": None,
            },
            {
                "id": "5678",
                "service_id": service_id,
                "email_address": "test2@example.com",
                "is_default": False,
                "created_at": datetime.utcnow(),
                "updated_at": None,
            },
            {
                "id": "9457",
                "service_id": service_id,
                "email_address": "test3@example.com",
                "is_default": False,
                "created_at": datetime.utcnow(),
                "updated_at": None,
            },
        ]

    return mocker.patch(
        "app.service_api_client.get_reply_to_email_addresses",
        side_effect=_get,
    )


@pytest.fixture(scope="function")
def no_reply_to_email_addresses(notify_admin, mocker):
    def _get(service_id):
        return []

    return mocker.patch("app.service_api_client.get_reply_to_email_addresses", side_effect=_get)


@pytest.fixture(scope="function")
def single_reply_to_email_address(notify_admin, mocker):
    def _get(service_id):
        return [
            {
                "id": "1234",
                "service_id": service_id,
                "email_address": "test@example.com",
                "is_default": True,
                "created_at": datetime.utcnow(),
                "updated_at": None,
            }
        ]

    return mocker.patch("app.service_api_client.get_reply_to_email_addresses", side_effect=_get)


@pytest.fixture(scope="function")
def get_default_reply_to_email_address(notify_admin, mocker):
    def _get(service_id, reply_to_email_id):
        return {
            "id": "1234",
            "service_id": service_id,
            "email_address": "test@example.com",
            "is_default": True,
            "created_at": datetime.utcnow(),
            "updated_at": None,
        }

    return mocker.patch("app.service_api_client.get_reply_to_email_address", side_effect=_get)


@pytest.fixture(scope="function")
def get_non_default_reply_to_email_address(notify_admin, mocker):
    def _get(service_id, reply_to_email_id):
        return {
            "id": "1234",
            "service_id": service_id,
            "email_address": "test@example.com",
            "is_default": False,
            "created_at": datetime.utcnow(),
            "updated_at": None,
        }

    return mocker.patch("app.service_api_client.get_reply_to_email_address", side_effect=_get)


@pytest.fixture(scope="function")
def mock_add_reply_to_email_address(notify_admin, mocker):
    def _add_reply_to(service_id, email_address, is_default=False):
        return

    return mocker.patch("app.service_api_client.add_reply_to_email_address", side_effect=_add_reply_to)


@pytest.fixture(scope="function")
def mock_update_reply_to_email_address(notify_admin, mocker):
    def _update_reply_to(service_id, reply_to_email_id, email_address=None, active=None, is_default=False):
        return

    return mocker.patch("app.service_api_client.update_reply_to_email_address", side_effect=_update_reply_to)


@pytest.fixture(scope="function")
def multiple_letter_contact_blocks(notify_admin, mocker):
    def _get(service_id):
        return [
            {
                "id": "1234",
                "service_id": service_id,
                "contact_block": "1 Example Street",
                "is_default": True,
                "created_at": datetime.utcnow(),
                "updated_at": None,
            },
            {
                "id": "5678",
                "service_id": service_id,
                "contact_block": "2 Example Street",
                "is_default": False,
                "created_at": datetime.utcnow(),
                "updated_at": None,
            },
            {
                "id": "9457",
                "service_id": service_id,
                "contact_block": "3 Example Street",
                "is_default": False,
                "created_at": datetime.utcnow(),
                "updated_at": None,
            },
        ]

    return mocker.patch("app.service_api_client.get_letter_contacts", side_effect=_get)


@pytest.fixture(scope="function")
def no_letter_contact_blocks(notify_admin, mocker):
    def _get(service_id):
        return []

    return mocker.patch("app.service_api_client.get_letter_contacts", side_effect=_get)


@pytest.fixture(scope="function")
def single_letter_contact_block(notify_admin, mocker):
    def _get(service_id):
        return [
            {
                "id": "1234",
                "service_id": service_id,
                "contact_block": "1 Example Street",
                "is_default": True,
                "created_at": datetime.utcnow(),
                "updated_at": None,
            }
        ]

    return mocker.patch("app.service_api_client.get_letter_contacts", side_effect=_get)


@pytest.fixture(scope="function")
def injected_letter_contact_block(notify_admin, mocker):
    def _get(service_id):
        return [
            {
                "id": "1234",
                "service_id": service_id,
                "contact_block": "foo\nbar<script>alert(1);</script>",
                "is_default": True,
                "created_at": datetime.utcnow(),
                "updated_at": None,
            }
        ]

    return mocker.patch("app.service_api_client.get_letter_contacts", side_effect=_get)


@pytest.fixture(scope="function")
def get_default_letter_contact_block(notify_admin, mocker):
    def _get(service_id, letter_contact_id):
        return {
            "id": "1234",
            "service_id": service_id,
            "contact_block": "1 Example Street",
            "is_default": True,
            "created_at": datetime.utcnow(),
            "updated_at": None,
        }

    return mocker.patch("app.service_api_client.get_letter_contact", side_effect=_get)


@pytest.fixture(scope="function")
def mock_add_letter_contact(notify_admin, mocker):
    def _add_letter_contact(service_id, contact_block, is_default=False):
        return {
            "data": {
                "id": "1234",
                "service_id": service_id,
                "contact_block": "1 Example Street",
                "is_default": True,
                "created_at": str(datetime.utcnow()),
                "updated_at": None,
            }
        }

    return mocker.patch("app.service_api_client.add_letter_contact", side_effect=_add_letter_contact)


@pytest.fixture(scope="function")
def mock_update_letter_contact(notify_admin, mocker):
    def _update_letter_contact(service_id, letter_contact_id, contact_block, is_default=False):
        return

    return mocker.patch("app.service_api_client.update_letter_contact", side_effect=_update_letter_contact)


@pytest.fixture(scope="function")
def multiple_sms_senders(notify_admin, mocker):
    def _get(service_id):
        return [
            {
                "id": "1234",
                "service_id": service_id,
                "sms_sender": "07812398712",
                "is_default": True,
                "created_at": datetime.utcnow(),
                "inbound_number_id": "4321",
                "updated_at": None,
            },
            {
                "id": "5678",
                "service_id": service_id,
                "sms_sender": "Example 2",
                "is_default": False,
                "created_at": datetime.utcnow(),
                "inbound_number_id": None,
                "updated_at": None,
            },
            {
                "id": "9457",
                "service_id": service_id,
                "sms_sender": "Example 3",
                "is_default": False,
                "created_at": datetime.utcnow(),
                "inbound_number_id": None,
                "updated_at": None,
            },
        ]

    return mocker.patch("app.service_api_client.get_sms_senders", side_effect=_get)


@pytest.fixture(scope="function")
def multiple_sms_senders_with_diff_default(notify_admin, mocker):
    def _get(service_id):
        return [
            {
                "id": "1234",
                "service_id": service_id,
                "sms_sender": "Example",
                "is_default": True,
                "created_at": datetime.utcnow(),
                "inbound_number_id": None,
                "updated_at": None,
            },
            {
                "id": "5678",
                "service_id": service_id,
                "sms_sender": "Example 2",
                "is_default": False,
                "created_at": datetime.utcnow(),
                "inbound_number_id": None,
                "updated_at": None,
            },
            {
                "id": "9457",
                "service_id": service_id,
                "sms_sender": "Example 3",
                "is_default": False,
                "created_at": datetime.utcnow(),
                "inbound_number_id": "12354",
                "updated_at": None,
            },
        ]

    return mocker.patch("app.service_api_client.get_sms_senders", side_effect=_get)


@pytest.fixture(scope="function")
def multiple_sms_senders_no_inbound(notify_admin, mocker):
    def _get(service_id):
        return [
            {
                "id": "1234",
                "service_id": service_id,
                "sms_sender": "Example",
                "is_default": True,
                "created_at": datetime.utcnow(),
                "inbound_number_id": None,
                "updated_at": None,
            },
            {
                "id": "5678",
                "service_id": service_id,
                "sms_sender": "Example 2",
                "is_default": False,
                "created_at": datetime.utcnow(),
                "inbound_number_id": None,
                "updated_at": None,
            },
        ]

    return mocker.patch("app.service_api_client.get_sms_senders", side_effect=_get)


@pytest.fixture(scope="function")
def no_sms_senders(notify_admin, mocker):
    def _get(service_id):
        return []

    return mocker.patch("app.service_api_client.get_sms_senders", side_effect=_get)


@pytest.fixture(scope="function")
def single_sms_sender(notify_admin, mocker):
    def _get(service_id):
        return [
            {
                "id": "1234",
                "service_id": service_id,
                "sms_sender": "GOVUK",
                "is_default": True,
                "created_at": datetime.utcnow(),
                "inbound_number_id": None,
                "updated_at": None,
            }
        ]

    return mocker.patch("app.service_api_client.get_sms_senders", side_effect=_get)


@pytest.fixture(scope="function")
def get_default_sms_sender(notify_admin, mocker):
    def _get(service_id, sms_sender_id):
        return {
            "id": "1234",
            "service_id": service_id,
            "sms_sender": "GOVUK",
            "is_default": True,
            "created_at": datetime.utcnow(),
            "inbound_number_id": None,
            "updated_at": None,
        }

    return mocker.patch("app.service_api_client.get_sms_sender", side_effect=_get)


@pytest.fixture(scope="function")
def get_non_default_sms_sender(notify_admin, mocker):
    def _get(service_id, sms_sender_id):
        return {
            "id": "1234",
            "service_id": service_id,
            "sms_sender": "GOVUK",
            "is_default": False,
            "created_at": datetime.utcnow(),
            "inbound_number_id": None,
            "updated_at": None,
        }

    return mocker.patch("app.service_api_client.get_sms_sender", side_effect=_get)


@pytest.fixture(scope="function")
def mock_add_sms_sender(notify_admin, mocker):
    def _add_sms_sender(service_id, sms_sender, is_default=False):
        return

    return mocker.patch("app.service_api_client.add_sms_sender", side_effect=_add_sms_sender)


@pytest.fixture(scope="function")
def mock_update_sms_sender(notify_admin, mocker):
    def _update_sms_sender(service_id, sms_sender_id, sms_sender=None, active=None, is_default=False):
        return

    return mocker.patch("app.service_api_client.update_sms_sender", side_effect=_update_sms_sender)


@pytest.fixture(scope="function")
def multiple_available_inbound_numbers(notify_admin, mocker):
    def _get():
        return {
            "data": [
                {
                    "active": True,
                    "created_at": "2017-10-18T16:57:14.154185Z",
                    "id": "781d9c60-7a7e-46b7-9896-7b045b992fa7",
                    "number": "0712121214",
                    "provider": "mmg",
                    "service": None,
                    "updated_at": None,
                },
                {
                    "active": True,
                    "created_at": "2017-10-18T16:57:22.585806Z",
                    "id": "781d9c60-7a7e-46b7-9896-7b045b992fa5",
                    "number": "0712121215",
                    "provider": "mmg",
                    "service": None,
                    "updated_at": None,
                },
                {
                    "active": True,
                    "created_at": "2017-10-18T16:57:38.585806Z",
                    "id": "781d9c61-7a7e-46b7-9896-7b045b992fa5",
                    "number": "0712121216",
                    "provider": "mmg",
                    "service": None,
                    "updated_at": None,
                },
            ]
        }

    return mocker.patch("app.inbound_number_client.get_available_inbound_sms_numbers", side_effect=_get)


@pytest.fixture(scope="function")
def no_available_inbound_numbers(notify_admin, mocker):
    def _get():
        return {"data": []}

    return mocker.patch("app.inbound_number_client.get_available_inbound_sms_numbers", side_effect=_get)


@pytest.fixture(scope="function")
def fake_uuid():
    return sample_uuid()


@pytest.fixture
def mocked_get_service_data():
    """Data source for `mock_get_service`

    This fixture is the underlying data source for `mock_get_service`. Insert service JSON blobs into this dictionary,
    with service ID as the key, to allow multiple services to be queried from `get_service` calls.
    """
    return {}


@pytest.fixture(scope="function")
def mock_get_service(notify_admin, mocker, api_user_active, mocked_get_service_data):
    def _get(service_id):
        return {
            "data": mocked_get_service_data.get(
                service_id,
                service_json(
                    service_id,
                    users=[api_user_active["id"]],
                    email_message_limit=50,
                    sms_message_limit=50,
                    letter_message_limit=50,
                ),
            )
        }

    return mocker.patch("app.service_api_client.get_service", side_effect=_get)


@pytest.fixture(scope="function")
def mock_get_service_statistics(notify_admin, mocker, api_user_active):
    def _get(service_id, limit_days=None):
        return {
            "email": {"requested": 0, "delivered": 0, "failed": 0},
            "sms": {"requested": 0, "delivered": 0, "failed": 0},
            "letter": {"requested": 0, "delivered": 0, "failed": 0},
        }

    return mocker.patch("app.service_api_client.get_service_statistics", side_effect=_get)


@pytest.fixture(scope="function")
def mock_get_unsubscribe_requests_statistics(notify_admin, mocker):
    return mocker.patch(
        "app.service_api_client.get_unsubscribe_request_statistics",
        return_value={
            "unsubscribe_requests_count": 250,
            "datetime_of_latest_unsubscribe_request": "2024-07-14 09:36:17",
        },
    )


@pytest.fixture(scope="function")
def mock_get_detailed_services(notify_admin, mocker, fake_uuid):
    service_one = service_json(
        id_=SERVICE_ONE_ID,
        name="service_one",
        users=[fake_uuid],
        email_message_limit=1000,
        sms_message_limit=1000,
        letter_message_limit=1000,
        active=True,
        restricted=False,
    )
    service_two = service_json(
        id_=fake_uuid,
        name="service_two",
        users=[fake_uuid],
        email_message_limit=1000,
        sms_message_limit=1000,
        letter_message_limit=1000,
        active=True,
        restricted=True,
    )
    service_one["statistics"] = {
        "email": {"requested": 0, "delivered": 0, "failed": 0},
        "sms": {"requested": 0, "delivered": 0, "failed": 0},
        "letter": {"requested": 0, "delivered": 0, "failed": 0},
    }
    service_two["statistics"] = {
        "email": {"requested": 0, "delivered": 0, "failed": 0},
        "sms": {"requested": 0, "delivered": 0, "failed": 0},
        "letter": {"requested": 0, "delivered": 0, "failed": 0},
    }
    services = {"data": [service_one, service_two]}

    return mocker.patch("app.service_api_client.get_services", return_value=services)


@pytest.fixture(scope="function")
def mock_get_live_service(notify_admin, mocker, api_user_active):
    def _get(service_id):
        service = service_json(service_id, users=[api_user_active["id"]], restricted=False)
        return {"data": service}

    return mocker.patch("app.service_api_client.get_service", side_effect=_get)


@pytest.fixture(scope="function")
def mock_create_service(notify_admin, mocker):
    def _create(
        service_name,
        organisation_type,
        email_message_limit,
        international_sms_message_limit,
        sms_message_limit,
        letter_message_limit,
        restricted,
        user_id,
    ):
        service = service_json(
            101,
            service_name,
            [user_id],
            restricted=restricted,
            email_message_limit=email_message_limit,
            international_sms_message_limit=international_sms_message_limit,
            sms_message_limit=sms_message_limit,
            letter_message_limit=letter_message_limit,
        )
        return service["id"]

    return mocker.patch("app.service_api_client.create_service", side_effect=_create)


@pytest.fixture(scope="function")
def mock_update_service(notify_admin, mocker):
    def _update(service_id, **kwargs):
        service = service_json(
            service_id,
            **{
                key: kwargs[key]
                for key in kwargs
                if key
                in [
                    "name",
                    "users",
                    "active",
                    "sms_message_limit",
                    "email_message_limit",
                    "letter_message_limit",
                    "restricted",
                    "sms_sender",
                    "permissions",
                ]
            },
        )
        return {"data": service}

    return mocker.patch("app.service_api_client.update_service", side_effect=_update, autospec=True)


@pytest.fixture(scope="function")
def mock_update_service_raise_httperror_duplicate_name(notify_admin, mocker):
    def _update(service_id, **kwargs):
        json_mock = Mock(return_value={"message": {"name": [f"Duplicate service name '{kwargs.get('name')}'"]}})
        resp_mock = Mock(status_code=400, json=json_mock)
        http_error = HTTPError(response=resp_mock, message="Default message")
        raise http_error

    return mocker.patch("app.service_api_client.update_service", side_effect=_update)


SERVICE_ONE_ID = "596364a0-858e-42c8-9062-a8fe822260eb"
SERVICE_TWO_ID = "147ad62a-2951-4fa1-9ca0-093cd1a52c52"
ORGANISATION_ID = "c011fa40-4cbe-4524-b415-dde2f421bd9c"
ORGANISATION_TWO_ID = "d9b5be73-0b36-4210-9d89-8f1a5c2fef26"
TEMPLATE_ONE_ID = "b22d7d94-2197-4a7d-a8e7-fd5f9770bf48"
USER_ONE_ID = "7b395b52-c6c1-469c-9d61-54166461c1ab"


@pytest.fixture(scope="function")
def mock_get_services(notify_admin, mocker, active_user_with_permissions):
    def _get_services(params_dict=None):
        service_one = service_json(
            SERVICE_ONE_ID, "service_one", [active_user_with_permissions["id"]], 1000, True, False
        )
        service_two = service_json(
            SERVICE_TWO_ID, "service_two", [active_user_with_permissions["id"]], 1000, True, False
        )
        return {"data": [service_one, service_two]}

    return mocker.patch("app.service_api_client.get_services", side_effect=_get_services)


@pytest.fixture(scope="function")
def mock_get_services_with_no_services(notify_admin, mocker):
    def _get_services(params_dict=None):
        return {"data": []}

    return mocker.patch("app.service_api_client.get_services", side_effect=_get_services)


@pytest.fixture(scope="function")
def mock_get_services_with_one_service(notify_admin, mocker, api_user_active):
    def _get_services(params_dict=None):
        return {"data": [service_json(SERVICE_ONE_ID, "service_one", [api_user_active["id"]], 1000, True, True)]}

    return mocker.patch("app.service_api_client.get_services", side_effect=_get_services)


@pytest.fixture(scope="function")
def mock_get_service_template(notify_admin, mocker):
    def _get(service_id, template_id, version=None):
        template = template_json(
            service_id=service_id,
            id_=template_id,
            name="Two week reminder",
            type_="sms",
            content="Template <em>content</em> with & entity",
        )
        if version:
            template.update({"version": version})
        return {"data": template}

    return mocker.patch("app.service_api_client.get_service_template", side_effect=_get)


@pytest.fixture(scope="function")
def mock_get_deleted_template(notify_admin, mocker):
    def _get(service_id, template_id, version=None):
        template = template_json(
            service_id=service_id,
            id_=template_id,
            name="Two week reminder",
            type_="sms",
            content="Template <em>content</em> with & entity",
            archived=True,
        )
        if version:
            template.update({"version": version})
        return {"data": template}

    return mocker.patch("app.service_api_client.get_service_template", side_effect=_get)


@pytest.fixture(scope="function")
def mock_get_template_version(notify_admin, mocker, api_user_active):
    def _get(service_id, template_id, version):
        template_version = template_version_json(service_id, template_id, api_user_active, version=version)
        return {"data": template_version}

    return mocker.patch("app.service_api_client.get_service_template", side_effect=_get)


@pytest.fixture(scope="function")
def mock_get_template_versions(notify_admin, mocker, api_user_active):
    def _get(service_id, template_id):
        template_version = template_version_json(service_id, template_id, api_user_active, version=1)
        return {"data": [template_version]}

    return mocker.patch("app.service_api_client.get_service_template_versions", side_effect=_get)


@pytest.fixture(scope="function")
def mock_get_service_template_with_placeholders(notify_admin, mocker):
    def _get(service_id, template_id, version=None):
        template = template_json(
            service_id=service_id,
            id_=template_id,
            name="Two week reminder",
            type_="sms",
            content="((name)), Template <em>content</em> with & entity",
        )
        return {"data": template}

    return mocker.patch("app.service_api_client.get_service_template", side_effect=_get)


@pytest.fixture(scope="function")
def mock_get_empty_service_template_with_optional_placeholder(notify_admin, mocker):
    def _get(service_id, template_id, version=None):
        template = template_json(
            service_id=service_id,
            id_=template_id,
            name="Optional content",
            content="((show_placeholder??Some content))",
        )
        return {"data": template}

    return mocker.patch("app.service_api_client.get_service_template", side_effect=_get)


@pytest.fixture(scope="function")
def mock_get_service_template_with_multiple_placeholders(notify_admin, mocker):
    def _get(service_id, template_id, version=None):
        template = template_json(
            service_id=service_id,
            id_=template_id,
            name="Two week reminder",
            type_="sms",
            content="((one)) ((two)) ((three))",
        )
        return {"data": template}

    return mocker.patch("app.service_api_client.get_service_template", side_effect=_get)


@pytest.fixture(scope="function")
def mock_get_service_template_with_placeholders_same_as_recipient(notify_admin, mocker):
    def _get(service_id, template_id, version=None):
        template = template_json(
            service_id=service_id,
            id_=template_id,
            name="Two week reminder",
            type_="sms",
            content="((name)) ((date)) ((PHONENUMBER))",
        )
        return {"data": template}

    return mocker.patch("app.service_api_client.get_service_template", side_effect=_get)


@pytest.fixture(scope="function")
def mock_get_service_email_template(notify_admin, mocker):
    def _get(service_id, template_id, version=None):
        template = template_json(
            service_id=service_id,
            id_=template_id,
            name="Two week reminder",
            type_="email",
            content="Your vehicle tax expires on ((date))",
            subject="Your ((thing)) is due soon",
            redact_personalisation=False,
        )
        return {"data": template}

    return mocker.patch("app.service_api_client.get_service_template", side_effect=_get)


@pytest.fixture(scope="function")
def mock_get_service_email_template_without_placeholders(notify_admin, mocker):
    def _get(service_id, template_id, version=None):
        template = template_json(
            service_id=service_id,
            id_=template_id,
            name="Two week reminder",
            type_="email",
            content="Your vehicle tax expires soon",
            subject="Your thing is due soon",
            redact_personalisation=False,
        )
        return {"data": template}

    return mocker.patch("app.service_api_client.get_service_template", side_effect=_get)


@pytest.fixture(scope="function")
def mock_get_service_letter_template(notify_admin, mocker):
    def _get(service_id, template_id, version=None, postage="second"):
        template = template_json(
            service_id=service_id,
            id_=template_id,
            name="Two week reminder",
            type_="letter",
            content="Template <em>content</em> with & entity",
            subject="Subject",
            postage=postage,
        )
        return {"data": template}

    return mocker.patch("app.service_api_client.get_service_template", side_effect=_get)


@pytest.fixture(scope="function")
def mock_get_service_letter_template_welsh_language(notify_admin, mocker):
    def _get(service_id, template_id, version=None, postage="second"):
        template = template_json(
            service_id=service_id,
            id_=template_id,
            name="Two week reminder",
            type_="letter",
            content="Template <em>content</em> with & entity",
            subject="Subject",
            postage=postage,
            letter_languages=LetterLanguageOptions.welsh_then_english.value,
            letter_welsh_subject="Pennawd y llythyr",
            letter_welsh_content="Corff y llythyr",
        )
        return {"data": template}

    return mocker.patch("app.service_api_client.get_service_template", side_effect=_get)


@pytest.fixture(scope="function")
def mock_get_service_letter_template_with_attachment(notify_admin, mocker):
    def _get(service_id, template_id, version=None, postage="second"):
        template = template_json(
            service_id=service_id,
            id_=template_id,
            name="Two week reminder",
            type_="letter",
            content="Template <em>content</em> with & entity",
            subject="Subject",
            postage=postage,
            letter_attachment={
                "id": sample_uuid(),
                "original_filename": "original file.pdf",
                "page_count": 1,
            },
        )
        return {"data": template}

    return mocker.patch("app.service_api_client.get_service_template", side_effect=_get)


@pytest.fixture(scope="function")
def mock_get_service_letter_template_with_placeholders(notify_admin, mocker):
    def _get(service_id, template_id, version=None, postage="second"):
        template = template_json(
            service_id=service_id,
            id_=template_id,
            name="Two week reminder",
            type_="letter",
            content="Hello ((name)) your thing is due on ((date))",
            subject="Subject",
            postage=postage,
        )
        return {"data": template}

    return mocker.patch("app.service_api_client.get_service_template", side_effect=_get)


@pytest.fixture(scope="function")
def mock_get_service_letter_template_with_qr_placeholder(notify_admin, mocker):
    def _get(service_id, template_id, version=None, postage="second"):
        template = template_json(
            service_id=service_id,
            id_=template_id,
            name="QR code",
            type_="letter",
            content="qr: ((data))",
            subject="Subject",
            postage=postage,
        )
        return {"data": template}

    return mocker.patch("app.service_api_client.get_service_template", side_effect=_get)


@pytest.fixture(scope="function")
def mock_create_service_template(notify_admin, mocker, fake_uuid):
    def _create(
        *,
        name,
        type_,
        content,
        service_id,
        subject=None,
        parent_folder_id=None,
        letter_languages: LetterLanguageOptions | None = None,
        letter_welsh_subject: str = None,
        letter_welsh_content: str = None,
        has_unsubscribe_link: bool | None = None,
    ):
        template = template_json(
            service_id=service_id,
            id_=fake_uuid,
            name=name,
            type_=type_,
            content=content,
            folder=parent_folder_id,
            has_unsubscribe_link=has_unsubscribe_link,
        )
        return {"data": template}

    return mocker.patch("app.service_api_client.create_service_template", side_effect=_create)


@pytest.fixture(scope="function")
def mock_update_service_template(notify_admin, mocker):
    def _update(
        *,
        service_id,
        template_id,
        name=None,
        content=None,
        subject=None,
        letter_welsh_subject=None,
        letter_welsh_content=None,
        has_unsubscribe_link=False,
    ):
        template = template_json(
            service_id=service_id,
            id_=template_id,
            name=name,
            content=content,
            subject=subject,
            letter_welsh_subject=None,
            letter_welsh_content=None,
            has_unsubscribe_link=has_unsubscribe_link,
        )
        return {"data": template}

    return mocker.patch("app.service_api_client.update_service_template", side_effect=_update)


@pytest.fixture(scope="function")
def mock_create_service_template_content_too_big(notify_admin, mocker):
    def _create(
        *,
        name,
        type_,
        content,
        service_id,
        subject=None,
        parent_folder_id=None,
        has_unsubscribe_link=None,
    ):
        json_mock = Mock(
            return_value={
                "message": {"content": ["Content has a character count greater than the limit of 459"]},
                "result": "error",
            }
        )
        resp_mock = Mock(status_code=400, json=json_mock)
        http_error = HTTPError(
            response=resp_mock, message={"content": ["Content has a character count greater than the limit of 459"]}
        )
        raise http_error

    return mocker.patch("app.service_api_client.create_service_template", side_effect=_create)


@pytest.fixture(scope="function")
def mock_update_service_template_400_content_too_big(notify_admin, mocker):
    def _update(*, service_id, template_id, name=None, content=None, subject=None):
        json_mock = Mock(
            return_value={
                "message": {"content": ["Content has a character count greater than the limit of 459"]},
                "result": "error",
            }
        )
        resp_mock = Mock(status_code=400, json=json_mock)
        http_error = HTTPError(
            response=resp_mock, message={"content": ["Content has a character count greater than the limit of 459"]}
        )
        raise http_error

    return mocker.patch("app.service_api_client.update_service_template", side_effect=_update)


@pytest.fixture(scope="function")
def mock_update_service_template_400_qr_code_too_big(notify_admin, mocker):
    def _update(*, service_id, template_id, name=None, content=None, subject=None):
        json_mock = Mock(
            return_value={
                "message": {"content": ["qr-code-too-long"]},
                "result": "error",
            }
        )
        resp_mock = Mock(status_code=400, json=json_mock)
        http_error = HTTPError(response=resp_mock, message={"content": ["qr-code-too-long"]})
        raise http_error

    return mocker.patch("app.service_api_client.update_service_template", side_effect=_update)


def create_service_templates(service_id, number_of_templates=6):
    template_types = ["sms", "sms", "email", "email", "letter", "letter"]
    service_templates = []

    for _ in range(1, number_of_templates + 1):
        template_number = "two" if _ % 2 == 0 else "one"
        template_type = template_types[(_ % 6) - 1]

        service_templates.append(
            template_json(
                service_id=service_id,
                id_=TEMPLATE_ONE_ID if _ == 1 else str(generate_uuid()),
                name=f"{template_type}_template_{template_number}",
                type_=template_type,
                content=f"{template_type} template {template_number} content",
                subject=(
                    f"{template_type} template {template_number} subject"
                    if template_type in ["email", "letter"]
                    else None
                ),
            )
        )

    return {"data": service_templates}


def _template(template_type, name, parent=None, template_id=None):
    return {
        "id": template_id or str(uuid4()),
        "name": name,
        "template_type": template_type,
        "folder": parent,
        "content": "foo",
    }


@pytest.fixture(scope="function")
def mock_get_service_templates(notify_admin, mocker):
    def _create(service_id):
        return create_service_templates(service_id)

    return mocker.patch("app.service_api_client.get_service_templates", side_effect=_create)


@pytest.fixture(scope="function")
def mock_get_more_service_templates_than_can_fit_onscreen(notify_admin, mocker):
    def _create(service_id):
        return create_service_templates(service_id, number_of_templates=20)

    return mocker.patch("app.service_api_client.get_service_templates", side_effect=_create)


@pytest.fixture(scope="function")
def mock_get_service_templates_when_no_templates_exist(notify_admin, mocker):
    def _create(service_id):
        return {"data": []}

    return mocker.patch("app.service_api_client.get_service_templates", side_effect=_create)


@pytest.fixture(scope="function")
def mock_get_service_templates_with_only_one_template(notify_admin, mocker):
    def _get(service_id):
        return {
            "data": [
                template_json(
                    service_id=service_id,
                    id_=generate_uuid(),
                    name="sms_template_one",
                    type_="sms",
                    content="sms template one content",
                )
            ]
        }

    return mocker.patch("app.service_api_client.get_service_templates", side_effect=_get)


@pytest.fixture(scope="function")
def mock_delete_service_template(notify_admin, mocker):
    def _delete(service_id, template_id):
        template = template_json(
            service_id=service_id,
            id_=template_id,
            name="Template to delete",
            type_="sms",
            content="content to be deleted",
        )
        return {"data": template}

    return mocker.patch("app.service_api_client.delete_service_template", side_effect=_delete)


@pytest.fixture(scope="function")
def mock_redact_template(notify_admin, mocker):
    return mocker.patch("app.service_api_client.redact_service_template")


@pytest.fixture(scope="function")
def mock_update_service_template_sender(notify_admin, mocker):
    def _update(service_id, template_id, reply_to):
        return

    return mocker.patch("app.service_api_client.update_service_template_sender", side_effect=_update)


@pytest.fixture(scope="function")
def api_user_pending(fake_uuid):
    return create_user(id=fake_uuid, state="pending")


@pytest.fixture(scope="function")
def platform_admin_user(fake_uuid):
    return create_platform_admin_user(
        permissions={
            SERVICE_ONE_ID: [
                "send_texts",
                "send_emails",
                "send_letters",
                "manage_users",
                "manage_templates",
                "manage_settings",
                "manage_api_keys",
                "view_activity",
            ]
        }
    )


@pytest.fixture(scope="function")
def api_user_active():
    return create_api_user_active()


@pytest.fixture(scope="function")
def api_user_active_email_auth(fake_uuid):
    return create_user(id=fake_uuid, auth_type="email_auth")


@pytest.fixture(scope="function")
def active_user_with_permissions_no_mobile(fake_uuid):
    return create_service_one_admin(
        id=fake_uuid,
        mobile_number=None,
    )


@pytest.fixture(scope="function")
def api_nongov_user_active(fake_uuid):
    return create_service_one_admin(
        id=fake_uuid,
        email_address="someuser@example.com",
    )


@pytest.fixture(scope="function")
def active_user_with_permissions(fake_uuid):
    return create_active_user_with_permissions()


@pytest.fixture(scope="function")
def active_user_with_permission_to_two_services(fake_uuid):
    permissions = [
        "send_texts",
        "send_emails",
        "send_letters",
        "manage_users",
        "manage_templates",
        "manage_settings",
        "manage_api_keys",
        "view_activity",
    ]

    return create_user(
        id=fake_uuid,
        permissions={
            SERVICE_ONE_ID: permissions,
            SERVICE_TWO_ID: permissions,
        },
        organisations=[ORGANISATION_ID],
        services=[SERVICE_ONE_ID, SERVICE_TWO_ID],
    )


@pytest.fixture(scope="function")
def active_user_with_permission_to_other_service(active_user_with_permission_to_two_services):
    active_user_with_permission_to_two_services["permissions"].pop(SERVICE_ONE_ID)
    active_user_with_permission_to_two_services["services"].pop(0)
    active_user_with_permission_to_two_services["name"] = "Service Two User"
    active_user_with_permission_to_two_services["email_address"] = "service-two-user@test.gov.uk"
    return active_user_with_permission_to_two_services


@pytest.fixture(scope="function")
def active_caseworking_user():
    return create_active_caseworking_user()


@pytest.fixture
def active_user_view_permissions():
    return create_active_user_view_permissions()


@pytest.fixture
def active_user_no_settings_permission():
    return create_active_user_no_settings_permission()


@pytest.fixture(scope="function")
def api_user_locked(fake_uuid):
    return create_user(
        id=fake_uuid,
        failed_login_count=5,
        password_changed_at=None,
    )


@pytest.fixture(scope="function")
def api_user_request_password_reset(fake_uuid):
    return create_user(
        id=fake_uuid,
        failed_login_count=5,
    )


@pytest.fixture(scope="function")
def api_user_changed_password(fake_uuid):
    return create_user(
        id=fake_uuid,
        failed_login_count=5,
        password_changed_at=str(datetime.utcnow() + timedelta(minutes=1)),
    )


@pytest.fixture(scope="function")
def mock_send_change_email_verification(notify_admin, mocker):
    return mocker.patch("app.user_api_client.send_change_email_verification")


@pytest.fixture(scope="function")
def mock_register_user(notify_admin, mocker, api_user_pending):
    def _register(name, email_address, mobile_number, password, auth_type):
        api_user_pending["name"] = name
        api_user_pending["email_address"] = email_address
        api_user_pending["mobile_number"] = mobile_number
        api_user_pending["password"] = password
        api_user_pending["auth_type"] = auth_type
        return api_user_pending

    return mocker.patch("app.user_api_client.register_user", side_effect=_register)


@pytest.fixture(scope="function")
def login_non_govuser(client_request, api_user_active):
    api_user_active["email_address"] = "someuser@example.com"

    client_request.login(api_user_active)


@pytest.fixture(scope="function")
def mock_get_user(notify_admin, mocker, api_user_active):
    def _get_user(id_):
        api_user_active["id"] = id_
        return api_user_active

    return mocker.patch("app.user_api_client.get_user", side_effect=_get_user)


@pytest.fixture(scope="function")
def mock_get_locked_user(notify_admin, mocker, api_user_locked):
    def _get_user(id_):
        api_user_locked["id"] = id_
        return api_user_locked

    return mocker.patch("app.user_api_client.get_user", side_effect=_get_user)


@pytest.fixture(scope="function")
def mock_get_user_pending(notify_admin, mocker, api_user_pending):
    return mocker.patch("app.user_api_client.get_user", return_value=api_user_pending)


@pytest.fixture(scope="function")
def mock_get_user_by_email(notify_admin, mocker, api_user_active):
    def _get_user(email_address):
        api_user_active["email_address"] = email_address
        return api_user_active

    return mocker.patch("app.user_api_client.get_user_by_email", side_effect=_get_user)


@pytest.fixture(scope="function")
def mock_dont_get_user_by_email(notify_admin, mocker):
    def _get_user(email_address):
        return None

    return mocker.patch("app.user_api_client.get_user_by_email", side_effect=_get_user, autospec=True)


@pytest.fixture(scope="function")
def mock_get_user_by_email_request_password_reset(notify_admin, mocker, api_user_request_password_reset):
    return mocker.patch("app.user_api_client.get_user_by_email", return_value=api_user_request_password_reset)


@pytest.fixture(scope="function")
def mock_get_user_by_email_user_changed_password(notify_admin, mocker, api_user_changed_password):
    return mocker.patch("app.user_api_client.get_user_by_email", return_value=api_user_changed_password)


@pytest.fixture(scope="function")
def mock_get_user_by_email_locked(notify_admin, mocker, api_user_locked):
    return mocker.patch("app.user_api_client.get_user_by_email", return_value=api_user_locked)


@pytest.fixture(scope="function")
def mock_get_user_by_email_pending(notify_admin, mocker, api_user_pending):
    return mocker.patch("app.user_api_client.get_user_by_email", return_value=api_user_pending)


@pytest.fixture(scope="function")
def mock_get_user_by_email_not_found(notify_admin, mocker, api_user_active):
    def _get_user(email):
        json_mock = Mock(return_value={"message": "Not found", "result": "error"})
        resp_mock = Mock(status_code=404, json=json_mock)
        http_error = HTTPError(response=resp_mock, message="Default message")
        raise http_error

    return mocker.patch("app.user_api_client.get_user_by_email", side_effect=_get_user)


@pytest.fixture(scope="function")
def mock_verify_password(notify_admin, mocker):
    def _verify_password(user, password):
        return True

    return mocker.patch("app.user_api_client.verify_password", side_effect=_verify_password)


@pytest.fixture(scope="function")
def mock_update_user_password(notify_admin, mocker, api_user_active):
    def _update(user_id, password):
        api_user_active["id"] = user_id
        return api_user_active

    return mocker.patch("app.user_api_client.update_password", side_effect=_update)


@pytest.fixture(scope="function")
def mock_update_user_attribute(notify_admin, mocker, api_user_active):
    def _update(user_id, **kwargs):
        api_user_active["id"] = user_id
        return api_user_active

    return mocker.patch("app.user_api_client.update_user_attribute", side_effect=_update)


@pytest.fixture
def mock_activate_user(notify_admin, mocker, api_user_active):
    def _activate(user_id):
        api_user_active["id"] = user_id
        return {"data": api_user_active}

    return mocker.patch("app.user_api_client.activate_user", side_effect=_activate)


@pytest.fixture(scope="function")
def mock_email_is_not_already_in_use(notify_admin, mocker):
    return mocker.patch("app.user_api_client.get_user_by_email_or_none", return_value=None)


@pytest.fixture(scope="function")
def mock_revoke_api_key(notify_admin, mocker):
    def _revoke(service_id, key_id):
        return {}

    return mocker.patch("app.models.api_key.api_key_api_client.revoke_api_key", side_effect=_revoke)


@pytest.fixture(scope="function")
def mock_get_api_keys(notify_admin, mocker, fake_uuid):
    def _get_keys(service_id, key_id=None):
        keys = {
            "apiKeys": [
                api_key_json(id_=fake_uuid, name="some key name", key_type="normal"),
                api_key_json(
                    id_="1234567",
                    name="another key name",
                    expiry_date=str(date.fromtimestamp(0)),
                    key_type="test",
                ),
                api_key_json(
                    id_=str(uuid4()),
                    name="third key",
                    key_type="team",
                ),
            ]
        }
        return keys

    return mocker.patch("app.models.api_key.api_key_api_client.get_api_keys", side_effect=_get_keys)


@pytest.fixture(scope="function")
def mock_get_no_api_keys(notify_admin, mocker):
    def _get_keys(service_id):
        keys = {"apiKeys": []}
        return keys

    return mocker.patch("app.models.api_key.api_key_api_client.get_api_keys", side_effect=_get_keys)


@pytest.fixture(scope="function")
def mock_login(notify_admin, mocker, mock_get_user, mock_update_user_attribute, mock_events):
    def _verify_code(user_id, code, code_type):
        return True, ""

    def _no_services(params_dict=None):
        return {"data": []}

    return (
        mocker.patch("app.user_api_client.check_verify_code", side_effect=_verify_code),
        mocker.patch("app.service_api_client.get_services", side_effect=_no_services),
    )


@pytest.fixture(scope="function")
def mock_send_verify_code(notify_admin, mocker):
    return mocker.patch("app.user_api_client.send_verify_code")


@pytest.fixture(scope="function")
def mock_send_verify_email(notify_admin, mocker):
    return mocker.patch("app.user_api_client.send_verify_email")


@pytest.fixture(scope="function")
def mock_check_verify_code(notify_admin, mocker):
    def _verify(user_id, code, code_type):
        return True, ""

    return mocker.patch("app.user_api_client.check_verify_code", side_effect=_verify)


@pytest.fixture(scope="function")
def mock_check_verify_code_code_not_found(notify_admin, mocker):
    def _verify(user_id, code, code_type):
        return False, "Code not found"

    return mocker.patch("app.user_api_client.check_verify_code", side_effect=_verify)


@pytest.fixture(scope="function")
def mock_check_verify_code_code_expired(notify_admin, mocker):
    def _verify(user_id, code, code_type):
        return False, "Code has expired"

    return mocker.patch("app.user_api_client.check_verify_code", side_effect=_verify)


@pytest.fixture(scope="function")
def mock_create_job(notify_admin, mocker, api_user_active):
    def _create(job_id, service_id, scheduled_for=None, contact_list_id=None):
        return job_json(
            service_id,
            api_user_active,
            job_id=job_id,
        )

    return mocker.patch("app.job_api_client.create_job", side_effect=_create)


@pytest.fixture(scope="function")
def mock_get_job(notify_admin, mocker, api_user_active):
    def _get_job(service_id, job_id):
        return {"data": job_json(service_id, api_user_active, job_id=job_id)}

    return mocker.patch("app.job_api_client.get_job", side_effect=_get_job)


@pytest.fixture(scope="function")
def mock_get_letter_job(notify_admin, mocker, api_user_active):
    def _get_job(service_id, job_id):
        return {"data": job_json(service_id, api_user_active, job_id=job_id, template_type="letter")}

    return mocker.patch("app.job_api_client.get_job", side_effect=_get_job)


@pytest.fixture
def mock_get_job_doesnt_exist(notify_admin, mocker):
    def _get_job(service_id, job_id):
        raise HTTPError(response=Mock(status_code=404, json={}), message={})

    return mocker.patch("app.job_api_client.get_job", side_effect=_get_job)


@pytest.fixture(scope="function")
def mock_get_scheduled_job(notify_admin, mocker, api_user_active):
    def _get_job(service_id, job_id):
        return {
            "data": job_json(
                service_id,
                api_user_active,
                job_id=job_id,
                job_status="scheduled",
                scheduled_for="2016-01-02T00:00:00.061258",
            )
        }

    return mocker.patch("app.job_api_client.get_job", side_effect=_get_job)


@pytest.fixture(scope="function")
def mock_get_cancelled_job(notify_admin, mocker, api_user_active):
    def _get_job(service_id, job_id):
        return {
            "data": job_json(
                service_id,
                api_user_active,
                job_id=job_id,
                job_status="cancelled",
                scheduled_for="2016-01-01T00:00:00.061258",
            )
        }

    return mocker.patch("app.job_api_client.get_job", side_effect=_get_job)


@pytest.fixture(scope="function")
def mock_get_job_in_progress(notify_admin, mocker, api_user_active):
    def _get_job(service_id, job_id):
        return {
            "data": job_json(
                service_id,
                api_user_active,
                job_id=job_id,
                notification_count=10,
                notifications_requested=5,
                job_status="processing",
            )
        }

    return mocker.patch("app.job_api_client.get_job", side_effect=_get_job)


@pytest.fixture(scope="function")
def mock_get_job_with_sending_limits_exceeded(notify_admin, mocker, api_user_active):
    def _get_job(service_id, job_id):
        return {
            "data": job_json(
                service_id,
                api_user_active,
                job_id=job_id,
                notification_count=10,
                notifications_requested=5,
                job_status="sending limits exceeded",
            )
        }

    return mocker.patch("app.job_api_client.get_job", side_effect=_get_job)


@pytest.fixture(scope="function")
def mock_get_letter_job_in_progress(notify_admin, mocker, api_user_active):
    def _get_job(service_id, job_id):
        return {
            "data": job_json(
                service_id,
                api_user_active,
                job_id=job_id,
                notification_count=10,
                notifications_requested=5,
                job_status="processing",
                template_type="letter",
            )
        }

    return mocker.patch("app.job_api_client.get_job", side_effect=_get_job)


@pytest.fixture(scope="function")
def mock_has_jobs(notify_admin, mocker):
    return mocker.patch("app.job_api_client.has_jobs", return_value=True)


@pytest.fixture(scope="function")
def mock_has_no_jobs(notify_admin, mocker):
    return mocker.patch("app.job_api_client.has_jobs", return_value=False)


@pytest.fixture(scope="function")
def mock_get_jobs(notify_admin, mocker, api_user_active, fake_uuid):
    def _get_jobs(service_id, limit_days=None, statuses=None, contact_list_id=None, page=1):
        if statuses is None:
            statuses = ["", "scheduled", "pending", "cancelled", "finished", "finished all notifications created"]

        jobs = [
            job_json(
                service_id,
                api_user_active,
                job_id=fake_uuid,
                original_file_name=filename,
                scheduled_for=scheduled_for,
                job_status=job_status,
                template_version=template_version,
                template_name=template_name,
            )
            for filename, scheduled_for, job_status, template_name, template_version in (
                ("full_of_regret.csv", "2016-01-01 23:09:00.061258", "cancelled", "Template X", 1),
                ("even_later.csv", "2016-01-01 23:09:00.061258", "scheduled", "Template Y", 1),
                ("send_me_later.csv", "2016-01-01 11:09:00.061258", "scheduled", "Template Z", 1),
                ("export 1/1/2016.xls", None, "finished", "Template A", 1),
                ("all email addresses.xlsx", None, "pending", "Template B", 1),
                ("applicants.ods", None, "finished", "Template C", 1),
                ("thisisatest.csv", None, "finished all notifications created", "Template D", 2),
            )
        ]
        return {
            "data": [job for job in jobs if job["job_status"] in statuses],
            "links": {
                "prev": f"services/{service_id}/jobs?page={page - 1}",
                "next": f"services/{service_id}/jobs?page={page + 1}",
            },
        }

    return mocker.patch("app.job_api_client.get_jobs", side_effect=_get_jobs)


@pytest.fixture(scope="function")
def mock_get_scheduled_job_stats(notify_admin, mocker, api_user_active):
    return mocker.patch(
        "app.job_api_client.get_scheduled_job_stats",
        return_value={
            # These values match the return value of `mock_get_jobs`
            "count": 2,
            "soonest_scheduled_for": "2016-01-01 11:09:00",
        },
    )


@pytest.fixture(scope="function")
def mock_get_uploads(mocker, api_user_active):
    def _get_uploads(service_id, limit_days=None, statuses=None, page=1):
        uploads = [
            {
                "id": None,
                "original_file_name": "Uploaded letters",
                "recipient": None,
                "notification_count": 33,
                "template_type": "letter",
                "created_at": "2017-10-10 16:30:00",
                "statistics": [],
                "upload_type": "letter_day",
            },
            {
                "id": "job_id_1",
                "original_file_name": "some.csv",
                "notification_count": 10,
                "created_at": "2016-01-01 11:09:00.061258",
                "statistics": [{"count": 8, "status": "delivered"}, {"count": 2, "status": "temporary-failure"}],
                "upload_type": "job",
                "template_type": "sms",
                "recipient": None,
            },
            {
                "id": "letter_id_1",
                "original_file_name": "some.pdf",
                "notification_count": 1,
                "created_at": "2016-01-01 11:09:00.061258",
                "statistics": [{"count": 1, "status": "delivered"}],
                "upload_type": "letter",
                "template_type": None,
                "recipient": "Firstname Lastname\n123 Example Street\nCity of Town\nXM4 5QQ",
            },
        ]
        return {
            "data": uploads,
            "links": {
                "prev": f"services/{service_id}/uploads?page={page - 1}",
                "next": f"services/{service_id}/uploads?page={page + 1}",
            },
        }

    # Why is mocking on the model needed?
    return mocker.patch("app.models.job.PaginatedUploads._get_items", side_effect=_get_uploads)


@pytest.fixture(scope="function")
def mock_get_uploaded_letters(notify_admin, mocker):
    def _get_uploaded_letters(service_id, *, letter_print_day, page=1):
        uploads = [
            {
                "api_key": None,
                "billable_units": 1,
                "client_reference": "Homer-Simpson.pdf",
                "created_at": "2020-02-02T13:59:00+00:00",
                "created_by": {
                    "email_address": "test@example.com",
                    "id": "a1958d6b-955b-4f68-8847-cf43cd4b189a",
                    "name": "Test User",
                },
                "document_download_count": None,
                "id": "03e34025-be54-4d43-8e6a-fb1ea0fd1f29",
                "international": False,
                "job": None,
                "job_row_number": None,
                "key_name": None,
                "key_type": "normal",
                "normalised_to": None,
                "notification_type": "letter",
                "personalisation": {},
                "phone_prefix": None,
                "postage": "second",
                "rate_multiplier": None,
                "reference": "dvla-reference",
                "reply_to_text": None,
                "sent_at": "2020-02-02T14:00:00+00:00",
                "sent_by": None,
                "service": "f995d8a3-4ece-4961-bbbd-b657b192648c",
                "status": "delivered",
                "template": {
                    "content": "",
                    "id": "673e4f67-7d9a-42b8-8e56-f3444aa2fbef",
                    "is_precompiled_letter": True,
                    "name": "Pre-compiled PDF",
                    "redact_personalisation": False,
                    "subject": "Pre-compiled PDF",
                    "template_type": "letter",
                    "version": 1,
                },
                "to": "742 Evergreen Terrace",
                "updated_at": "2020-02-02T14:00:00+00:00",
            },
            {
                "api_key": None,
                "billable_units": 1,
                "client_reference": "Kevin-McCallister.pdf",
                "created_at": "2020-02-02T12:59:00+00:00",
                "created_by": {
                    "email_address": "test@example.com",
                    "id": "a1958d6b-955b-4f68-8847-cf43cd4b189a",
                    "name": "Test User",
                },
                "document_download_count": None,
                "id": "fc090d91-e761-4464-9041-9c4594c96a35",
                "international": False,
                "job": None,
                "job_row_number": None,
                "key_name": None,
                "key_type": "normal",
                "normalised_to": None,
                "notification_type": "letter",
                "personalisation": {},
                "phone_prefix": None,
                "postage": "second",
                "rate_multiplier": None,
                "reference": "dvla-reference",
                "reply_to_text": None,
                "sent_at": "2020-02-02T14:00:00+00:00",
                "sent_by": None,
                "service": "f995d8a3-4ece-4961-bbbd-b657b192648c",
                "status": "delivered",
                "template": {
                    "content": "",
                    "id": "673e4f67-7d9a-42b8-8e56-f3444aa2fbef",
                    "is_precompiled_letter": True,
                    "name": "Pre-compiled PDF",
                    "redact_personalisation": False,
                    "subject": "Pre-compiled PDF",
                    "template_type": "letter",
                    "version": 1,
                },
                "to": "671 Lincoln Avenue\nWinnetka",
                "updated_at": "2020-02-02T14:00:00+00:00",
            },
        ]
        return {
            "notifications": uploads,
            "total": 1234,
            "links": {
                "prev": f"services/{service_id}/uploads?page={page - 1}",
                "next": f"services/{service_id}/uploads?page={page + 1}",
            },
        }

    return mocker.patch(
        "app.main.views_nl.uploads.upload_api_client.get_letters_by_service_and_print_day",
        side_effect=_get_uploaded_letters,
    )


@pytest.fixture(scope="function")
def mock_get_no_uploaded_letters(notify_admin, mocker):
    return mocker.patch(
        "app.main.views_nl.uploads.upload_api_client.get_letters_by_service_and_print_day",
        return_value={"notifications": [], "total": 0, "links": {}},
    )


@pytest.fixture(scope="function")
def mock_get_no_uploads(mocker, api_user_active):
    mocker.patch(
        "app.models.job.PaginatedUploads._get_items",
        return_value={
            "data": [],
        },
    )


@pytest.fixture(scope="function")
def mock_get_no_jobs(mocker, api_user_active):
    return mocker.patch(
        "app.models.job.PaginatedJobs._get_items",
        return_value={
            "data": [],
            "links": {},
        },
    )


@pytest.fixture(scope="function")
def mock_create_contact_list(notify_admin, mocker, api_user_active):
    def _create(
        service_id,
        upload_id,
        original_file_name,
        row_count,
        template_type,
    ):
        return {
            "service_id": service_id,
            "upload_id": upload_id,
            "original_file_name": original_file_name,
            "row_count": row_count,
            "template_type": template_type,
        }

    return mocker.patch(
        "app.contact_list_api_client.create_contact_list",
        side_effect=_create,
    )


@pytest.fixture(scope="function")
def mock_get_contact_lists(mocker, api_user_active, fake_uuid):
    def _get(service_id, template_type=None):
        return [
            contact_list_json(
                id_=fake_uuid,
                created_at="2020-06-13T09:59:56.000000Z",
                service_id=service_id,
            ),
            contact_list_json(
                id_="d7b0bd1a-d1c7-4621-be5c-3c1b4278a2ad",
                created_at="2020-06-13T12:00:00.000000Z",
                service_id=service_id,
                original_file_name="phone number list.csv",
                row_count=123,
                recent_job_count=2,
                template_type="sms",
            ),
            contact_list_json(
                id_=fake_uuid,
                created_at="2020-05-02T01:00:00.000000Z",
                original_file_name="UnusedList.tsv",
                row_count=1,
                has_jobs=False,
                service_id=service_id,
                template_type="sms",
            ),
        ]

    return mocker.patch(
        "app.models.contact_list.ContactLists._get_items",
        side_effect=_get,
    )


@pytest.fixture(scope="function")
def mock_get_contact_list(notify_admin, mocker, api_user_active, fake_uuid):
    def _get(*, service_id, contact_list_id):
        return contact_list_json(
            id_=fake_uuid,
            created_at="2020-06-13T09:59:56.000000Z",
            service_id=service_id,
        )

    return mocker.patch(
        "app.models.contact_list.contact_list_api_client.get_contact_list",
        side_effect=_get,
    )


@pytest.fixture(scope="function")
def mock_get_no_contact_list(notify_admin, mocker, api_user_active, fake_uuid):
    def _get(*, service_id, contact_list_id):
        raise HTTPError(response=Mock(status_code=404))

    return mocker.patch(
        "app.models.contact_list.contact_list_api_client.get_contact_list",
        side_effect=_get,
    )


@pytest.fixture(scope="function")
def mock_get_no_contact_lists(mocker):
    return mocker.patch(
        "app.models.contact_list.ContactLists._get_items",
        return_value=[],
    )


@pytest.fixture(scope="function")
def mock_get_notifications(
    mocker,
    notify_admin,
    api_user_active,
):
    def _get_notifications(
        service_id,
        job_id=None,
        page=1,
        page_size=50,
        count_pages=None,
        template_type=None,
        status=None,
        limit_days=None,
        rows=5,
        include_jobs=None,
        include_from_test_key=None,
        to=None,
        include_one_off=None,
    ):
        job = None
        if job_id is not None:
            job = job_json(service_id, api_user_active, job_id=job_id)
        if template_type:
            template = template_json(
                service_id=service_id,
                id_=str(generate_uuid()),
                type_=template_type[0],
                redact_personalisation=False,
                is_precompiled_letter=False,
            )
        else:
            template = template_json(
                service_id=service_id,
                id_=str(generate_uuid()),
                redact_personalisation=False,
            )
        return notification_json(
            service_id,
            template=template,
            rows=rows,
            job=job,
            with_links=True if count_pages is None else count_pages,
            created_by_name="Firstname Lastname",
        )

    return mocker.patch("app.models.notification.Notifications._get_items", side_effect=_get_notifications)


@pytest.fixture(scope="function")
def mock_get_notifications_with_previous_next(notify_admin, mocker):
    def _get_notifications(
        service_id,
        job_id=None,
        page=1,
        count_pages=None,
        template_type=None,
        status=None,
        limit_days=None,
        include_jobs=None,
        include_from_test_key=None,
        to=None,
        include_one_off=None,
    ):
        return notification_json(service_id, rows=50, with_links=True if count_pages is None else count_pages)

    return mocker.patch("app.models.notification.Notifications._get_items", side_effect=_get_notifications)


@pytest.fixture(scope="function")
def mock_get_notifications_with_no_notifications(notify_admin, mocker):
    def _get_notifications(
        service_id,
        job_id=None,
        page=1,
        count_pages=None,
        template_type=None,
        status=None,
        limit_days=None,
        include_jobs=None,
        include_from_test_key=None,
        to=None,
        include_one_off=None,
    ):
        return notification_json(service_id, rows=0)

    return mocker.patch("app.models.notification.Notifications._get_items", side_effect=_get_notifications)


@pytest.fixture(scope="function")
def mock_get_inbound_sms(notify_admin, mocker):
    def _get_inbound_sms(service_id, user_number=None, page=1):
        return inbound_sms_json()

    return mocker.patch(
        "app.models.notification.InboundSMSMessages._get_items",
        side_effect=_get_inbound_sms,
    )


@pytest.fixture
def mock_get_inbound_sms_by_id_with_no_messages(notify_admin, mocker):
    def _get_inbound_sms_by_id(service_id, notification_id):
        raise HTTPError(response=Mock(status_code=404))

    return mocker.patch(
        "app.service_api_client.get_inbound_sms_by_id",
        side_effect=_get_inbound_sms_by_id,
    )


@pytest.fixture(scope="function")
def mock_get_most_recent_inbound_sms(notify_admin, mocker):
    def _get_most_recent_inbound_sms(service_id, user_number=None, page=1):
        return inbound_sms_json()

    return mocker.patch(
        "app.service_api_client.get_most_recent_inbound_sms",
        side_effect=_get_most_recent_inbound_sms,
    )


@pytest.fixture(scope="function")
def mock_get_most_recent_inbound_sms_with_no_messages(notify_admin, mocker):
    def _get_most_recent_inbound_sms(service_id, user_number=None, page=1):
        return {"has_next": False, "data": []}

    return mocker.patch(
        "app.service_api_client.get_most_recent_inbound_sms",
        side_effect=_get_most_recent_inbound_sms,
    )


@pytest.fixture(scope="function")
def mock_get_inbound_sms_summary(notify_admin, mocker):
    def _get_inbound_sms_summary(
        service_id,
    ):
        return {"count": 9999, "most_recent": datetime.utcnow().isoformat()}

    return mocker.patch(
        "app.service_api_client.get_inbound_sms_summary",
        side_effect=_get_inbound_sms_summary,
    )


@pytest.fixture(scope="function")
def mock_get_inbound_sms_summary_with_no_messages(notify_admin, mocker):
    def _get_inbound_sms_summary(
        service_id,
    ):
        return {"count": 0, "latest_message": None}

    return mocker.patch(
        "app.service_api_client.get_inbound_sms_summary",
        side_effect=_get_inbound_sms_summary,
    )


@pytest.fixture(scope="function")
def mock_get_most_recent_inbound_usage_date(mocker):
    return mocker.patch(
        "app.service_api_client.get_most_recent_inbound_number_usage_date",
        return_value={"most_recent_date": "2023-12-01T12:00:00Z"},
    )


@pytest.fixture(scope="function")
def mock_get_inbound_number_for_service(notify_admin, mocker):
    return mocker.patch(
        "app.inbound_number_client.get_inbound_sms_number_for_service", return_value={"data": {"number": "07812398712"}}
    )


@pytest.fixture(scope="function")
def mock_no_inbound_number_for_service(notify_admin, mocker):
    return mocker.patch("app.inbound_number_client.get_inbound_sms_number_for_service", return_value={"data": {}})


@pytest.fixture(scope="function")
def mock_has_permissions(mocker):
    def _has_permission(*permissions, restrict_admin_usage=False, allow_org_user=False):
        return True

    return mocker.patch("app.models.user.User.has_permissions", side_effect=_has_permission)


@pytest.fixture(scope="function")
def mock_get_users_by_service(mocker):
    def _get_users_for_service(service_id):
        return [
            create_service_one_admin(
                id=sample_uuid(),
                logged_in_at=None,
                mobile_number="+447700900986",
                email_address="notify@digital.cabinet-office.gov.uk",
            )
        ]

    # You shouldn’t be calling the user API client directly, so it’s the
    # instance on the model that’s mocked here
    return mocker.patch("app.models.user.Users._get_items", side_effect=_get_users_for_service)


@pytest.fixture(scope="function")
def mock_s3_upload(mocker):
    def _upload(service_id, filedata, region):
        return sample_uuid()

    return mocker.patch("app.main.views_nl.send.s3upload", side_effect=_upload)


@pytest.fixture(scope="function")
def mock_s3_download(mocker):
    def _download(service_id, upload_id):
        return """
            phone number,name
            +447700900986,John
            +447700900986,Smith
        """

    return mocker.patch("app.main.views_nl.send.s3download", side_effect=_download)


@pytest.fixture(scope="function")
def mock_s3_get_metadata(mocker):
    def _get_metadata(service_id, upload_id):
        return {"original_file_name": "example.csv"}

    return mocker.patch("app.main.views_nl.send.get_csv_metadata", side_effect=_get_metadata)


@pytest.fixture(scope="function")
def mock_s3_set_metadata(mocker):
    return mocker.patch("app.main.views_nl.send.set_metadata_on_csv_upload")


@pytest.fixture(scope="function")
def sample_invite(mocker, service_one):
    id_ = USER_ONE_ID
    from_user = service_one["users"][0]
    email_address = "invited_user@test.gov.uk"
    service_id = service_one["id"]
    permissions = "view_activity,send_emails,send_letters,send_texts,manage_settings,manage_users,manage_api_keys"
    created_at = str(datetime.utcnow())
    auth_type = "sms_auth"
    folder_permissions = []

    return invite_json(
        id_, from_user, service_id, email_address, permissions, created_at, "pending", auth_type, folder_permissions
    )


@pytest.fixture(scope="function")
def mock_create_invite(notify_admin, mocker, sample_invite):
    def _create_invite(from_user, service_id, email_address, permissions, folder_permissions):
        sample_invite["from_user"] = from_user
        sample_invite["service"] = service_id
        sample_invite["email_address"] = email_address
        sample_invite["status"] = "pending"
        sample_invite["permissions"] = permissions
        sample_invite["folder_permissions"] = folder_permissions
        return sample_invite

    return mocker.patch("app.invite_api_client.create_invite", side_effect=_create_invite)


@pytest.fixture(scope="function")
def mock_get_invites_for_service(mocker, service_one, sample_invite):
    def _get_invites(service_id):
        data = []
        for i in range(5):
            invite = copy.copy(sample_invite)
            invite["email_address"] = f"user_{i}@testnotify.gov.uk"
            data.append(invite)
        return data

    return mocker.patch("app.models.user.InvitedUsers._get_items", side_effect=_get_invites)


@pytest.fixture(scope="function")
def mock_get_invites_without_manage_permission(mocker, service_one, sample_invite):
    def _get_invites(service_id):
        return [
            invite_json(
                id_=str(sample_uuid()),
                from_user=service_one["users"][0],
                email_address="invited_user@test.gov.uk",
                service_id=service_one["id"],
                permissions="view_activity,send_messages,manage_api_keys",
                created_at=str(datetime.utcnow()),
                auth_type="sms_auth",
                folder_permissions=[],
                status="pending",
            )
        ]

    return mocker.patch("app.models.user.InvitedUsers._get_items", side_effect=_get_invites)


@pytest.fixture(scope="function")
def mock_accept_invite(notify_admin, mocker, sample_invite):
    def _accept(service_id, invite_id):
        return sample_invite

    return mocker.patch("app.invite_api_client.accept_invite", side_effect=_accept)


@pytest.fixture(scope="function")
def mock_add_user_to_service(notify_admin, mocker, service_one, api_user_active):
    def _add_user(service_id, user_id, permissions, folder_permissions):
        return

    return mocker.patch("app.user_api_client.add_user_to_service", side_effect=_add_user)


@pytest.fixture(scope="function")
def mock_set_user_permissions(notify_admin, mocker):
    return mocker.patch("app.user_api_client.set_user_permissions", return_value=None)


@pytest.fixture(scope="function")
def mock_remove_user_from_service(notify_admin, mocker):
    return mocker.patch("app.service_api_client.remove_user_from_service", return_value=None)


@pytest.fixture(scope="function")
def mock_get_template_statistics(notify_admin, mocker, service_one, fake_uuid):
    template = template_json(
        service_id=service_one["id"],
        id_=fake_uuid,
        name="Test template",
        type_="sms",
        content="Something very interesting",
    )
    data = {
        "count": 1,
        "template_name": template["name"],
        "template_type": template["template_type"],
        "template_id": template["id"],
        "is_precompiled_letter": False,
        "status": "delivered",
    }

    def _get_stats(service_id, limit_days=None):
        return [data]

    return mocker.patch("app.template_statistics_client.get_template_statistics_for_service", side_effect=_get_stats)


@pytest.fixture(scope="function")
def mock_get_monthly_template_usage(notify_admin, mocker, service_one, fake_uuid):
    def _stats(service_id, year):
        return [
            {"template_id": fake_uuid, "month": 4, "year": year, "count": 2, "name": "My first template", "type": "sms"}
        ]

    return mocker.patch("app.template_statistics_client.get_monthly_template_usage_for_service", side_effect=_stats)


@pytest.fixture(scope="function")
def mock_get_monthly_notification_stats(notify_admin, mocker, service_one, fake_uuid):
    def _stats(service_id, year):
        return {
            "data": {
                datetime.utcnow().strftime("%Y-%m"): {
                    "email": {
                        "sending": 1,
                        "delivered": 1,
                    },
                    "sms": {
                        "sending": 1,
                        "delivered": 1,
                    },
                    "letter": {
                        "sending": 1,
                        "delivered": 1,
                    },
                }
            }
        }

    return mocker.patch("app.service_api_client.get_monthly_notification_stats", side_effect=_stats)


@pytest.fixture(scope="function")
def mock_get_annual_usage_for_service(notify_admin, mocker, service_one, fake_uuid):
    def _get_usage(service_id, year=None):
        return [
            {
                "notification_type": "email",
                "chargeable_units": 1000,
                "notifications_sent": 1000,
                "charged_units": 1000,
                "rate": 0.00,
                "cost": 0,
            },
            {
                "notification_type": "sms",
                "chargeable_units": 251500,
                "notifications_sent": 105000,
                "charged_units": 1500,
                "rate": 0.0165,
                "cost": 24.75,  # 250K free allowance
            },
            {
                "notification_type": "sms",
                "chargeable_units": 300,
                "notifications_sent": 300,
                "charged_units": 300,
                "rate": 0.017,
                "cost": 5.1,
            },
            {
                "notification_type": "letter",
                "chargeable_units": 300,
                "notifications_sent": 100,
                "charged_units": 300,
                "rate": 0.1,
                "cost": 30,
            },
        ]

    return mocker.patch("app.billing_api_client.get_annual_usage_for_service", side_effect=_get_usage)


@pytest.fixture(scope="function")
def mock_get_monthly_usage_for_service(notify_admin, mocker):
    def _get_usage(service_id, year):
        return [
            {
                "month": "March",
                "notification_type": "sms",
                "rate": 0.017,
                "chargeable_units": 1230,
                "notifications_sent": 1234,
                "postage": "none",
                "charged_units": 1230,
                "free_allowance_used": 0,
                "cost": 20.91,
            },
            {
                "month": "February",
                "notification_type": "sms",
                "rate": 0.017,
                "chargeable_units": 33,
                "notifications_sent": 1234,
                "postage": "none",
                "charged_units": 33,
                "free_allowance_used": 0,
                "cost": 0.561,
            },
            {
                "month": "February",
                "notification_type": "sms",
                "rate": 0.0165,
                "chargeable_units": 1100,
                "notifications_sent": 1234,
                "postage": "none",
                "charged_units": 960,
                "free_allowance_used": 140,
                "cost": 15.84,
            },
            {
                "month": "February",
                "notification_type": "letter",
                "rate": 0.18,
                "chargeable_units": 6,
                "notifications_sent": 6,
                "postage": "economy",
                "charged_units": 6,
                "free_allowance_used": 0,
                "cost": 1.08,
            },
            {
                "month": "February",
                "notification_type": "letter",
                "rate": 0.31,
                "chargeable_units": 10,
                "notifications_sent": 10,
                "postage": "second",
                "charged_units": 10,
                "free_allowance_used": 0,
                "cost": 3.1,
            },
            {
                "month": "February",
                "notification_type": "letter",
                "rate": 0.33,
                "chargeable_units": 5,
                "notifications_sent": 5,
                "postage": "first",
                "charged_units": 5,
                "free_allowance_used": 0,
                "cost": 1.65,
            },
            {
                "month": "February",
                "notification_type": "letter",
                "rate": 0.55,
                "chargeable_units": 3,
                "notifications_sent": 3,
                "postage": "europe",
                "charged_units": 3,
                "free_allowance_used": 0,
                "cost": 2.52,
            },
            {
                "month": "February",
                "notification_type": "letter",
                "rate": 0.84,
                "chargeable_units": 7,
                "notifications_sent": 7,
                "postage": "rest-of-world",
                "charged_units": 7,
                "free_allowance_used": 0,
                "cost": 5.88,
            },
            {
                "month": "April",
                "notification_type": "sms",
                "rate": 0.017,
                "chargeable_units": 249860,
                "notifications_sent": 1234,
                "postage": "none",
                "charged_units": 0,
                "free_allowance_used": 249860,
                "cost": 0,
            },
        ]

    return mocker.patch("app.billing_api_client.get_monthly_usage_for_service", side_effect=_get_usage)


@pytest.fixture(scope="function")
def mock_get_annual_usage_for_service_in_future(notify_admin, mocker, service_one, fake_uuid):
    def _get_usage(service_id, year=None):
        return [
            {
                "notification_type": "sms",
                "chargeable_units": 0,
                "notifications_sent": 0,
                "charged_units": 0,
                "rate": 0.0158,
                "cost": 0,
            },
            {
                "notification_type": "email",
                "chargeable_units": 0,
                "notifications_sent": 0,
                "charged_units": 0,
                "rate": 0.0,
                "cost": 0,
            },
        ]

    return mocker.patch("app.billing_api_client.get_annual_usage_for_service", side_effect=_get_usage)


@pytest.fixture(scope="function")
def mock_get_monthly_usage_for_service_in_future(notify_admin, mocker):
    def _get_usage(service_id, year):
        return []

    return mocker.patch("app.billing_api_client.get_monthly_usage_for_service", side_effect=_get_usage)


@pytest.fixture(scope="function")
def mock_events(notify_admin, mocker):
    def _create_event(event_type, event_data):
        return {"some": "data"}

    return mocker.patch("app.events_api_client.create_event", side_effect=_create_event)


@pytest.fixture(scope="function")
def mock_send_already_registered_email(notify_admin, mocker):
    return mocker.patch("app.user_api_client.send_already_registered_email")


def create_email_brandings(number_of_brandings, non_standard_values=None, shuffle=False):
    brandings = [
        {
            "id": str(idx),
            "name": f"org {idx}",
            "text": f"org {idx}",
            "colour": None,
            "logo": f"logo{idx}.png",
            "brand_type": "org",
        }
        for idx in range(1, number_of_brandings + 1)
    ]

    for idx, row in enumerate(non_standard_values or {}):
        brandings[row["idx"]].update(non_standard_values[idx])
        brandings[row["idx"]].pop("idx")

    if shuffle:
        brandings.insert(3, brandings.pop(4))

    return brandings


@pytest.fixture(scope="function")
def mock_get_all_email_branding(mocker):
    def _get_all_email_branding(sort_key=None):
        non_standard_values = [
            {"idx": 1, "colour": "red"},
            {"idx": 2, "colour": "orange"},
            {"idx": 3, "text": None},
            {"idx": 4, "colour": "blue"},
        ]
        shuffle = sort_key is None
        return create_email_brandings(5, non_standard_values=non_standard_values, shuffle=shuffle)

    return mocker.patch(
        "app.models.branding.AllEmailBranding._get_items",
        side_effect=_get_all_email_branding,
    )


@pytest.fixture(scope="function")
def mock_get_all_letter_branding(mocker):
    def _get_letter_branding():
        return [
            {
                "id": str(UUID(int=0)),
                "name": "HM Government",
                "filename": "hm-government",
            },
            {
                "id": str(UUID(int=1)),
                "name": "Land Registry",
                "filename": "land-registry",
            },
            {
                "id": str(UUID(int=2)),
                "name": "Animal and Plant Health Agency",
                "filename": "animal",
            },
        ]

    return mocker.patch("app.models.branding.AllLetterBranding._get_items", side_effect=_get_letter_branding)


@pytest.fixture
def mock_get_letter_branding_by_id(notify_admin, mocker):
    def _get_branding_by_id(_id):
        return {
            "id": _id,
            "name": "HM Government",
            "filename": "hm-government",
        }

    return mocker.patch("app.letter_branding_client.get_letter_branding", side_effect=_get_branding_by_id)


@pytest.fixture(scope="function")
def mock_get_letter_branding_pool(mocker):
    def _get_branding_pool(org_id):
        return [
            {
                "id": "1234",
                "name": "Cabinet Office",
                "filename": "co",
            },
            {
                "id": "5678",
                "name": "Department for Education",
                "filename": "dfe",
            },
            {
                "id": "9abc",
                "name": "Government Digital Service",
                "filename": "gds",
            },
        ]

    return mocker.patch("app.models.branding.LetterBrandingPool._get_items", side_effect=_get_branding_pool)


@pytest.fixture(scope="function")
def mock_get_empty_letter_branding_pool(mocker):
    def _get_branding_pool(org_id):
        return []

    return mocker.patch("app.models.branding.LetterBrandingPool._get_items", side_effect=_get_branding_pool)


@pytest.fixture(scope="function")
def mock_no_email_branding(notify_admin, mocker):
    def _get_email_branding():
        return []

    return mocker.patch("app.email_branding_client.get_all_email_branding", side_effect=_get_email_branding)


def create_email_branding(id, non_standard_values=None):
    branding = {
        "logo": "example.png",
        "name": "Organisation name",
        "alt_text": "Alt text",
        "text": "Organisation text",
        "id": id,
        "colour": "#f00",
        "brand_type": "org",
    }

    if non_standard_values:
        branding.update(non_standard_values)

    return {"email_branding": branding}


def create_letter_branding(id, non_standard_values=None):
    branding = {"id": id, "filename": "example", "name": "Organisation name", "created_by_id": "abcd-1234"}

    if non_standard_values:
        branding.update(non_standard_values)

    return {"letter_branding": branding}


def create_email_branding_pool(additional_values=None):
    branding_pool = [
        {
            "logo": "example_1.png",
            "name": "Email branding name 1",
            "alt_text": "Alt text",
            "text": "Email branding text 1",
            "id": "email-branding-1-id",
            "colour": "#f00",
            "brand_type": "org",
        },
        {
            "logo": "example_2.png",
            "name": "Email branding name 2",
            "alt_text": "Alt text",
            "text": "Email branding text 2",
            "id": "email-branding-2-id",
            "colour": "#f00",
            "brand_type": "org",
        },
    ]

    if additional_values:
        branding_pool.append(additional_values)

    return branding_pool


@pytest.fixture(scope="function")
def mock_get_email_branding_pool(mocker):
    def _get_email_branding_pool(org_id):
        return create_email_branding_pool()

    return mocker.patch("app.models.branding.EmailBrandingPool._get_items", side_effect=_get_email_branding_pool)


@pytest.fixture(scope="function")
def mock_get_empty_email_branding_pool(mocker):
    def _get_email_branding_pool(org_id):
        return []

    return mocker.patch("app.models.branding.EmailBrandingPool._get_items", side_effect=_get_email_branding_pool)


@pytest.fixture(scope="function")
def mock_get_email_branding(notify_admin, mocker, fake_uuid):
    def _get_email_branding(id):
        return create_email_branding(id)

    return mocker.patch("app.models.branding.email_branding_client.get_email_branding", side_effect=_get_email_branding)


@pytest.fixture(scope="function")
def mock_get_email_branding_with_both_brand_type(notify_admin, mocker, fake_uuid):
    def _get_email_branding(id):
        return create_email_branding(fake_uuid, {"brand_type": "both"})

    return mocker.patch("app.email_branding_client.get_email_branding", side_effect=_get_email_branding)


@pytest.fixture(scope="function")
def mock_get_email_branding_with_org_banner_brand_type(notify_admin, mocker, fake_uuid):
    def _get_email_branding(id):
        return create_email_branding(fake_uuid, {"brand_type": "org_banner"})

    return mocker.patch("app.email_branding_client.get_email_branding", side_effect=_get_email_branding)


@pytest.fixture(scope="function")
def mock_get_email_branding_without_brand_text(notify_admin, mocker, fake_uuid):
    def _get_email_branding_without_brand_text(id):
        return create_email_branding(fake_uuid, {"text": "", "brand_type": "org_banner"})

    return mocker.patch(
        "app.email_branding_client.get_email_branding", side_effect=_get_email_branding_without_brand_text
    )


@pytest.fixture(scope="function")
def mock_create_email_branding(notify_admin, mocker, fake_uuid):
    def _create_email_branding(logo, name, alt_text, text, colour, brand_type, created_by_id):
        return create_email_branding(
            fake_uuid,
            {
                "name": name,
                "alt_text": alt_text,
                "text": text,
                "colour": colour,
                "brand_type": brand_type,
                "created_by_id": created_by_id,
            },
        )["email_branding"]

    return mocker.patch("app.email_branding_client.create_email_branding", side_effect=_create_email_branding)


@pytest.fixture(scope="function")
def mock_create_letter_branding(notify_admin, mocker, fake_uuid):
    def _create_letter_branding(filename, name, created_by_id):
        return create_letter_branding(
            fake_uuid,
            {
                "name": name,
                "filename": filename,
                "created_by_id": created_by_id,
            },
        )["letter_branding"]

    return mocker.patch("app.letter_branding_client.create_letter_branding", side_effect=_create_letter_branding)


@pytest.fixture(scope="function")
def mock_get_email_branding_name_for_alt_text(notify_admin, mocker):
    def _get_email_branding_name_for_alt_text(alt_text):
        return alt_text

    return mocker.patch(
        "app.email_branding_client.get_email_branding_name_for_alt_text",
        side_effect=_get_email_branding_name_for_alt_text,
    )


@pytest.fixture(scope="function")
def mock_update_email_branding(notify_admin, mocker):
    def _update_email_branding(branding_id, logo, name, alt_text, text, colour, brand_type, updated_by_id):
        return

    return mocker.patch("app.email_branding_client.update_email_branding", side_effect=_update_email_branding)


@pytest.fixture(scope="function")
def mock_get_guest_list(notify_admin, mocker):
    def _get_guest_list(service_id):
        return {"email_addresses": ["test@example.com"], "phone_numbers": ["07900900000"]}

    return mocker.patch("app.service_api_client.get_guest_list", side_effect=_get_guest_list)


@pytest.fixture(scope="function")
def mock_update_guest_list(notify_admin, mocker):
    return mocker.patch("app.service_api_client.update_guest_list")


@pytest.fixture(scope="function")
def mock_reset_failed_login_count(notify_admin, mocker):
    return mocker.patch("app.user_api_client.reset_failed_login_count")


@pytest.fixture
def mock_get_notification(notify_admin, mocker):
    def _get_notification(
        service_id,
        notification_id,
    ):
        noti = notification_json(service_id, rows=1, personalisation={"name": "Jo"})["notifications"][0]

        noti["id"] = notification_id
        noti["created_by"] = {"id": fake_uuid, "name": "Test User", "email_address": "test@user.gov.uk"}
        noti["template"] = template_json(
            service_id=service_id,
            id_="5407f4db-51c7-4150-8758-35412d42186a",
            content="hello ((name))",
            subject="blah",
            redact_personalisation=False,
            name="sample template",
        )
        return noti

    return mocker.patch("app.notification_api_client.get_notification", side_effect=_get_notification)


@pytest.fixture
def mock_send_notification(notify_admin, mocker, fake_uuid):
    def _send_notification(service_id, *, template_id, recipient, personalisation, sender_id):
        return {"id": fake_uuid}

    return mocker.patch("app.notification_api_client.send_notification", side_effect=_send_notification)


@pytest.fixture(scope="function")
def _client(notify_admin):
    """
    Do not use this fixture directly – use `client_request` instead
    """
    with notify_admin.test_request_context(), notify_admin.test_client() as client:
        yield client


@pytest.fixture(scope="function")
def _logged_in_client(_client, request, active_user_with_permissions, mocker, service_one, mock_login):
    """
    Do not use this fixture directly – use `client_request` instead
    """
    _client.login(active_user_with_permissions, mocker, service_one, request=request)
    yield _client


@pytest.fixture
def os_environ():
    """
    clear os.environ, and restore it after the test runs
    """
    # for use whenever you expect code to edit environment variables
    old_env = os.environ.copy()
    os.environ.clear()
    yield
    for k, v in old_env.items():
        os.environ[k] = v


@pytest.fixture
def client_request(request, _logged_in_client, mocker, service_one, fake_nonce):
    def block_method(object, method_name, preferred_method_name):
        def blocked_method(*args, **kwargs):
            raise AttributeError(
                f"Don’t use {object.__class__.__name__}.{method_name}"
                f" – try {object.__class__.__name__}.{preferred_method_name} instead"
            )

        setattr(object, method_name, blocked_method)

    class ClientRequest:
        @staticmethod
        @contextmanager
        def session_transaction():
            with _logged_in_client.session_transaction() as session:
                yield session

        @staticmethod
        def login(user, service=service_one):
            _logged_in_client.login(user, mocker, service, request)

        @staticmethod
        def logout():
            _logged_in_client.logout(None)

        @staticmethod
        def get(
            endpoint,
            _expected_status=200,
            _follow_redirects=False,
            _expected_redirect=None,
            _test_page_title=True,
            _test_for_elements_without_class=True,
            _test_forms_have_an_action_set=True,
            _test_for_non_smart_quotes=True,
            _test_for_script_csp_nonce=True,
            _optional_args="",
            **endpoint_kwargs,
        ):
            return ClientRequest.get_url(
                url_for(endpoint, **(endpoint_kwargs or {})) + _optional_args,
                _expected_status=_expected_status,
                _follow_redirects=_follow_redirects,
                _expected_redirect=_expected_redirect,
                _test_page_title=_test_page_title,
                _test_for_elements_without_class=_test_for_elements_without_class,
                _test_forms_have_an_action_set=_test_forms_have_an_action_set,
                _test_for_non_smart_quotes=_test_for_non_smart_quotes,
                _test_for_script_csp_nonce=_test_for_script_csp_nonce,
            )

        # ruff: noqa: C901
        @staticmethod
        def get_url(
            url,
            _expected_status=200,
            _follow_redirects=False,
            _expected_redirect=None,
            _test_page_title=True,
            _test_for_elements_without_class=True,
            _test_forms_have_an_action_set=True,
            _test_for_non_smart_quotes=True,
            _test_for_script_csp_nonce=True,
            **endpoint_kwargs,
        ):
            from flask.templating import _render

            mocker.patch("secrets.token_urlsafe", return_value=fake_nonce)

            with mock.patch("flask.templating._render", wraps=_render) as mock_render:
                resp = _logged_in_client.get(
                    url,
                    follow_redirects=_follow_redirects,
                )

                check_render_template_forms(mock_render.call_args_list)

            if _expected_redirect and _expected_status == 200:
                _expected_status = 302

            if 300 <= _expected_status <= 399:
                assert _expected_redirect, "You must specify a redirect URL, not just a status"

            assert resp.status_code == _expected_status, resp.location

            if _expected_redirect:
                assert resp.location == _expected_redirect

            html = resp.data.decode("utf-8")
            page = NotifyBeautifulSoup(html, "html.parser")

            if page.doctype == "html":
                html5parser.parse(html)

                if html5parser.errors:
                    location, error, _extra_info = html5parser.errors[-1]
                    line_number, character_number = location
                    line_with_context = "\n".join(html.splitlines()[line_number - 10 : line_number])
                    raise html5lib.html5parser.ParseError(
                        f"\n\n{line_with_context}\n{' ' * (character_number - 1)}^ {error}"
                    )

            if _test_page_title:
                ClientRequest.test_page_title(page, url)

            if _test_for_elements_without_class and _expected_status not in (301, 302):
                ClientRequest.test_for_elements_without_class(page)

            if _test_forms_have_an_action_set and _expected_status not in (301, 302):
                ClientRequest.test_forms_have_an_action_set(page)

            if _test_for_non_smart_quotes:
                ClientRequest.test_for_non_smart_quotes(page)

            if _test_for_script_csp_nonce:
                ClientRequest.test_for_script_csp_nonce(page)

            ClientRequest._test_for_duplicate_ids(page)

            return page

        @staticmethod
        def post(
            endpoint,
            _data=None,
            _expected_status=None,
            _follow_redirects=False,
            _expected_redirect=None,
            _content_type=None,
            **endpoint_kwargs,
        ):
            return ClientRequest.post_url(
                url_for(endpoint, **(endpoint_kwargs or {})),
                _data=_data,
                _expected_status=_expected_status,
                _follow_redirects=_follow_redirects,
                _expected_redirect=_expected_redirect,
                _content_type=_content_type,
            )

        @staticmethod
        def post_url(
            url,
            _data=None,
            _expected_status=None,
            _follow_redirects=False,
            _expected_redirect=None,
            _content_type=None,
        ):
            if _expected_status is None:
                _expected_status = 200 if _follow_redirects else 302
            post_kwargs = {}
            if _content_type:
                post_kwargs.update(content_type=_content_type)

            from flask.templating import _render

            with mock.patch("flask.templating._render", wraps=_render) as mock_render:
                resp = _logged_in_client.post(url, data=_data, follow_redirects=_follow_redirects, **post_kwargs)
                check_render_template_forms(mock_render.call_args_list)

            assert resp.status_code == _expected_status
            if _expected_redirect:
                assert_url_expected(resp.location, _expected_redirect)

            return NotifyBeautifulSoup(resp.data.decode("utf-8"), "html.parser")

        @staticmethod
        def get_response(endpoint, _expected_status=200, _optional_args="", **endpoint_kwargs):
            return ClientRequest.get_response_from_url(
                url_for(endpoint, **(endpoint_kwargs or {})) + _optional_args,
                _expected_status=_expected_status,
            )

        @staticmethod
        def get_response_from_url(
            url,
            _expected_status=200,
        ):
            resp = _logged_in_client.get(url)
            assert resp.status_code == _expected_status
            return resp

        @staticmethod
        def post_response(
            endpoint, _data=None, _expected_status=302, _optional_args="", _content_type=None, **endpoint_kwargs
        ):
            return ClientRequest.post_response_from_url(
                url_for(endpoint, **(endpoint_kwargs or {})) + _optional_args,
                _data=_data,
                _content_type=_content_type,
                _expected_status=_expected_status,
            )

        @staticmethod
        def post_response_from_url(
            url,
            _data=None,
            _expected_status=302,
            _content_type=None,
        ):
            post_kwargs = {}
            if _content_type:
                post_kwargs.update(content_type=_content_type)
            resp = _logged_in_client.post(url, data=_data, **post_kwargs)
            assert resp.status_code == _expected_status
            return resp

        @staticmethod
        def test_page_title(page, url):
            # Page should have one H1
            assert len(page.select("h1")) == 1
            page_title, h1 = (normalize_spaces(page.select_one(selector).text) for selector in ("title", "h1"))
            assert normalize_spaces(page_title).startswith(h1), (
                f"Page {url} title '{page_title}' does not start with H1 '{h1}'"
            )

        @staticmethod
        def test_for_elements_without_class(page):
            for tag, hint in (
                ("p", "govuk-body"),
                ("a", "govuk-link govuk-link--no-visited-state"),
            ):
                element = page.select_one(f"{tag}:not([class])")
                if (
                    element
                    and not element.has_attr("style")  # Elements with inline CSS are exempt
                    and element.text.strip()  # Empty elements are exempt
                    and "govuk-error-summary__body" not in element.parent["class"]
                ):
                    raise AssertionError(
                        f"Found a <{tag}> without a class attribute:\n"
                        f"    {element}\n"
                        f"\n"
                        f'(you probably want to add class="{hint}")'
                    )

            assert not page.select(r"main.govuk-\!-padding-top-0 h1.govuk-heading-l"), (
                "Use heading-large or set error_summary_enabled=True"
            )

            if page.select("h1.heading-large"):
                assert "govuk-!-padding-top-0" in page.select_one("main")["class"], (
                    "Use govuk-heading-l or set error_summary_enabled=False"
                )

        @staticmethod
        def test_forms_have_an_action_set(page):
            assert not len(
                page.select("form:not(.js-hidden form):not(form[hidden]):not(form[action])")
            ), (  # forms hidden when js is enabled, or by default are exempt
                "Forms that POST need an action set, even if posting to the same page"
            )

        @staticmethod
        def test_for_non_smart_quotes(page):
            for el in page.select("h1, h2, h3, h4, h5, h6, p, li, .banner-dangerous"):
                assert not ("'" in el.text or '"' in el.text), (
                    f"Non-smart quote or apostrophe found in <{el.name}>: {normalize_spaces(el.text)}"
                )

        @staticmethod
        def test_for_script_csp_nonce(page):
            for script_tag in page.select("script"):
                src = script_tag.get("src")
                nonce = script_tag.get("nonce")
                if src and current_app.config["ASSET_DOMAIN"] in src:
                    assert nonce is None
                else:
                    assert nonce == fake_nonce

        @staticmethod
        def _test_for_duplicate_ids(page):
            ids = [element["id"] for element in page.select("*[id]")]
            for id in ids:
                assert ids.count(id) == 1, f"Duplicate id `{id}` found on these elements:\n    " + ", ".join(
                    f"<{element.name}>" for element in page.select(f"*[id='{id}']")
                )

    return ClientRequest


def normalize_spaces(input):
    if input is None:
        return None
    if isinstance(input, str):
        return " ".join(input.split())
    return normalize_spaces(" ".join(item.text for item in input))


@pytest.fixture(scope="function")
def mock_get_service_data_retention(notify_admin, mocker):
    data = {
        "id": str(sample_uuid()),
        "service_id": str(sample_uuid()),
        "service_name": "service name",
        "notification_type": "email",
        "days_of_retention": 7,
        "created_at": datetime.now(),
        "updated_at": None,
    }
    return mocker.patch("app.service_api_client.get_service_data_retention", return_value=[data])


@pytest.fixture(scope="function")
def mock_create_service_data_retention(notify_admin, mocker):
    return mocker.patch("app.service_api_client.create_service_data_retention")


@pytest.fixture(scope="function")
def mock_update_service_data_retention(notify_admin, mocker):
    return mocker.patch("app.service_api_client.update_service_data_retention")


@pytest.fixture(scope="function")
def mock_get_free_sms_fragment_limit(notify_admin, mocker):
    sample_limit = 250000
    return mocker.patch("app.billing_api_client.get_free_sms_fragment_limit_for_year", return_value=sample_limit)


@pytest.fixture(scope="function")
def mock_create_or_update_free_sms_fragment_limit(notify_admin, mocker):
    sample_limit = {"free_sms_fragment_limit": 250000}
    return mocker.patch("app.billing_api_client.create_or_update_free_sms_fragment_limit", return_value=sample_limit)


@contextmanager
def set_config(app, name, value):
    old_val = app.config.get(name)
    app.config[name] = value
    yield
    app.config[name] = old_val


@contextmanager
def set_config_values(app, dict):
    old_values = {}

    for key in dict:
        old_values[key] = app.config.get(key)
        app.config[key] = dict[key]

    yield

    for key in dict:
        app.config[key] = old_values[key]


@pytest.fixture
def webauthn_dev_server(notify_admin, mocker):
    overrides = {
        "NOTIFY_ENVIRONMENT": "development",
        "ADMIN_BASE_URL": "https://webauthn.io",
    }

    with set_config_values(notify_admin, overrides):
        webauthn_server.init_app(notify_admin)
        yield

    webauthn_server.init_app(notify_admin)


@pytest.fixture(scope="function")
def valid_token(notify_admin, fake_uuid):
    return generate_token(
        json.dumps({"user_id": fake_uuid, "secret_code": "my secret"}),
        notify_admin.config["SECRET_KEY"],
        notify_admin.config["DANGEROUS_SALT"],
    )


@pytest.fixture(scope="function")
def mock_get_orgs_and_services_associated_with_branding_empty(notify_admin, mocker):
    def _get(email_branding_id):
        return {"data": {"services": [], "organisations": []}}

    return mocker.patch("app.email_branding_client.get_orgs_and_services_associated_with_branding", side_effect=_get)


@pytest.fixture(scope="function")
def mock_get_orgs_and_services_associated_with_branding_no_orgs(notify_admin, mocker):
    def _get(email_branding_id):
        return {
            "data": {
                "services": [{"name": "service 1", "id": "1234"}, {"name": "service 2", "id": "5678"}],
                "organisations": [],
            }
        }

    return mocker.patch("app.email_branding_client.get_orgs_and_services_associated_with_branding", side_effect=_get)


@pytest.fixture(scope="function")
def mock_get_orgs_and_services_associated_with_branding_no_services(notify_admin, mocker):
    def _get(email_branding_id):
        return {"data": {"services": [], "organisations": [{"name": "organisation 1", "id": "1234"}]}}

    return mocker.patch("app.email_branding_client.get_orgs_and_services_associated_with_branding", side_effect=_get)


@pytest.fixture(scope="function")
def mock_get_valid_service_inbound_api(notify_admin, mocker):
    def _get(service_id, callback_api_id):
        return {
            "created_at": "2017-12-04T10:52:55.289026Z",
            "updated_by_id": fake_uuid,
            "id": callback_api_id,
            "url": "https://hello3.gov.uk/inbound_sms",
            "service_id": service_id,
            "updated_at": "2017-12-04T11:28:42.575153Z",
        }

    return mocker.patch("app.service_api_client.get_service_inbound_api", side_effect=_get)


@pytest.fixture(scope="function")
def mock_get_valid_service_callback_api(notify_admin, mocker):
    def _get(service_id, callback_api_id, callback_type):
        return {
            "created_at": "2017-12-04T10:52:55.289026Z",
            "updated_by_id": fake_uuid,
            "id": callback_api_id,
            "url": f"https://hello2.gov.uk/{callback_type}",
            "service_id": service_id,
            "updated_at": "2017-12-04T11:28:42.575153Z",
        }

    return mocker.patch("app.service_api_client.get_service_callback_api", side_effect=_get)


@pytest.fixture(scope="function")
def mock_get_empty_service_inbound_api(notify_admin, mocker):
    return mocker.patch(
        "app.service_api_client.get_service_inbound_api",
        side_effect=lambda service_id, callback_api_id: None,
    )


@pytest.fixture(scope="function")
def mock_get_empty_service_callback_api(notify_admin, mocker):
    return mocker.patch(
        "app.service_api_client.get_service_callback_api",
        side_effect=lambda service_id, callback_api_id, callback_type: None,
    )


@pytest.fixture(scope="function")
def mock_create_service_inbound_api(notify_admin, mocker):
    def _create_service_inbound_api(service_id, url, bearer_token, user_id, callback_type):
        return

    return mocker.patch("app.service_api_client.create_service_inbound_api", side_effect=_create_service_inbound_api)


@pytest.fixture(scope="function")
def mock_update_service_inbound_api(notify_admin, mocker):
    def _update_service_inbound_api(service_id, url, bearer_token, user_id, callback_api_id, callback_type):
        return

    return mocker.patch("app.service_api_client.update_service_inbound_api", side_effect=_update_service_inbound_api)


@pytest.fixture(scope="function")
def mock_create_service_callback_api(notify_admin, mocker):
    def _create_service_callback_api(service_id, url, bearer_token, user_id, callback_type):
        return

    return mocker.patch("app.service_api_client.create_service_callback_api", side_effect=_create_service_callback_api)


@pytest.fixture(scope="function")
def mock_update_service_callback_api(notify_admin, mocker):
    def _update_service_callback_api(service_id, url, bearer_token, user_id, callback_api_id, callback_type):
        return

    return mocker.patch("app.service_api_client.update_service_callback_api", side_effect=_update_service_callback_api)


@pytest.fixture(scope="function")
def mock_create_returned_letters_callback_api(notify_admin, mocker):
    def _create_returned_letters_callback_api(service_id, url, bearer_token, user_id, callback_type):
        return

    return mocker.patch(
        "app.service_api_client.create_returned_letters_callback_api", side_effect=_create_returned_letters_callback_api
    )


@pytest.fixture(scope="function")
def mock_update_delivery_status_callback_api(notify_admin, mocker):
    def _update_delivery_status_callback_api(service_id, url, bearer_token, user_id, callback_api_id, callback_type):
        return

    return mocker.patch(
        "app.service_api_client.update_delivery_status_callback_api", side_effect=_update_delivery_status_callback_api
    )


@pytest.fixture(scope="function")
def mock_update_returned_letters_callback_api(notify_admin, mocker):
    def _update_returned_letters_callback_api(service_id, url, bearer_token, user_id, callback_api_id, callback_type):
        return

    return mocker.patch(
        "app.service_api_client.update_returned_letters_callback_api", side_effect=_update_returned_letters_callback_api
    )


@pytest.fixture(scope="function")
def organisation_one(api_user_active):
    return organisation_json(ORGANISATION_ID, "organisation one", [api_user_active["id"]])


@pytest.fixture(scope="function")
def mock_get_organisations(notify_admin, mocker):
    def _get_organisations():
        return [
            organisation_json("7aa5d4e9-4385-4488-a489-07812ba13383", "Org 1"),
            organisation_json("7aa5d4e9-4385-4488-a489-07812ba13384", "Org 2"),
            organisation_json("7aa5d4e9-4385-4488-a489-07812ba13385", "Org 3"),
        ]

    mocker.patch(
        "app.models.organisation.AllOrganisations._get_items",
        side_effect=_get_organisations,
    )

    return mocker.patch(
        "app.notify_client.organisations_api_client.organisations_client.get_organisations",
        side_effect=_get_organisations,
    )


@pytest.fixture(scope="function")
def mock_get_organisations_with_unusual_domains(notify_admin, mocker):
    def _get_organisations():
        return [
            organisation_json(
                "7aa5d4e9-4385-4488-a489-07812ba13383",
                "Org 1",
                domains=[
                    "ldquo.net",
                    "rdquo.net",
                    "lsquo.net",
                    "rsquo.net",
                ],
            ),
        ]

    return mocker.patch("app.organisations_client.get_organisations", side_effect=_get_organisations)


@pytest.fixture(scope="function")
def mock_get_organisation(notify_admin, mocker):
    def _get_organisation(org_id):
        return organisation_json(
            org_id,
            {
                "o1": "Org 1",
                "o2": "Org 2",
                "o3": "Org 3",
            }.get(org_id, "Test organisation"),
        )

    return mocker.patch("app.organisations_client.get_organisation", side_effect=_get_organisation)


@pytest.fixture(scope="function")
def mock_get_organisation_by_domain(notify_admin, mocker):
    def _get_organisation_by_domain(domain):
        return organisation_json(ORGANISATION_ID)

    return mocker.patch(
        "app.organisations_client.get_organisation_by_domain",
        side_effect=_get_organisation_by_domain,
    )


@pytest.fixture(scope="function")
def mock_get_organisation_nhs_gp(notify_admin, mocker):
    def _get_organisation(domain):
        return organisation_json(ORGANISATION_ID, organisation_type="nhs_gp")

    return mocker.patch("app.organisations_client.get_organisation", side_effect=_get_organisation)


@pytest.fixture(scope="function")
def mock_get_no_organisation_by_domain(notify_admin, mocker):
    return mocker.patch(
        "app.organisations_client.get_organisation_by_domain",
        return_value=None,
    )


@pytest.fixture(scope="function")
def mock_get_service_organisation(
    mock_get_organisation,
    mocker,
):
    return mocker.patch(
        "app.models.service.Service.organisation_id",
        new_callable=PropertyMock,
        return_value=ORGANISATION_ID,
    )


@pytest.fixture(scope="function")
def mock_update_service_organisation(notify_admin, mocker):
    def _update_service_organisation(service_id, org_id):
        return

    return mocker.patch(
        "app.organisations_client.update_service_organisation", side_effect=_update_service_organisation
    )


def _get_organisation_services(organisation_id):
    if organisation_id == "o1":
        return [
            service_json("12345", "service one", restricted=False),
            service_json("67890", "service two"),
            service_json("abcde", "service three"),
        ]
    if organisation_id == "o2":
        return [
            service_json("12345", "service one (org 2)", restricted=False),
            service_json("67890", "service two (org 2)", restricted=False),
            service_json("abcde", "service three"),
        ]
    return [
        service_json("12345", "service one"),
        service_json("67890", "service two"),
        service_json(SERVICE_ONE_ID, "service one", [sample_uuid()]),
    ]


@pytest.fixture(scope="function")
def mock_get_organisation_services(notify_admin, mocker, api_user_active):
    return mocker.patch("app.organisations_client.get_organisation_services", side_effect=_get_organisation_services)


@pytest.fixture(scope="function")
def mock_notify_users_of_request_to_go_live_for_service(notify_admin, mocker, api_user_active):
    def _notify_users_of_request_to_go_live_for_service(service_id):
        return

    return mocker.patch(
        "app.organisations_client.notify_users_of_request_to_go_live_for_service",
        side_effect=_notify_users_of_request_to_go_live_for_service,
    )


@pytest.fixture(scope="function")
def mock_get_users_for_organisation(mocker):
    def _get_users_for_organisation(org_id):
        return [
            user_json(id_="1234", name="Test User 1"),
            user_json(id_="5678", name="Test User 2", email_address="testt@gov.uk"),
        ]

    return mocker.patch("app.models.user.OrganisationUsers._get_items", side_effect=_get_users_for_organisation)


@pytest.fixture(scope="function")
def mock_get_invited_users_for_organisation(mocker, sample_org_invite):
    def _get_invited_invited_users_for_organisation(org_id):
        return [sample_org_invite]

    return mocker.patch(
        "app.models.user.OrganisationInvitedUsers._get_items",
        side_effect=_get_invited_invited_users_for_organisation,
    )


@pytest.fixture(scope="function")
def sample_org_invite(mocker, organisation_one):
    id_ = str(UUID(bytes=b"sample_org_invit", version=4))
    invited_by = organisation_one["users"][0]
    email_address = "invited_user@test.gov.uk"
    organisation = organisation_one["id"]
    created_at = str(datetime.utcnow())
    status = "pending"
    permissions = ["can_make_services_live"]

    return org_invite_json(
        id_=id_,
        invited_by=invited_by,
        org_id=organisation,
        email_address=email_address,
        created_at=created_at,
        status=status,
        permissions=permissions,
    )


@pytest.fixture(scope="function")
def mock_get_invites_for_organisation(mocker, sample_org_invite):
    def _get_org_invites(org_id):
        data = []
        for i in range(5):
            invite = copy.copy(sample_org_invite)
            invite["email_address"] = f"user_{i}@testnotify.gov.uk"
            data.append(invite)
        return data

    return mocker.patch("app.models.user.OrganisationInvitedUsers._get_items", side_effect=_get_org_invites)


@pytest.fixture(scope="function")
def mock_check_org_invite_token(notify_admin, mocker, sample_org_invite):
    def _check_org_token(token):
        return sample_org_invite

    return mocker.patch("app.org_invite_api_client.check_token", side_effect=_check_org_token)


@pytest.fixture(scope="function")
def mock_check_org_cancelled_invite_token(notify_admin, mocker, sample_org_invite):
    def _check_org_token(token):
        sample_org_invite["status"] = "cancelled"
        return sample_org_invite

    return mocker.patch("app.org_invite_api_client.check_token", side_effect=_check_org_token)


@pytest.fixture(scope="function")
def mock_check_org_accepted_invite_token(notify_admin, mocker, sample_org_invite):
    sample_org_invite["status"] = "accepted"

    def _check_org_token(token):
        return sample_org_invite

    return mocker.patch("app.org_invite_api_client.check_token", return_value=sample_org_invite)


@pytest.fixture(scope="function")
def mock_accept_org_invite(notify_admin, mocker, sample_org_invite):
    def _accept(organisation_id, invite_id):
        return sample_org_invite

    return mocker.patch("app.org_invite_api_client.accept_invite", side_effect=_accept)


@pytest.fixture(scope="function")
def mock_add_user_to_organisation(notify_admin, mocker, organisation_one, api_user_active):
    def _add_user(organisation_id, user_id, permissions):
        return api_user_active

    return mocker.patch("app.user_api_client.add_user_to_organisation", side_effect=_add_user)


@pytest.fixture(scope="function")
def mock_update_organisation(notify_admin, mocker):
    def _update_org(org, **kwargs):
        return

    return mocker.patch("app.organisations_client.update_organisation", side_effect=_update_org)


@pytest.fixture
def mock_get_organisations_and_services_for_user(notify_admin, mocker, organisation_one, api_user_active):
    def _get_orgs_and_services(user_id):
        return {"organisations": [], "services": []}

    return mocker.patch(
        "app.user_api_client.get_organisations_and_services_for_user", side_effect=_get_orgs_and_services
    )


@pytest.fixture
def mock_get_non_empty_organisations_and_services_for_user(notify_admin, mocker, organisation_one, api_user_active):
    def _make_services(name, trial_mode=False):
        return [
            {
                "name": f"{name} {i}",
                "id": SERVICE_TWO_ID,
                "restricted": trial_mode,
                "organisation": None,
            }
            for i in range(1, 3)
        ]

    def _get_orgs_and_services(user_id):
        return {
            "organisations": [
                {
                    "name": "Org 1",
                    "id": "o1",
                    "count_of_live_services": 1,
                },
                {
                    "name": "Org 2",
                    "id": "o2",
                    "count_of_live_services": 2,
                },
                {
                    "name": "Org 3",
                    "id": "o3",
                    "count_of_live_services": 0,
                },
            ],
            "services": (
                _get_organisation_services("o1") + _get_organisation_services("o2") + _make_services("Service")
            ),
        }

    return mocker.patch(
        "app.user_api_client.get_organisations_and_services_for_user", side_effect=_get_orgs_and_services
    )


@pytest.fixture
def mock_get_just_services_for_user(notify_admin, mocker, organisation_one, api_user_active):
    def _make_services(name, trial_mode=False):
        return [
            {
                "name": f"{name} {i + 1}",
                "id": id,
                "restricted": trial_mode,
                "organisation": None,
            }
            for i, id in enumerate([SERVICE_TWO_ID, SERVICE_ONE_ID])
        ]

    def _get_orgs_and_services(user_id):
        return {
            "organisations": [],
            "services": _make_services("Service"),
        }

    return mocker.patch(
        "app.user_api_client.get_organisations_and_services_for_user", side_effect=_get_orgs_and_services
    )


@pytest.fixture
def mock_get_empty_organisations_and_one_service_for_user(notify_admin, mocker, organisation_one, api_user_active):
    def _get_orgs_and_services(user_id):
        return {
            "organisations": [],
            "services": [
                {
                    "name": "Only service",
                    "id": SERVICE_TWO_ID,
                    "restricted": True,
                }
            ],
        }

    return mocker.patch(
        "app.user_api_client.get_organisations_and_services_for_user", side_effect=_get_orgs_and_services
    )


@pytest.fixture
def mock_create_event(notify_admin, mocker):
    """
    This should be used whenever your code is calling `flask_login.login_user`
    """

    def _add_event(event_type, event_data):
        return

    return mocker.patch("app.events_api_client.create_event", side_effect=_add_event)


def url_for_endpoint_with_token(endpoint, token, next=None):
    token = token.replace("%2E", ".")
    return url_for(endpoint, token=token, next=next)


@pytest.fixture
def mock_get_template_folders(notify_admin, mocker):
    return mocker.patch("app.template_folder_api_client.get_template_folders", return_value=[])


@pytest.fixture
def mock_move_to_template_folder(notify_admin, mocker):
    return mocker.patch("app.template_folder_api_client.move_to_folder")


@pytest.fixture
def mock_create_template_folder(notify_admin, mocker):
    return mocker.patch("app.template_folder_api_client.create_template_folder", return_value=sample_uuid())


@pytest.fixture(scope="function")
def mock_get_service_and_organisation_counts(notify_admin, mocker):
    return mocker.patch(
        "app.status_api_client.get_count_of_live_services_and_organisations",
        return_value={
            "organisations": 111,
            "services": 9999,
        },
    )


@pytest.fixture(scope="function")
def mock_get_service_history(notify_admin, mocker):
    return mocker.patch(
        "app.service_api_client.get_service_history",
        return_value={
            "service_history": [
                {
                    "name": "Example service",
                    "created_at": "2010-10-10T01:01:01.000000Z",
                    "updated_at": None,
                    "created_by_id": uuid4(),
                },
                {
                    "name": "Non-chronological event",
                    "created_at": "2010-10-10T01:01:01.000000Z",
                    "updated_at": "2012-12-12T14:14:14.000000Z",
                    "created_by_id": sample_uuid(),
                },
                {
                    "name": "Before lunch",
                    "created_at": "2010-10-10T01:01:01.000000Z",
                    "updated_at": "2012-12-12T12:12:12.000000Z",
                    "created_by_id": sample_uuid(),
                },
                {
                    "name": "After lunch",
                    "created_at": "2010-10-10T01:01:01.000000Z",
                    "updated_at": "2012-12-12T13:13:13.000000Z",
                    "created_by_id": sample_uuid(),
                },
            ],
            "api_key_history": [
                {
                    "name": "Good key",
                    "updated_at": None,
                    "created_at": "2010-10-10T10:10:10.000000Z",
                    "created_by_id": sample_uuid(),
                },
                {
                    "name": "Bad key",
                    "updated_at": "2012-11-11T12:12:12.000000Z",
                    "created_at": "2011-11-11T11:11:11.000000Z",
                    "created_by_id": sample_uuid(),
                },
                {
                    "name": "Bad key",
                    "updated_at": None,
                    "created_at": "2011-11-11T11:11:11.000000Z",
                    "created_by_id": sample_uuid(),
                },
                {
                    "name": "Key event returned in non-chronological order",
                    "updated_at": None,
                    "created_at": "2010-10-10T09:09:09.000000Z",
                    "created_by_id": sample_uuid(),
                },
            ],
            "events": [],
        },
    )


@pytest.fixture(scope="function")
def mock_get_returned_letter_summary_with_no_returned_letters(notify_admin, mocker):
    return mocker.patch(
        "app.service_api_client.get_returned_letter_summary",
        return_value=[],
    )


def do_mock_get_page_counts_for_letter(mocker, count, welsh_page_count=0, attachment_page_count=0):
    return mocker.patch(
        "app.template_preview_client.get_page_counts_for_letter",
        return_value={
            "count": count,
            "welsh_page_count": welsh_page_count,
            "attachment_page_count": attachment_page_count,
        },
    )


@pytest.fixture(scope="function")
def mock_get_page_counts_for_letter(mocker, count=1, welsh_page_count=0, attachment_page_count=0):
    return do_mock_get_page_counts_for_letter(
        mocker=mocker, count=count, welsh_page_count=welsh_page_count, attachment_page_count=attachment_page_count
    )


@pytest.fixture
def mock_template_preview(mocker, mock_get_page_counts_for_letter):
    content = b"letter preview as png or pdf"
    status_code = 200
    headers = {}
    example_response = (content, status_code, headers)
    mocker.patch("app.template_preview_client.get_preview_for_templated_letter", return_value=example_response)

    mocker.patch("app.template_preview_client.get_png_for_valid_pdf_page", return_value=example_response)
    mocker.patch("app.template_preview_client.get_png_for_invalid_pdf_page", return_value=example_response)


@pytest.fixture(scope="function")
def mock_get_returned_letter_statistics_with_no_returned_letters(notify_admin, mocker):
    return mocker.patch(
        "app.service_api_client.get_returned_letter_statistics",
        return_value={
            "returned_letter_count": 0,
            "most_recent_report": None,
        },
    )


def create_api_user_active(with_unique_id=False):
    return create_user(
        id=str(uuid4()) if with_unique_id else sample_uuid(),
    )


def create_active_user_empty_permissions(with_unique_id=False):
    return create_service_one_user(
        id=str(uuid4()) if with_unique_id else sample_uuid(),
        name="Test User With Empty Permissions",
    )


def create_active_user_with_permissions(with_unique_id=False):
    return create_service_one_admin(
        id=str(uuid4()) if with_unique_id else sample_uuid(),
    )


def create_active_user_view_permissions(with_unique_id=False):
    return create_service_one_user(
        id=str(uuid4()) if with_unique_id else sample_uuid(),
        name="Test User With Permissions",
        permissions={SERVICE_ONE_ID: ["view_activity"]},
    )


def create_active_caseworking_user(with_unique_id=False):
    return create_user(
        id=str(uuid4()) if with_unique_id else sample_uuid(),
        email_address="caseworker@example.gov.uk",
        permissions={
            SERVICE_ONE_ID: [
                "send_texts",
                "send_emails",
                "send_letters",
            ]
        },
        services=[SERVICE_ONE_ID],
    )


def create_active_user_no_settings_permission(with_unique_id=False):
    return create_service_one_user(
        id=str(uuid4()) if with_unique_id else sample_uuid(),
        name="Test User With Permissions",
        permissions={
            SERVICE_ONE_ID: [
                "manage_templates",
                "manage_api_keys",
                "view_activity",
            ]
        },
    )


def create_active_user_manage_template_permissions(with_unique_id=False):
    return create_service_one_user(
        id=str(uuid4()) if with_unique_id else sample_uuid(),
        name="Test User With Permissions",
        permissions={
            SERVICE_ONE_ID: [
                "manage_templates",
                "view_activity",
            ]
        },
    )


def create_platform_admin_user(with_unique_id=False, auth_type="webauthn_auth", permissions=None):
    return create_user(
        id=str(uuid4()) if with_unique_id else sample_uuid(),
        name="Platform admin user",
        email_address="platform@admin.gov.uk",
        permissions=permissions or {},
        platform_admin=True,
        auth_type=auth_type,
        can_use_webauthn=True,
    )


def create_service_one_admin(**overrides):
    user_data = {
        "permissions": {
            SERVICE_ONE_ID: [
                "send_texts",
                "send_emails",
                "send_letters",
                "manage_users",
                "manage_templates",
                "manage_settings",
                "manage_api_keys",
                "view_activity",
            ]
        },
    }
    user_data.update(overrides)
    return create_service_one_user(**user_data)


def create_service_one_user(**overrides):
    user_data = {
        "organisations": [ORGANISATION_ID],
        "services": [SERVICE_ONE_ID],
    }
    user_data.update(overrides)
    return create_user(**user_data)


def create_service_two_user_with_permissions(with_unique_id=False):
    user_data = {
        "id": str(sample_uuid()) if with_unique_id else sample_uuid(),
        "organisations": [ORGANISATION_ID],
        "services": [SERVICE_TWO_ID],
        "permissions": {
            SERVICE_TWO_ID: [
                "send_texts",
                "send_emails",
                "send_letters",
                "manage_users",
                "manage_templates",
                "manage_settings",
                "manage_api_keys",
                "view_activity",
            ]
        },
    }
    return create_user(**user_data)


def create_user(**overrides):
    user_data = {
        "name": "Test User",
        "password": "somepassword",
        "email_address": "test@user.gov.uk",
        "created_at": "2018-11-07T08:34:54.857402Z",
        "mobile_number": "07700 900762",
        "state": "active",
        "failed_login_count": 0,
        "permissions": {},
        "organisation_permissions": {},
        "platform_admin": False,
        "auth_type": "sms_auth",
        "password_changed_at": str(datetime.utcnow()),
        "services": [],
        "organisations": [],
        "current_session_id": None,
        "logged_in_at": None,
        "email_access_validated_at": None,
        "can_use_webauthn": False,
    }
    user_data.update(overrides)
    return user_data


def create_reply_to_email_address(
    id_="1234", service_id="abcd", email_address="test@example.com", is_default=True, created_at=None, updated_at=None
):
    return {
        "id": id_,
        "service_id": service_id,
        "email_address": email_address,
        "is_default": is_default,
        "created_at": created_at,
        "updated_at": updated_at,
    }


def create_multiple_email_reply_to_addresses(service_id="abcd"):
    return [
        {
            "id": "1234",
            "service_id": service_id,
            "email_address": "test@example.com",
            "is_default": True,
            "created_at": datetime.utcnow(),
            "updated_at": None,
        },
        {
            "id": "5678",
            "service_id": service_id,
            "email_address": "test2@example.com",
            "is_default": False,
            "created_at": datetime.utcnow(),
            "updated_at": None,
        },
        {
            "id": "9457",
            "service_id": service_id,
            "email_address": "test3@example.com",
            "is_default": False,
            "created_at": datetime.utcnow(),
            "updated_at": None,
        },
    ]


def create_sms_sender(
    id_="1234",
    service_id="abcd",
    sms_sender="GOVUK",
    is_default=True,
    created_at=None,
    inbound_number_id=None,
    updated_at=None,
):
    return {
        "id": id_,
        "service_id": service_id,
        "sms_sender": sms_sender,
        "is_default": is_default,
        "created_at": created_at,
        "inbound_number_id": inbound_number_id,
        "updated_at": updated_at,
    }


def create_multiple_sms_senders(service_id="abcd"):
    return [
        {
            "id": "1234",
            "service_id": service_id,
            "sms_sender": "Example",
            "is_default": True,
            "created_at": datetime.utcnow(),
            "inbound_number_id": "1234",
            "updated_at": None,
        },
        {
            "id": "5678",
            "service_id": service_id,
            "sms_sender": "Example 2",
            "is_default": False,
            "created_at": datetime.utcnow(),
            "inbound_number_id": None,
            "updated_at": None,
        },
        {
            "id": "9457",
            "service_id": service_id,
            "sms_sender": "Example 3",
            "is_default": False,
            "created_at": datetime.utcnow(),
            "inbound_number_id": None,
            "updated_at": None,
        },
    ]


def create_letter_contact_block(
    id_="1234",
    service_id="abcd",
    contact_block="1 Example Street",
    is_default=True,
    created_at=None,
    updated_at=None,
):
    return {
        "id": id_,
        "service_id": service_id,
        "contact_block": contact_block,
        "is_default": is_default,
        "created_at": created_at,
        "updated_at": updated_at,
    }


def create_multiple_letter_contact_blocks(service_id="abcd"):
    return [
        {
            "id": "1234",
            "service_id": service_id,
            "contact_block": "1 Example Street",
            "is_default": True,
            "created_at": datetime.utcnow(),
            "updated_at": None,
        },
        {
            "id": "5678",
            "service_id": service_id,
            "contact_block": "2 Example Street",
            "is_default": False,
            "created_at": datetime.utcnow(),
            "updated_at": None,
        },
        {
            "id": "9457",
            "service_id": service_id,
            "contact_block": "foo\n\n<bar>\n\nbaz",
            "is_default": False,
            "created_at": datetime.utcnow(),
            "updated_at": None,
        },
    ]


def create_notification(
    notification_id=None,
    service_id="abcd",
    notification_status="delivered",
    redact_personalisation=False,
    template_type=None,
    template_name="sample template",
    is_precompiled_letter=False,
    key_type=None,
    postage=None,
    sent_one_off=True,
    reply_to_text=None,
):
    noti = notification_json(
        service_id,
        rows=1,
        status=notification_status,
        template_type=template_type,
        postage=postage,
        reply_to_text=reply_to_text,
    )["notifications"][0]

    noti["id"] = notification_id or sample_uuid()
    if sent_one_off:
        noti["created_by"] = {"id": sample_uuid(), "name": "Test User", "email_address": "test@user.gov.uk"}
    noti["personalisation"] = {"name": "Jo"}
    noti["template"] = template_json(
        service_id=service_id,
        id_="5407f4db-51c7-4150-8758-35412d42186a",
        content="hello ((name))",
        subject="blah",
        redact_personalisation=redact_personalisation,
        type_=template_type,
        is_precompiled_letter=is_precompiled_letter,
        name=template_name,
    )
    if key_type:
        noti["key_type"] = key_type
    return noti


def create_notifications(
    service_id=SERVICE_ONE_ID,
    template_type="sms",
    rows=5,
    status=None,
    subject="subject",
    content="content",
    client_reference=None,
    personalisation=None,
    redact_personalisation=False,
    is_precompiled_letter=False,
    postage=None,
    to=None,
):
    template = template_json(
        service_id=service_id,
        id_=str(generate_uuid()),
        type_=template_type,
        subject=subject,
        content=content,
        redact_personalisation=redact_personalisation,
        is_precompiled_letter=is_precompiled_letter,
    )

    return notification_json(
        service_id,
        template=template,
        rows=rows,
        personalisation=personalisation,
        template_type=template_type,
        client_reference=client_reference,
        status=status,
        created_by_name="Firstname Lastname",
        postage=postage,
        to=to,
    )


def create_folder(id):
    return {"id": id, "parent_id": None, "name": "My folder"}


def create_template(
    service_id=SERVICE_ONE_ID,
    template_id=None,
    template_type="sms",
    name="sample template",
    content="Template content",
    subject="Template subject",
    redact_personalisation=False,
    postage=None,
    folder=None,
):
    return template_json(
        service_id=service_id,
        id_=template_id or str(generate_uuid()),
        name=name,
        type_=template_type,
        content=content,
        subject=subject,
        redact_personalisation=redact_personalisation,
        postage=postage,
        folder=folder,
    )


def create_unsubscribe_request_report(
    *,
    service_id=SERVICE_ONE_ID,
    processed_by_service_at=None,
    batch_id=None,
    will_be_archived_at=None,
    count=1,
    earliest_timestamp,
    latest_timestamp,
):
    return {
        "service_id": service_id,
        "count": count,
        "earliest_timestamp": earliest_timestamp,
        "latest_timestamp": latest_timestamp,
        "processed_by_service_at": processed_by_service_at,
        "batch_id": batch_id,
        "is_a_batched_report": bool(batch_id),
        "will_be_archived_at": will_be_archived_at,
    }


def create_report_request(**overrides):
    report_request_data = {
        "id": "5bf2a1f9-0e6b-4d5e-b409-3509bf7a37b0",
        "user_id": "a4125154-9272-474e-8500-cfb23a58d7a6",
        "service_id": SERVICE_ONE_ID,
        "report_type": "notifications_status_csv",
        "status": REPORT_REQUEST_STORED,
        "parameter": {},
        "created_at": "2025-02-27T13:35:32.919548Z",
        "updated_at": "2025-02-27T13:35:32.919548Z",
    }
    report_request_data.update(overrides)
    return report_request_data


@pytest.fixture
def mock_get_invited_user_by_id(notify_admin, mocker, sample_invite):
    def _get(invited_user_id):
        return sample_invite

    return mocker.patch(
        "app.invite_api_client.get_invited_user",
        side_effect=_get,
    )


@pytest.fixture
def mock_get_invited_org_user_by_id(notify_admin, mocker, sample_org_invite):
    def _get(invited_org_user_id):
        return sample_org_invite

    return mocker.patch(
        "app.org_invite_api_client.get_invited_user",
        side_effect=_get,
    )


@pytest.fixture
def mock_antivirus_virus_free(notify_admin, mocker):
    yield mocker.patch("app.extensions.antivirus_client.scan", return_value=True)


@pytest.fixture
def mock_antivirus_virus_found(notify_admin, mocker):
    yield mocker.patch("app.extensions.antivirus_client.scan", return_value=False)


@pytest.fixture
def webauthn_credential():
    return {
        "id": str(uuid4()),
        "name": "Test credential",
        "credential_data": "WJ8AAAAAAAAAAAAAAAAAAAAAAECKU1ppjl9gmhHWyDkgHsUvZmhr6oF3/lD3llzLE2SaOSgOGIsIuAQqgp8JQSUu3r/oOaP8RS44dlQjrH+ALfYtpQECAyYgASFYIDGeoB8RJc5iMpRzZYAK5dndyHQkfFXRUWutPKPKMgdcIlggWfHwfzsvhsClHgz6E9xX58d6EQ55b4oLJ3Qf5YZjyzo=",  # noqa
        "registration_response": "anything",
        "created_at": "2017-10-18T16:57:14.154185Z",
        "logged_in_at": "2017-10-19T00:00:00.000000Z",
    }


@pytest.fixture
def webauthn_credential_2():
    return {
        "id": str(uuid4()),
        "name": "Another test credential",
        "credential_data": "WJ0AAAAAAAAAAAAAAAAAAAAAAECKU1jppl9mhgHWyDkgHsUvZmhr6oF3/lD3llzLE2SaOSgOGIsIuAQqgp8JQSUu3r/oOaP8RS44dlQjrH+ALfYtpAECAyYhWCAxnqAfESXOYjKUc2WACuXZ3ch0JHxV0VFrrTyjyjIHXCJYIFnx8L4H87bApR4M+hPcV+fHehEOeW+KCyd0H+WGY8s6",  # noqa
        "registration_response": "stuff",
        "created_at": "2021-05-14T16:57:14.154185Z",
        "logged_in_at": None,
    }


@pytest.fixture
def logo_client(notify_admin):
    from app import logo_client

    yield logo_client


@pytest.fixture(scope="function")
def mock_create_service_join_request(notify_admin, mocker):
    def _create_service_join_request(user_to_invite_id, *, service_id, service_managers_ids, reason):
        return

    return mocker.patch("app.service_api_client.create_service_join_request", side_effect=_create_service_join_request)


@pytest.fixture(scope="function")
def mock_get_letter_rates(mocker):
    def _get_letter_rates():
        return [
            {"post_class": "economy", "rate": "0.59", "sheet_count": 1, "start_date": "2024-06-30T23:00:00"},
            {"post_class": "second", "rate": "0.68", "sheet_count": 1, "start_date": "2024-06-30T23:00:00"},
            {"post_class": "first", "rate": "1.49", "sheet_count": 1, "start_date": "2024-06-30T23:00:00"},
            {"post_class": "europe", "rate": "1.56", "sheet_count": 1, "start_date": "2024-01-02T00:00:00"},
            {"post_class": "rest-of-world", "rate": "1.56", "sheet_count": 1, "start_date": "2024-01-02T00:00:00"},
            {"post_class": "economy", "rate": "0.64", "sheet_count": 2, "start_date": "2024-06-30T23:00:00"},
            {"post_class": "second", "rate": "0.72", "sheet_count": 2, "start_date": "2024-06-30T23:00:00"},
            {"post_class": "first", "rate": "1.53", "sheet_count": 2, "start_date": "2024-06-30T23:00:00"},
            {"post_class": "europe", "rate": "1.61", "sheet_count": 2, "start_date": "2024-01-02T00:00:00"},
            {"post_class": "rest-of-world", "rate": "1.61", "sheet_count": 2, "start_date": "2024-01-02T00:00:00"},
            {"post_class": "economy", "rate": "0.68", "sheet_count": 3, "start_date": "2024-06-30T23:00:00"},
            {"post_class": "second", "rate": "0.77", "sheet_count": 3, "start_date": "2024-06-30T23:00:00"},
            {"post_class": "first", "rate": "1.57", "sheet_count": 3, "start_date": "2024-06-30T23:00:00"},
            {"post_class": "europe", "rate": "1.66", "sheet_count": 3, "start_date": "2024-01-02T00:00:00"},
            {"post_class": "rest-of-world", "rate": "1.66", "sheet_count": 3, "start_date": "2024-01-02T00:00:00"},
            {"post_class": "economy", "rate": "0.77", "sheet_count": 4, "start_date": "2024-06-30T23:00:00"},
            {"post_class": "second", "rate": "0.82", "sheet_count": 4, "start_date": "2024-06-30T23:00:00"},
            {"post_class": "first", "rate": "1.63", "sheet_count": 4, "start_date": "2024-06-30T23:00:00"},
            {"post_class": "europe", "rate": "1.71", "sheet_count": 4, "start_date": "2024-01-02T00:00:00"},
            {"post_class": "rest-of-world", "rate": "1.71", "sheet_count": 4, "start_date": "2024-01-02T00:00:00"},
            {"post_class": "economy", "rate": "0.78", "sheet_count": 5, "start_date": "2024-06-30T23:00:00"},
            {"post_class": "second", "rate": "0.86", "sheet_count": 5, "start_date": "2024-06-30T23:00:00"},
            {"post_class": "first", "rate": "1.67", "sheet_count": 5, "start_date": "2024-06-30T23:00:00"},
            {"post_class": "europe", "rate": "1.76", "sheet_count": 5, "start_date": "2024-01-02T00:00:00"},
            {"post_class": "rest-of-world", "rate": "1.76", "sheet_count": 5, "start_date": "2024-01-02T00:00:00"},
        ]

    return mocker.patch("app.models.letter_rates.LetterRates._get_items", side_effect=_get_letter_rates)


@pytest.fixture(scope="function")
def mock_get_sms_rate(notify_admin, mocker):
    def _get_sms_rate():
        return {
            "rate": 0.0197,
            "valid_from": "2024-01-02T12:00:00",
        }

    return mocker.patch("app.models.sms_rate.sms_rate_api_client.get_sms_rate", side_effect=_get_sms_rate)


@pytest.fixture(scope="function")
def mock_onwards_request_headers(mocker):
    mock_gorh = mocker.patch("notifications_utils.request_helper.NotifyRequest.get_onwards_request_headers")
    mock_gorh.return_value = {"some-onwards": "request-headers"}
    return mock_gorh


@pytest.fixture(scope="function")
def mock_get_notifications_count_for_service(mocker):
    return mocker.patch(
        "app.notification_api_client.get_notifications_count_for_service",
        return_value=100,
    )


@pytest.fixture(scope="function")
def fake_nonce():
    return "TESTs5Vr8v3jgRYLoQuVwA"


@pytest.fixture
def mock_get_service_settings_page_common(
    mock_get_all_letter_branding,
    mock_get_inbound_number_for_service,
    mock_get_free_sms_fragment_limit,
    mock_get_service_data_retention,
    mock_get_organisation,
):
    return
