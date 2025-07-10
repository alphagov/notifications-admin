import uuid
from datetime import UTC, datetime, timedelta
from itertools import repeat
from unittest.mock import patch
from urllib.parse import parse_qs, urlparse

import pytest
from bs4 import BeautifulSoup, Doctype
from flask import session as flask_session
from flask import url_for
from flask.testing import FlaskClient
from flask_login import login_user

from app.models.user import User


class TestClient(FlaskClient):
    def login(self, user, mocker=None, service=None, request=None):
        # Skipping authentication here and just log them in
        model_user = User(user)
        with self.session_transaction() as session:
            session["current_session_id"] = model_user.current_session_id
            session["user_id"] = model_user.id
        if mocker:
            mocker.patch("app.user_api_client.get_user", return_value=user)
        if mocker and service:
            with self.session_transaction() as session:
                session["service_id"] = service["id"]

        # Add the service to the services available via the mock on `service_api_client.get_service` so that requests
        # for it will return the correct JSON.
        if request and service:
            request.getfixturevalue("mock_get_service")  # make sure fixture is loaded
            mocked_get_service_data = request.getfixturevalue("mocked_get_service_data")
            mocked_get_service_data[service["id"]] = service

        with patch("app.events_api_client.create_event"):
            login_user(model_user)
        with self.session_transaction() as test_session:
            for key, value in flask_session.items():
                test_session[key] = value

    def logout(self, user):
        self.get(url_for("main.sign_out"))


class NotifyBeautifulSoup(BeautifulSoup):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.override_method("find", "select_one")
        self.override_method("find_all", "select")

    def override_method(self, method_name, preferred_method_name):
        def overridden_method(*args, **kwargs):
            raise AttributeError(
                f"Don’t use BeautifulSoup.{method_name} – try BeautifulSoup.{preferred_method_name} instead"
            )

        setattr(self, method_name, overridden_method)

    @property
    def doctype(self):
        return next(
            (item for item in self.contents if isinstance(item, Doctype)),
            "",
        )


def sample_uuid():
    return "6ce466d0-fd6a-11e5-82f5-e0accb9d11a6"


def generate_uuid():
    return uuid.uuid4()


def created_by_json(id_, name="", email_address=""):
    return {"id": id_, "name": name, "email_address": email_address}


def user_json(
    id_="1234",
    name="Test User",
    email_address="test@gov.uk",
    mobile_number="+447700900986",
    password_changed_at=None,
    permissions=None,
    auth_type="sms_auth",
    failed_login_count=0,
    logged_in_at=None,
    state="active",
    platform_admin=False,
    current_session_id="1234",
    organisations=None,
    services=None,
):
    if permissions is None:
        permissions = {
            str(generate_uuid()): [
                "view_activity",
                "send_texts",
                "send_emails",
                "send_letters",
                "manage_users",
                "manage_templates",
                "manage_settings",
                "manage_api_keys",
            ]
        }

    if services is None:
        services = [str(service_id) for service_id in permissions.keys()]

    return {
        "id": id_,
        "name": name,
        "email_address": email_address,
        "mobile_number": mobile_number,
        "password_changed_at": password_changed_at,
        "permissions": permissions,
        "auth_type": auth_type,
        "failed_login_count": failed_login_count,
        "logged_in_at": logged_in_at or datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S.%f"),
        "state": state,
        "platform_admin": platform_admin,
        "current_session_id": current_session_id,
        "organisations": organisations or [],
        "services": services,
    }


def invited_user(
    _id="1234",
    service=None,
    from_user="1234",
    email_address="testinviteduser@gov.uk",
    permissions=None,
    status="pending",
    created_at=None,
    auth_type="sms_auth",
    organisation=None,
):
    data = {
        "id": _id,
        "from_user": from_user,
        "email_address": email_address,
        "status": status,
        "created_at": created_at or datetime.utcnow(),
        "auth_type": auth_type,
    }
    if service:
        data["service"] = service
    if permissions:
        data["permissions"] = permissions
    if organisation:
        data["organisation"] = organisation

    return data


