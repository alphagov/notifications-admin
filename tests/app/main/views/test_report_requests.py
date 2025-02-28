import uuid
from io import BytesIO

from notifications_python_client.errors import HTTPError

from app.main.views.report_requests import ReportRequest
from tests.conftest import SERVICE_ONE_ID, create_report_request


def test_report_request_download_gets_file_from_s3(client_request, fake_uuid, platform_admin_user, mocker):
    report_request = create_report_request(id="5bf2a1f9-0e6b-4d5e-b409-3509bf7a37b0", user_id=fake_uuid)
    mocker.patch("app.report_request_api_client.get_report_request", return_value={"data": report_request})
    mocker.patch.object(ReportRequest, "download", return_value=BytesIO(b"my notifications file"))

    client_request.login(platform_admin_user)
    response = client_request.get_response(
        "main.report_request_download",
        service_id=SERVICE_ONE_ID,
        report_request_id=report_request["id"],
    )

    assert response.get_data() == b"my notifications file"
    assert response.headers["Content-Type"] == "text/csv; charset=utf-8"
    assert response.headers["Content-Disposition"] == (f"attachment; filename={report_request['id']}.csv")


def test_report_request_download_when_report_does_not_exist(client_request, fake_uuid, platform_admin_user, mocker):
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

    client_request.login(platform_admin_user)
    client_request.get(
        "main.report_request_download",
        service_id=SERVICE_ONE_ID,
        report_request_id=fake_uuid,
        _expected_status=404,
    )


def test_report_request_download_for_wrong_user(client_request, platform_admin_user, mocker):
    request = create_report_request(service_id=SERVICE_ONE_ID, user_id=uuid.uuid4())
    mocker.patch("app.report_request_api_client.get_report_request", return_value={"data": request})

    client_request.login(platform_admin_user)
    client_request.get(
        "main.report_request_download",
        service_id=SERVICE_ONE_ID,
        report_request_id=request["id"],
        _expected_status=403,
    )


def test_report_request_download_when_report_is_in_wrong_status(client_request, fake_uuid, platform_admin_user, mocker):
    request = create_report_request(user_id=fake_uuid, status="deleted")
    mocker.patch("app.report_request_api_client.get_report_request", return_value={"data": request})

    client_request.login(platform_admin_user)
    client_request.get(
        "main.report_request_download",
        service_id=SERVICE_ONE_ID,
        report_request_id=request["id"],
        _expected_status=404,
    )
