import json
import uuid
from io import BytesIO

import pytest
from flask import url_for
from notifications_python_client.errors import HTTPError

from app.main.views_nl.report_requests import ReportRequest
from tests.conftest import SERVICE_ONE_ID, create_report_request


def test_report_request_download_gets_file_from_s3(client_request, fake_uuid, mocker):
    report_request = create_report_request(id="5bf2a1f9-0e6b-4d5e-b409-3509bf7a37b0", user_id=fake_uuid)
    mocker.patch("app.report_request_api_client.get_report_request", return_value={"data": report_request})
    mocker.patch.object(ReportRequest, "download", return_value=BytesIO(b"my notifications file"))

    response = client_request.get_response(
        "main.report_request_download",
        service_id=SERVICE_ONE_ID,
        report_request_id=report_request["id"],
    )

    assert response.get_data() == b"my notifications file"
    assert response.headers["Content-Type"] == "text/csv; charset=utf-8"
    assert response.headers["Content-Disposition"] == (f"attachment; filename={report_request['id']}.csv")


def test_report_request_download_when_report_does_not_exist(client_request, fake_uuid, mocker):
    mocker.patch(
        "app.report_request_api_client.get_report_request",
        side_effect=HTTPError(
            response=mocker.Mock(
                status_code=404,
                json={
                    "result": "error",
                    "message": "No result found",
                },
            ),
            message="No result found",
        ),
    )

    client_request.get(
        "main.report_request_download",
        service_id=SERVICE_ONE_ID,
        report_request_id=fake_uuid,
        _expected_status=404,
    )


def test_report_request_download_for_wrong_user(client_request, mocker):
    request = create_report_request(service_id=SERVICE_ONE_ID, user_id=uuid.uuid4())
    mocker.patch("app.report_request_api_client.get_report_request", return_value={"data": request})

    client_request.get(
        "main.report_request_download",
        service_id=SERVICE_ONE_ID,
        report_request_id=request["id"],
        _expected_status=403,
    )


def test_report_request_download_when_report_is_in_wrong_status(client_request, fake_uuid, mocker):
    request = create_report_request(user_id=fake_uuid, status="deleted")
    mocker.patch("app.report_request_api_client.get_report_request", return_value={"data": request})

    client_request.get(
        "main.report_request_download",
        service_id=SERVICE_ONE_ID,
        report_request_id=request["id"],
        _expected_status=404,
    )


@pytest.mark.skip(reason="[NOTIFYNL] Translation issue")
def test_report_request_renders_preparing_template_if_report_in_progress(
    client_request, fake_uuid, mocker, mock_get_service_data_retention
):
    request = create_report_request(
        user_id=fake_uuid,
        status="in_progress",
        parameter={"notification_type": "sms", "notification_status": "sending"},
    )
    mocker.patch("app.report_request_api_client.get_report_request", return_value={"data": request})

    page = client_request.get(
        "main.report_request",
        service_id=SERVICE_ONE_ID,
        report_request_id=request["id"],
    )

    assert page.select_one("h1").text == "Preparing your report"
    assert "text messages with the ‘sending’ status from the last 7 days" in page.select_one("p").text


def test_report_request_redirects_to_ready_if_report_stored(client_request, fake_uuid, mocker):
    request = create_report_request(user_id=fake_uuid, status="stored")
    mocker.patch("app.report_request_api_client.get_report_request", return_value={"data": request})

    response = client_request.get_response(
        "main.report_request",
        service_id=SERVICE_ONE_ID,
        report_request_id=request["id"],
        _expected_status=302,
    )

    assert response.location == url_for(
        "main.report_ready",
        service_id=SERVICE_ONE_ID,
        report_request_id=request["id"],
    )


@pytest.mark.skip(reason="[NOTIFYNL] Translation issue")
def test_report_request_renders_error_template_if_report_failed(client_request, fake_uuid, mocker):
    request = create_report_request(user_id=fake_uuid, status="failed")
    mocker.patch("app.report_request_api_client.get_report_request", return_value={"data": request})

    page = client_request.get(
        "main.report_request",
        service_id=SERVICE_ONE_ID,
        report_request_id=request["id"],
        _test_page_title=False,
    )

    assert page.select_one(".banner-dangerous h1").text.strip() == "We could not create your report"


@pytest.mark.skip(reason="[NOTIFYNL] Translation issue")
def test_report_request_renders_unavailable_template_if_report_not_found(client_request, fake_uuid, mocker):
    mocker.patch(
        "app.report_request_api_client.get_report_request",
        side_effect=HTTPError(
            response=mocker.Mock(
                status_code=404,
                json={"result": "error", "message": "No result found"},
            ),
            message="No result found",
        ),
    )

    page = client_request.get(
        "main.report_request",
        service_id=SERVICE_ONE_ID,
        report_request_id=fake_uuid,
    )

    assert page.select_one("h1").text == "Your report is no longer available"
    assert page.select_one("main a.govuk-link").text == "Go back to the dashboard to download a new report"
    assert page.select_one("main a.govuk-link")["href"] == url_for("main.service_dashboard", service_id=SERVICE_ONE_ID)