def service_json(
    id_="1234",
    name="Test Service",
    users=None,
    email_message_limit=1000,
    letter_message_limit=1000,
    international_sms_message_limit=500,
    sms_message_limit=1000,
    active=True,
    restricted=True,
    reply_to_email_address=None,
    custom_email_sender_name=None,
    email_sender_local_part="test.service",
    sms_sender="GOVUK",
    email_branding=None,
    branding="govuk",
    created_at=None,
    letter_contact_block=None,
    service_callback_api=None,
    permissions=None,
    organisation_type="central",
    prefix_sms=True,
    contact_link=None,
    organisation_id=None,
    rate_limit=3000,
    notes=None,
    billing_contact_email_addresses=None,
    billing_contact_names=None,
    billing_reference=None,
    purchase_order_number=None,
    has_active_go_live_request=False,
    go_live_user=None,
    confirmed_unique=False,
):
    if users is None:
        users = []
    if permissions is None:
        permissions = ["email", "sms"]
    if service_callback_api is None:
        service_callback_api = []
    return {
        "id": id_,
        "name": name,
        "users": users,
        "email_message_limit": email_message_limit,
        "international_sms_message_limit": international_sms_message_limit,
        "sms_message_limit": sms_message_limit,
        "letter_message_limit": letter_message_limit,
        "rate_limit": rate_limit,
        "active": active,
        "restricted": restricted,
        "reply_to_email_address": reply_to_email_address,
        "custom_email_sender_name": custom_email_sender_name,
        "email_sender_local_part": email_sender_local_part,
        "sms_sender": sms_sender,
        "organisation_type": organisation_type,
        "email_branding": email_branding,
        "branding": branding,
        "created_at": created_at or str(datetime.utcnow()),
        "letter_branding": None,
        "letter_contact_block": letter_contact_block,
        "permissions": permissions,
        "service_callback_api": service_callback_api,
        "prefix_sms": prefix_sms,
        "contact_link": contact_link,
        "volume_email": 111111,
        "volume_sms": 222222,
        "volume_letter": 333333,
        "consent_to_research": True,
        "count_as_live": True,
        "organisation": organisation_id,
        "notes": notes,
        "billing_contact_email_addresses": billing_contact_email_addresses,
        "billing_contact_names": billing_contact_names,
        "billing_reference": billing_reference,
        "purchase_order_number": purchase_order_number,
        "has_active_go_live_request": has_active_go_live_request,
        "go_live_user": go_live_user,
        "confirmed_unique": confirmed_unique,
    }


def organisation_json(
    id_="1234",
    name=False,
    users=None,
    active=True,
    created_at=None,
    services=None,
    letter_branding_id=None,
    email_branding_id=None,
    domains=None,
    crown=True,
    agreement_signed=False,
    agreement_signed_version=None,
    agreement_signed_by_id=None,
    agreement_signed_on_behalf_of_name=None,
    agreement_signed_on_behalf_of_email_address=None,
    organisation_type="central",
    request_to_go_live_notes=None,
    notes=None,
    billing_contact_email_addresses=None,
    billing_contact_names=None,
    billing_reference=None,
    purchase_order_number=None,
    can_approve_own_go_live_requests=False,
    can_ask_to_join_a_service=False,
    permissions=None,
):
    if users is None:
        users = []
    if services is None:
        services = []
    if permissions is None:
        permissions = []
    if can_ask_to_join_a_service:
        permissions.extend(["can_ask_to_join_a_service"])
    return {
        "id": id_,
        "name": "Test Organisation" if name is False else name,
        "active": active,
        "users": users,
        "created_at": created_at or str(datetime.utcnow()),
        "email_branding_id": email_branding_id,
        "letter_branding_id": letter_branding_id,
        "organisation_type": organisation_type,
        "crown": crown,
        "agreement_signed": agreement_signed,
        "agreement_signed_at": None,
        "agreement_signed_by_id": agreement_signed_by_id,
        "agreement_signed_version": agreement_signed_version,
        "agreement_signed_on_behalf_of_name": agreement_signed_on_behalf_of_name,
        "agreement_signed_on_behalf_of_email_address": agreement_signed_on_behalf_of_email_address,
        "domains": domains or [],
        "request_to_go_live_notes": request_to_go_live_notes,
        "count_of_live_services": len(services),
        "notes": notes,
        "billing_contact_email_addresses": billing_contact_email_addresses,
        "billing_contact_names": billing_contact_names,
        "billing_reference": billing_reference,
        "purchase_order_number": purchase_order_number,
        "can_approve_own_go_live_requests": can_approve_own_go_live_requests,
        "can_ask_to_join_a_service": can_ask_to_join_a_service,
        "permissions": permissions or [],
    }


def template_json(
    *,
    service_id,
    id_,
    name="sample template",
    type_=None,
    content=None,
    subject=None,
    version=1,
    archived=False,
    redact_personalisation=None,
    service_letter_contact=None,
    reply_to=None,
    reply_to_text=None,
    is_precompiled_letter=False,
    postage=None,
    folder=None,
    letter_attachment=None,
    letter_languages=None,
    letter_welsh_subject=None,
    letter_welsh_content=None,
    updated_at=None,
    has_unsubscribe_link=None,
):
    template = {
        "id": id_,
        "name": name,
        "template_type": type_ or "sms",
        "content": content,
        "service": service_id,
        "version": version,
        "updated_at": updated_at or datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S.%f"),
        "archived": archived,
        "service_letter_contact": service_letter_contact,
        "reply_to": reply_to,
        "reply_to_text": reply_to_text,
        "is_precompiled_letter": is_precompiled_letter,
        "folder": folder,
        "postage": postage,
        "letter_attachment": letter_attachment,
        "letter_languages": letter_languages or "english" if type_ == "letter" else None,
        "letter_welsh_subject": letter_welsh_subject,
        "letter_welsh_content": letter_welsh_content,
        "has_unsubscribe_link": has_unsubscribe_link,
    }
    if content is None:
        template["content"] = "template content"
    if subject is None and type_ != "sms":
        template["subject"] = "template subject"
    if subject is not None:
        template["subject"] = subject
    if redact_personalisation is not None:
        template["redact_personalisation"] = redact_personalisation
    return template


def template_version_json(service_id, id_, created_by, version=1, created_at=None, **kwargs):
    template = template_json(service_id=service_id, id_=id_, **kwargs)
    template["created_by"] = created_by_json(
        created_by["id"],
        created_by["name"],
        created_by["email_address"],
    )
    if created_at is None:
        created_at = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S.%f")
    template["created_at"] = created_at
    template["version"] = version
    return template


def api_key_json(id_, name, expiry_date=None, key_type="normal"):
    return {"id": id_, "name": name, "expiry_date": expiry_date, "key_type": key_type}


def invite_json(
    id_, from_user, service_id, email_address, permissions, created_at, status, auth_type, folder_permissions
):
    return {
        "id": id_,
        "from_user": from_user,
        "service": service_id,
        "email_address": email_address,
        "status": status,
        "permissions": permissions,
        "created_at": created_at,
        "auth_type": auth_type,
        "folder_permissions": folder_permissions,
    }


def org_invite_json(*, id_, invited_by, org_id, email_address, created_at, status, permissions):
    return {
        "id": id_,
        "invited_by": invited_by,
        "organisation": org_id,
        "email_address": email_address,
        "status": status,
        "created_at": created_at,
        "permissions": permissions,
    }


def inbound_sms_json():
    return {
        "has_next": True,
        "data": [
            {
                "user_number": phone_number,
                "notify_number": "07900000002",
                "content": f"message-{index + 1}",
                "created_at": (datetime.utcnow() - timedelta(minutes=60 * hours_ago, seconds=index)).isoformat(),
                "id": str(uuid.uuid4()),
            }
            for index, hours_ago, phone_number in (
                (0, 1, "447900900000"),
                (1, 1, "07900900000"),
                (2, 1, "07900900000"),
                (3, 3, "07900900002"),
                (4, 5, "33(0)1 12345678"),  # France
                (5, 7, "1-202-555-0104"),  # USA in one format
                (6, 9, "+12025550104"),  # USA in another format
                (7, 9, "+68223001"),  # Cook Islands
            )
        ],
    }


TEST_USER_EMAIL = "test@user.gov.uk"


def create_test_api_user(state, permissions=None):
    user_data = {
        "id": 1,
        "name": "Test User",
        "password": "somepassword",
        "email_address": TEST_USER_EMAIL,
        "mobile_number": "+441234123412",
        "state": state,
        "permissions": permissions or {},
    }
    return user_data