def test_report_request_raises_403_for_unauthorized_user(client_request, mocker):
    request = create_report_request(user_id=uuid.uuid4(), status="in_progress")
    mocker.patch("app.report_request_api_client.get_report_request", return_value={"data": request})

    response = client_request.get_response(
        "main.report_request",
        service_id=SERVICE_ONE_ID,
        report_request_id=request["id"],
        _expected_status=403,
    )

    assert response.status_code == 403


@pytest.mark.skip(reason="[NOTIFYNL] Translation issue")
def test_report_ready_renders_ready_template_if_report_ready(
    client_request, fake_uuid, mocker, mock_get_service_data_retention
):
    request = create_report_request(
        user_id=fake_uuid, status="stored", parameter={"notification_type": "sms", "notification_status": "all"}
    )
    mocker.patch("app.report_request_api_client.get_report_request", return_value={"data": request})
    mocker.patch.object(ReportRequest, "exists_in_s3", return_value=True)

    page = client_request.get(
        "main.report_ready",
        service_id=SERVICE_ONE_ID,
        report_request_id=request["id"],
    )

    assert page.select_one("h1").text == "Your report is ready to download"
    assert "all text messages from the last 7 days" in page.select_one("p").text.strip()


def test_report_ready_redirects_to_report_request_if_report_not_ready(client_request, fake_uuid, mocker):
    request = create_report_request(user_id=fake_uuid, status="in_progress")
    mocker.patch("app.report_request_api_client.get_report_request", return_value={"data": request})
    mocker.patch.object(ReportRequest, "exists_in_s3", return_value=True)

    response = client_request.get_response(
        "main.report_ready",
        service_id=SERVICE_ONE_ID,
        report_request_id=request["id"],
        _expected_status=302,
    )

    assert response.location == url_for(
        "main.report_request",
        service_id=SERVICE_ONE_ID,
        report_request_id=request["id"],
    )


def test_report_ready_redirects_to_report_request_if_report_not_found(client_request, fake_uuid, mocker):
    mocker.patch(
        "app.report_request_api_client.get_report_request",
        side_effect=HTTPError(
            response=mocker.Mock(
                status_code=404,
                json={"result": "error", "message": "No result found"},
            ),
            message="No result found",
        ),
    )
    mocker.patch.object(ReportRequest, "exists_in_s3", return_value=True)

    response = client_request.get_response(
        "main.report_ready",
        service_id=SERVICE_ONE_ID,
        report_request_id=fake_uuid,
        _expected_status=302,
    )
    assert response.location == url_for(
        "main.report_request",
        service_id=SERVICE_ONE_ID,
        report_request_id=fake_uuid,
    )


def test_report_ready_raises_403_for_unauthorized_user(client_request, mocker):
    request = create_report_request(user_id=uuid.uuid4(), status="stored")
    mocker.patch("app.report_request_api_client.get_report_request", return_value={"data": request})
    mocker.patch.object(ReportRequest, "exists_in_s3", return_value=True)

    response = client_request.get_response(
        "main.report_ready",
        service_id=SERVICE_ONE_ID,
        report_request_id=request["id"],
        _expected_status=403,
    )

    assert response.status_code == 403


@pytest.mark.skip(reason="[NOTIFYNL] Translation issue")
def test_report_ready_redirects_not_found_when_report_does_not_exist(client_request, fake_uuid, mocker):
    request = create_report_request(
        user_id=fake_uuid, status="stored", parameter={"notification_type": "sms", "notification_status": "all"}
    )
    mocker.patch("app.report_request_api_client.get_report_request", return_value={"data": request})
    mocker.patch.object(ReportRequest, "exists_in_s3", return_value=False)

    page = client_request.get(
        "main.report_ready",
        service_id=SERVICE_ONE_ID,
        report_request_id=request["id"],
    )

    assert page.select_one("h1").text == "Your report is no longer available"
    assert page.select_one("main a.govuk-link").text == "Go back to the dashboard to download a new report"
    assert page.select_one("main a.govuk-link")["href"] == url_for("main.service_dashboard", service_id=SERVICE_ONE_ID)


def test_report_request_status_json_returns_status(client_request, fake_uuid, mocker):
    request = create_report_request(user_id=fake_uuid, status="stored")
    mocker.patch("app.report_request_api_client.get_report_request", return_value={"data": request})
    response = client_request.get_response(
        "main.report_request_status_json",
        service_id=SERVICE_ONE_ID,
        report_request_id=request["id"],
    )

    assert json.loads(response.get_data(as_text=True)) == {"status": "stored"}