def job_json(
    service_id,
    created_by,
    job_id=None,
    template_id=None,
    template_version=1,
    template_type="sms",
    template_name="Example template",
    created_at=None,
    bucket_name="",
    original_file_name="thisisatest.csv",
    notification_count=1,
    notifications_sent=1,
    notifications_requested=1,
    job_status="finished",
    scheduled_for=None,
    processing_started=None,
):
    if job_id is None:
        job_id = str(generate_uuid())
    if template_id is None:
        template_id = "5d729fbd-239c-44ab-b498-75a985f3198f"
    if created_at is None:
        created_at = str(datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%S.%f%z"))
    data = {
        "id": job_id,
        "service": service_id,
        "template": template_id,
        "template_name": template_name,
        "template_version": template_version,
        "template_type": template_type,
        "original_file_name": original_file_name,
        "created_at": created_at,
        "notification_count": notification_count,
        "notifications_sent": notifications_sent,
        "notifications_requested": notifications_requested,
        "job_status": job_status,
        "statistics": [
            {
                "status": "blah",
                "count": notifications_requested,
            }
        ],
        "created_by": created_by_json(
            created_by["id"],
            created_by["name"],
            created_by["email_address"],
        ),
        "processing_started": processing_started,
        "scheduled_for": scheduled_for,
    }
    return data


def notification_json(  # noqa: C901
    service_id,
    job=None,
    template=None,
    to=None,
    status=None,
    sent_at=None,
    job_row_number=None,
    created_at=None,
    updated_at=None,
    with_links=False,
    rows=5,
    personalisation=None,
    template_type=None,
    reply_to_text=None,
    client_reference=None,
    created_by_name=None,
    postage=None,
    key_name=None,
):
    if template is None:
        template = template_json(service_id=service_id, id_=str(generate_uuid()), type_=template_type)
    if to is None:
        if template_type == "letter":
            to = "1 Example Street"
        elif template_type == "email":
            to = "example@gov.uk"
        else:
            to = "07123456789"
    if sent_at is None:
        sent_at = str(datetime.utcnow().time())
    if created_at is None:
        created_at = datetime.now(UTC).isoformat()
    if updated_at is None:
        updated_at = str((datetime.utcnow() + timedelta(minutes=1)).time())
    if status is None:
        status = "delivered"
    links = {}
    if template_type == "letter":
        postage = postage or "second"

    if with_links:
        links = {
            "prev": f"/service/{service_id}/notifications?page=0",
            "next": f"/service/{service_id}/notifications?page=1",
            "last": f"/service/{service_id}/notifications?page=2",
        }

    job_payload = None
    if job:
        job_payload = {"id": job["id"], "original_file_name": job["original_file_name"]}

    def _get_notification_id(index):
        if index < 16:
            return "{}{}{}{}{}{}{}{}-{}{}{}{}-{}{}{}{}-{}{}{}{}-{}{}{}{}{}{}{}{}{}{}{}{}".format(
                *repeat(hex(index)[2:], 32)
            )
        return str(uuid.uuid4())

    data = {
        "notifications": [
            {
                "id": _get_notification_id(i),
                "to": to,
                "template": template,
                "job": job_payload,
                "sent_at": sent_at,
                "status": status,
                "created_at": created_at,
                "created_by": None,
                "updated_at": updated_at,
                "job_row_number": job_row_number,
                "service": service_id,
                "template_version": template["version"],
                "personalisation": personalisation or {},
                "postage": postage,
                "notification_type": template_type,
                "reply_to_text": reply_to_text,
                "client_reference": client_reference,
                "created_by_name": created_by_name,
                "key_name": key_name,
            }
            for i in range(rows)
        ],
        "total": rows,
        "page_size": 50,
        "links": links,
    }
    return data


def single_notification_json(
    service_id,
    job=None,
    template=None,
    status=None,
    sent_at=None,
    created_at=None,
    updated_at=None,
    notification_type="sms",
):
    if template is None:
        template = template_json(service_id=service_id, id_=str(generate_uuid()))
    if sent_at is None:
        sent_at = str(datetime.utcnow())
    if created_at is None:
        created_at = str(datetime.utcnow())
    if updated_at is None:
        updated_at = str(datetime.utcnow() + timedelta(minutes=1))
    if status is None:
        status = "delivered"
    job_payload = None
    if job:
        job_payload = {"id": job["id"], "original_file_name": job["original_file_name"]}

    data = {
        "sent_at": sent_at,
        "to": "07123456789",
        "billable_units": 1,
        "status": status,
        "created_at": created_at,
        "reference": None,
        "updated_at": updated_at,
        "template_version": 5,
        "service": service_id,
        "id": "29441662-17ce-4ffe-9502-fcaed73b2826",
        "template": template,
        "job_row_number": 0,
        "notification_type": notification_type,
        "api_key": None,
        "job": job_payload,
        "sent_by": "mmg",
    }
    return data


def validate_route_permission(
    mocker, notify_admin, method, response_code, route, permissions, usr, service, session=None
):
    usr["permissions"][str(service["id"])] = permissions
    usr["services"] = [service["id"]]
    mocker.patch("app.user_api_client.check_verify_code", return_value=(True, ""))
    mocker.patch("app.service_api_client.get_services", return_value={"data": []})
    mocker.patch("app.service_api_client.update_service", return_value=service)
    mocker.patch("app.user_api_client.get_user", return_value=usr)
    mocker.patch("app.user_api_client.get_user_by_email", return_value=usr)
    mocker.patch("app.service_api_client.get_service", return_value={"data": service})
    mocker.patch("app.models.user.Users._get_items", return_value=[usr])
    mocker.patch("app.job_api_client.has_jobs", return_value=False)
    with notify_admin.test_request_context():
        with notify_admin.test_client() as client:
            client.login(usr)
            if session:
                with client.session_transaction() as session_:
                    for k, v in session.items():
                        session_[k] = v
            resp = None
            if method == "GET":
                resp = client.get(route)
            elif method == "POST":
                resp = client.post(route)
            else:
                pytest.fail(f"Invalid method call {method}")
            if resp.status_code != response_code:
                pytest.fail(f"Invalid permissions set for endpoint {route}")
    return resp


def validate_route_permission_with_client(mocker, client, method, response_code, route, permissions, usr, service):
    usr["permissions"][str(service["id"])] = permissions
    mocker.patch("app.user_api_client.check_verify_code", return_value=(True, ""))
    mocker.patch("app.service_api_client.get_services", return_value={"data": []})
    mocker.patch("app.service_api_client.update_service", return_value=service)
    mocker.patch("app.user_api_client.get_user", return_value=usr)
    mocker.patch("app.user_api_client.get_user_by_email", return_value=usr)
    mocker.patch("app.service_api_client.get_service", return_value={"data": service})
    mocker.patch("app.user_api_client.get_users_for_service", return_value=[usr])
    mocker.patch("app.job_api_client.has_jobs", return_value=False)
    client.login(usr)
    resp = None
    if method == "GET":
        resp = client.get_response_from_url(route, _expected_status=response_code)
    elif method == "POST":
        resp = client.post_response_from_url(route, _expected_status=response_code)
    else:
        pytest.fail(f"Invalid method call {method}")
    if resp.status_code != response_code:
        pytest.fail(f"Invalid permissions set for endpoint {route}")
    return resp


def assert_url_expected(actual, expected):
    actual_parts = urlparse(actual)
    expected_parts = urlparse(expected)
    for attribute in actual_parts._fields:
        if attribute == "query":
            # query string ordering can be non-deterministic
            # so we need to parse it first, which gives us a
            # dictionary of keys and values, not a
            # serialized string
            assert parse_qs(expected_parts.query) == parse_qs(actual_parts.query)
        else:
            assert getattr(actual_parts, attribute) == getattr(expected_parts, attribute), (
                f"Expected redirect: {expected}\nActual redirect: {actual}"
            )


def find_element_by_tag_and_partial_text(page, tag, string):
    return [e for e in page.select(tag) if string in e.text][0]


def contact_list_json(
    *,
    id_=None,
    created_at="2020-06-13T09:59:56.000000Z",
    created_by="Test User",
    service_id,
    original_file_name="EmergencyContactList.xls",
    row_count=100,
    recent_job_count=0,
    has_jobs=True,
    template_type="email",
):
    return {
        "id": id_ or sample_uuid(),
        "created_at": created_at,
        "created_by": created_by,
        "service_id": service_id,
        "original_file_name": original_file_name,
        "row_count": row_count,
        "recent_job_count": recent_job_count,
        "has_jobs": has_jobs,
        "template_type": template_type,
    }
