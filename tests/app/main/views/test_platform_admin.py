import datetime
import uuid
from unittest.mock import ANY, call

import pytest
from flask import url_for

from app.main.views_nl.platform_admin import (
    build_live_service_permissions_for_users_list,
    create_global_stats,
    format_stats_by_service,
    get_tech_failure_status_box_data,
    is_over_threshold,
    sum_service_usage,
)
from tests import service_json
from tests.conftest import SERVICE_ONE_ID, SERVICE_TWO_ID, create_user, normalize_spaces


def test_should_redirect_if_not_logged_in(client_request):
    client_request.logout()
    client_request.get(
        "main.platform_admin_search",
        _expected_redirect=url_for("main.sign_in", next=url_for("main.platform_admin_search")),
    )


def test_should_403_if_not_platform_admin(client_request):
    client_request.get("main.platform_admin_search", _expected_status=403)


def test_create_global_stats_sets_failure_rates(fake_uuid):
    services = [service_json(fake_uuid, "a", []), service_json(fake_uuid, "b", [])]
    services[0]["statistics"] = create_stats(
        emails_requested=1,
        emails_delivered=1,
        emails_failed=0,
    )
    services[1]["statistics"] = create_stats(
        emails_requested=2,
        emails_delivered=1,
        emails_failed=1,
    )

    stats = create_global_stats(services)
    assert stats == {
        "email": {"delivered": 2, "failed": 1, "requested": 3, "failure_rate": "33.3"},
        "sms": {"delivered": 0, "failed": 0, "requested": 0, "failure_rate": "0"},
        "letter": {"delivered": 0, "failed": 0, "requested": 0, "failure_rate": "0"},
    }


def create_stats(
    emails_requested=0,
    emails_delivered=0,
    emails_failed=0,
    sms_requested=0,
    sms_delivered=0,
    sms_failed=0,
    letters_requested=0,
    letters_delivered=0,
    letters_failed=0,
):
    return {
        "sms": {
            "requested": sms_requested,
            "delivered": sms_delivered,
            "failed": sms_failed,
        },
        "email": {
            "requested": emails_requested,
            "delivered": emails_delivered,
            "failed": emails_failed,
        },
        "letter": {
            "requested": letters_requested,
            "delivered": letters_delivered,
            "failed": letters_failed,
        },
    }


def test_format_stats_by_service_returns_correct_values(fake_uuid):
    services = [service_json(fake_uuid, "a", [])]
    services[0]["statistics"] = create_stats(
        emails_requested=10,
        emails_delivered=3,
        emails_failed=5,
        sms_requested=50,
        sms_delivered=7,
        sms_failed=11,
        letters_requested=40,
        letters_delivered=20,
        letters_failed=7,
    )

    ret = list(format_stats_by_service(services))
    assert len(ret) == 1

    assert ret[0]["stats"]["email"]["requested"] == 10
    assert ret[0]["stats"]["email"]["delivered"] == 3
    assert ret[0]["stats"]["email"]["failed"] == 5

    assert ret[0]["stats"]["sms"]["requested"] == 50
    assert ret[0]["stats"]["sms"]["delivered"] == 7
    assert ret[0]["stats"]["sms"]["failed"] == 11

    assert ret[0]["stats"]["letter"]["requested"] == 40
    assert ret[0]["stats"]["letter"]["delivered"] == 20
    assert ret[0]["stats"]["letter"]["failed"] == 7


def test_sum_service_usage_is_sum_of_all_activity(fake_uuid):
    service = service_json(fake_uuid, "My Service 1")
    service["statistics"] = create_stats(
        emails_requested=100, emails_delivered=25, emails_failed=25, sms_requested=100, sms_delivered=25, sms_failed=25
    )
    assert sum_service_usage(service) == 200


def test_sum_service_usage_with_zeros(fake_uuid):
    service = service_json(fake_uuid, "My Service 1")
    service["statistics"] = create_stats(
        emails_requested=0, emails_delivered=0, emails_failed=25, sms_requested=0, sms_delivered=0, sms_failed=0
    )
    assert sum_service_usage(service) == 0


@pytest.mark.skip(reason="[NOTIFYNL] Translation issue")
def test_platform_admin_list_complaints(client_request, platform_admin_user, mocker):
    complaint = {
        "id": str(uuid.uuid4()),
        "notification_id": str(uuid.uuid4()),
        "service_id": str(uuid.uuid4()),
        "service_name": "Sample service",
        "ses_feedback_id": "Some ses id",
        "complaint_type": "abuse",
        "complaint_date": "2018-06-05T13:50:30.012354",
        "created_at": "2018-06-05T13:50:30.012354",
    }
    mock = mocker.patch(
        "app.complaint_api_client.get_all_complaints", return_value={"complaints": [complaint], "links": {}}
    )

    client_request.login(platform_admin_user)
    page = client_request.get("main.platform_admin_list_complaints")

    assert "Email complaints" in page.text
    assert mock.called


def test_should_show_complaints_with_next_previous(
    client_request,
    platform_admin_user,
    mocker,
    service_one,
    fake_uuid,
):
    api_response = {
        "complaints": [
            {
                "complaint_date": None,
                "complaint_type": None,
                "created_at": "2017-12-18T05:00:00.000000Z",
                "id": fake_uuid,
                "notification_id": fake_uuid,
                "service_id": service_one["id"],
                "service_name": service_one["name"],
                "ses_feedback_id": "None",
            }
        ],
        "links": {"last": "/complaint?page=3", "next": "/complaint?page=3", "prev": "/complaint?page=1"},
    }

    mocker.patch("app.complaint_api_client.get_all_complaints", return_value=api_response)

    client_request.login(platform_admin_user)
    page = client_request.get(
        "main.platform_admin_list_complaints",
        page=2,
    )

    next_page_link = page.select_one("a[rel=next]")
    prev_page_link = page.select_one("a[rel=previous]")
    assert url_for("main.platform_admin_list_complaints", page=3) in next_page_link["href"]
    assert "Next page" in next_page_link.text.strip()
    assert "page 3" in next_page_link.text.strip()
    assert url_for("main.platform_admin_list_complaints", page=1) in prev_page_link["href"]
    assert "Previous page" in prev_page_link.text.strip()
    assert "page 1" in prev_page_link.text.strip()


def test_platform_admin_list_complaints_returns_404_with_invalid_page(
    client_request,
    platform_admin_user,
    mocker,
):
    mocker.patch("app.complaint_api_client.get_all_complaints", return_value={"complaints": [], "links": {}})

    client_request.login(platform_admin_user)
    client_request.get(
        "main.platform_admin_list_complaints",
        page="invalid",
        _expected_status=404,
    )


@pytest.mark.parametrize(
    "number, total, threshold, result",
    [
        (0, 0, 0, False),
        (1, 1, 0, True),
        (2, 3, 66, True),
        (2, 3, 67, False),
    ],
)
def test_is_over_threshold(number, total, threshold, result):
    assert is_over_threshold(number, total, threshold) is result


def test_get_tech_failure_status_box_data_removes_percentage_data():
    stats = {
        "failures": {"permanent-failure": 0, "technical-failure": 0, "temporary-failure": 1, "virus-scan-failed": 0},
        "test-key": 0,
        "total": 5589,
    }
    tech_failure_data = get_tech_failure_status_box_data(stats)

    assert "percentage" not in tech_failure_data


def test_platform_admin_show_submit_returned_letters_page(
    client_request,
    platform_admin_user,
):
    client_request.login(platform_admin_user)
    client_request.get("main.platform_admin_returned_letters")


def test_platform_admin_submit_returned_letters(
    client_request,
    platform_admin_user,
    mocker,
):
    mock_client = mocker.patch("app.letter_jobs_client.submit_returned_letters")

    client_request.login(platform_admin_user)
    client_request.post(
        "main.platform_admin_returned_letters",
        _data={"references": " NOTIFY000REF1 \n NOTIFY002REF2 "},
        _expected_redirect=url_for(
            "main.platform_admin_returned_letters",
        ),
    )

    mock_client.assert_called_once_with(["REF1", "REF2"])


def test_platform_admin_submit_empty_returned_letters(
    client_request,
    platform_admin_user,
    mocker,
):
    mock_client = mocker.patch("app.letter_jobs_client.submit_returned_letters")

    client_request.login(platform_admin_user)
    page = client_request.post(
        "main.platform_admin_returned_letters",
        _data={"references": "  \n  "},
        _expected_status=200,
    )

    assert not mock_client.called

    assert "Enter the returned letter references" in page.text


def test_clear_cache_shows_form(
    client_request,
    platform_admin_user,
    mocker,
):
    redis = mocker.patch("app.main.views_nl.platform_admin.redis_client")
    client_request.login(platform_admin_user)

    page = client_request.get("main.clear_cache")

    assert not redis.delete_by_pattern.called
    radios = {el["value"] for el in page.select("input[type=checkbox]")}

    assert radios == {
        "user",
        "service",
        "template",
        "email_branding",
        "letter_branding",
        "organisation",
        "text_message_and_letter_rates",
        "unsubscribe_request_reports",
        "service_join_request",
    }


@pytest.mark.skip(reason="[NOTIFYNL] Translation issue")
@pytest.mark.parametrize(
    "model_type, expected_calls, expected_confirmation",
    (
        (
            "template",
            [
                call("service-????????-????-????-????-????????????-templates"),
                call(
                    "service-????????-????-????-????-????????????-template-????????-????-????-????-????????????-version-*"
                ),
                call(
                    "service-????????-????-????-????-????????????-template-????????-????-????-????-????????????-versions"
                ),
                call(
                    "service-????????-????-????-????-????????????-template-????????-????-????-????-????????????-page-count"
                ),
                call("service-????????-????-????-????-????????????-template-precompiled"),
            ],
            "Removed 10 objects across 5 key formats for template",
        ),
        (
            ["service", "organisation"],
            [
                call("has_jobs-????????-????-????-????-????????????"),
                call("service-????????-????-????-????-????????????"),
                call("service-????????-????-????-????-????????????-templates"),
                call("service-????????-????-????-????-????????????-data-retention"),
                call("service-????????-????-????-????-????????????-template-folders"),
                call("service-????????-????-????-????-????????????-returned-letters-statistics"),
                call("service-????????-????-????-????-????????????-returned-letters-summary"),
                call("organisations"),
                call("domains"),
                call("live-service-and-organisation-counts"),
                call("organisation-????????-????-????-????-????????????-name"),
                call("organisation-????????-????-????-????-????????????-email-branding-pool"),
                call("organisation-????????-????-????-????-????????????-letter-branding-pool"),
            ],
            "Removed 26 objects across 13 key formats for service, organisation",
        ),
        (
            ["text_message_and_letter_rates"],
            [
                call("letter-rates"),
                call("sms-rate"),
            ],
            "Removed 4 objects across 2 key formats for text message and letter rates",
        ),
        (
            ["unsubscribe_request_reports"],
            [
                call("service-????????-????-????-????-????????????-unsubscribe-request-reports-summary"),
                call("service-????????-????-????-????-????????????-unsubscribe-request-statistics"),
            ],
            "Removed 4 objects across 2 key formats for unsubscribe request reports",
        ),
        (
            ["service_join_request"],
            [
                call("service-join-request-????????-????-????-????-????????????"),
            ],
            "Removed 2 objects across 1 key formats for service join request",
        ),
    ),
)
def test_clear_cache_submits_and_tells_you_how_many_things_were_deleted(
    client_request,
    platform_admin_user,
    model_type,
    expected_calls,
    expected_confirmation,
    mocker,
):
    redis = mocker.patch("app.main.views_nl.platform_admin.redis_client")
    redis.delete_by_pattern.return_value = 2
    client_request.login(platform_admin_user)

    page = client_request.post("main.clear_cache", _data={"model_type": model_type}, _expected_status=200)

    assert redis.delete_by_pattern.call_args_list == expected_calls

    flash_banner = page.select_one("div.banner-default")
    assert flash_banner.text.strip() == expected_confirmation


def test_clear_cache_requires_option(
    client_request,
    platform_admin_user,
    mocker,
):
    redis = mocker.patch("app.main.views_nl.platform_admin.redis_client")
    client_request.login(platform_admin_user)

    page = client_request.post("main.clear_cache", _data={}, _expected_status=200)

    assert normalize_spaces(page.select_one(".govuk-error-message").text) == "Error: Select at least one type of cache"
    assert not redis.delete_by_pattern.called


@pytest.mark.skip(reason="[NOTIFYNL] Translation issue")
def test_reports_page(
    client_request,
    platform_admin_user,
):
    client_request.login(platform_admin_user)
    page = client_request.get("main.platform_admin_reports")

    live_services_link = page.select("main a")[0]
    assert live_services_link.text == "Download live services csv report"
    assert live_services_link["href"] == "/platform-admin/reports/live-services.csv"

    monthly_statuses_link = page.select("main a")[1]
    assert monthly_statuses_link.text == "Monthly notification statuses for live services"
    assert monthly_statuses_link["href"] == url_for("main.notifications_sent_by_service")


def test_get_live_services_report(
    client_request,
    platform_admin_user,
    mocker,
):
    mocker.patch(
        "app.service_api_client.get_live_services_data",
        return_value={
            "data": [
                {
                    "service_id": 1,
                    "service_name": "jessie the oak tree",
                    "organisation_name": "Forest",
                    "consent_to_research": True,
                    "contact_name": "Forest fairy",
                    "organisation_type": "Ecosystem",
                    "contact_email": "forest.fairy@digital.cabinet-office.gov.uk",
                    "contact_mobile": "+447700900986",
                    "live_date": "Sat, 29 Mar 2014 00:00:00 GMT",
                    "sms_volume_intent": 100,
                    "email_volume_intent": 50,
                    "letter_volume_intent": 20,
                    "sms_totals": 300,
                    "email_totals": 1200,
                    "letter_totals": 0,
                    "free_sms_fragment_limit": 100,
                },
                {
                    "service_id": 2,
                    "service_name": "james the pine tree",
                    "organisation_name": "Forest",
                    "consent_to_research": None,
                    "contact_name": None,
                    "organisation_type": "Ecosystem",
                    "contact_email": None,
                    "contact_mobile": None,
                    "live_date": None,
                    "sms_volume_intent": None,
                    "email_volume_intent": 60,
                    "letter_volume_intent": 0,
                    "sms_totals": 0,
                    "email_totals": 0,
                    "letter_totals": 0,
                    "free_sms_fragment_limit": 200,
                },
            ]
        },
    )
    client_request.login(platform_admin_user)
    response = client_request.get_response(
        "main.live_services_csv",
    )
    report = response.get_data(as_text=True)
    assert report.strip() == (
        "Service ID,Organisation,Organisation type,Service name,Consent to research,Main contact,Contact email,"
        "Contact mobile,Live date,SMS volume intent,Email volume intent,Letter volume intent,SMS sent this year,"
        "Emails sent this year,Letters sent this year,Free sms allowance\r\n"
        "1,Forest,Ecosystem,jessie the oak tree,True,Forest fairy,forest.fairy@digital.cabinet-office.gov.uk,"
        "+447700900986,29-03-2014,100,50,20,300,1200,0,100\r\n"
        "2,Forest,Ecosystem,james the pine tree,,,,,,,60,0,0,0,0,200"
    )


def test_get_notifications_sent_by_service_shows_date_form(
    client_request,
    platform_admin_user,
):
    client_request.login(platform_admin_user)
    page = client_request.get("main.notifications_sent_by_service")

    assert [(input["type"], input["name"], input.get("value")) for input in page.select("input")] == [
        ("text", "start_date", None),
        ("text", "end_date", None),
        ("hidden", "csrf_token", ANY),
    ]


def test_get_notifications_sent_by_service_validates_form(
    client_request,
    platform_admin_user,
    mocker,
):
    mock_get_stats_from_api = mocker.patch("app.main.views_nl.platform_admin.notification_api_client")

    client_request.login(platform_admin_user)

    page = client_request.post(
        "main.notifications_sent_by_service", _expected_status=200, _data={"start_date": "", "end_date": "20190101"}
    )

    errors = page.select(".govuk-error-message")
    assert len(errors) == 2

    assert [error.text.strip() for error in errors] == [
        "Error: Enter a start date in the correct format",
        "Error: Enter an end date in the correct format",
    ]

    assert mock_get_stats_from_api.called is False


def test_get_billing_report_when_no_results_for_date(client_request, platform_admin_user, mocker):
    client_request.login(platform_admin_user)

    mocker.patch("app.main.views_nl.platform_admin.billing_api_client.get_data_for_billing_report", return_value=[])

    page = client_request.post(
        "main.get_billing_report", _expected_status=200, _data={"start_date": "2019-01-01", "end_date": "2019-03-31"}
    )

    error = page.select_one(".banner-dangerous")
    assert normalize_spaces(error.text) == "No results for dates"


def test_get_billing_report_calls_api_and_download_data(client_request, platform_admin_user, mocker):
    mocker.patch(
        "app.main.views_nl.platform_admin.billing_api_client.get_data_for_billing_report",
        return_value=[
            {
                "letter_breakdown": "6 second class letters at 45p\n2 first class letters at 35p\n",
                "total_letters": 8,
                "letter_cost": 3.4,
                "organisation_id": "7832a1be-a1f0-4f2a-982f-05adfd3d6354",
                "organisation_name": "Org for a - with sms and letter",
                "service_id": "48e82ac0-c8c4-4e46-8712-c83c35a94006",
                "service_name": "a - with sms and letter",
                "sms_cost": 0,
                "sms_chargeable_units": 0,
                "purchase_order_number": "PO1234",
                "contact_names": "Anne, Marie, Josh",
                "contact_email_addresses": "billing@example.com, accounts@example.com",
                "billing_reference": "Notify2020",
            }
        ],
    )

    client_request.login(platform_admin_user)
    response = client_request.post_response(
        "main.get_billing_report",
        _data={"start_date": "2019-01-01", "end_date": "2019-03-31"},
        _expected_status=200,
    )

    assert response.content_type == "text/csv; charset=utf-8"
    assert response.headers["Content-Disposition"] == (
        'attachment; filename="Billing Report from 2019-01-01 to 2019-03-31.csv"'
    )

    assert response.get_data(as_text=True) == (
        "organisation_id,organisation_name,service_id,service_name,sms_cost,sms_chargeable_units,"
        "total_letters,letter_cost,letter_breakdown,purchase_order_number,contact_names,contact_email_addresses,"
        "billing_reference\r\n"
        "7832a1be-a1f0-4f2a-982f-05adfd3d6354,"
        "Org for a - with sms and letter,"
        "48e82ac0-c8c4-4e46-8712-c83c35a94006,"
        "a - with sms and letter,"
        "0,"
        "0,"
        "8,"
        "3.4,"
        '"6 second class letters at 45p'
        "\n"
        '2 first class letters at 35p",'
        'PO1234,"Anne, Marie, Josh","billing@example.com, accounts@example.com",Notify2020'
        "\r\n"
    )


class TestGetDvlaBillingReport:
    def test_when_no_results_for_date(self, client_request, platform_admin_user, mocker):
        client_request.login(platform_admin_user)

        mocker.patch(
            "app.main.views_nl.platform_admin.billing_api_client.get_data_for_dvla_billing_report", return_value=[]
        )

        page = client_request.post(
            "main.get_dvla_billing_report",
            _expected_status=200,
            _data={"start_date": "2023-06-01", "end_date": "2023-06-01"},
        )

        error = page.select_one(".banner-dangerous")
        assert normalize_spaces(error.text) == "No results for dates"

    def test_calls_api_and_downloads_data(self, client_request, platform_admin_user, mocker):
        mocker.patch(
            "app.main.views_nl.platform_admin.billing_api_client.get_data_for_dvla_billing_report",
            return_value=[
                {
                    "date": "2023-06-01",
                    "postage": "first",
                    "cost_threshold": "sorted",
                    "sheets": 1,
                    "rate": 1.0,
                    "letters": 10,
                    "cost": 10.0,
                },
                {
                    "date": "2023-06-01",
                    "postage": "second",
                    "cost_threshold": "sorted",
                    "sheets": 1,
                    "rate": 0.5,
                    "letters": 50,
                    "cost": 25.0,
                },
                {
                    "date": "2023-06-01",
                    "postage": "second",
                    "cost_threshold": "unsorted",
                    "sheets": 3,
                    "rate": 0.75,
                    "letters": 5,
                    "cost": 3.75,
                },
            ],
        )

        client_request.login(platform_admin_user)
        response = client_request.post_response(
            "main.get_dvla_billing_report",
            _data={"start_date": "2023-06-01", "end_date": "2023-06-01"},
            _expected_status=200,
        )

        assert response.content_type == "text/csv; charset=utf-8"
        assert response.headers["Content-Disposition"] == (
            'attachment; filename="DVLA Billing Report from 2023-06-01 to 2023-06-01.csv"'
        )

        assert response.get_data(as_text=True) == (
            "despatch date,postage,DVLA cost threshold,sheets,rate (£),letters,cost (£)\r\n"
            "2023-06-01,first,sorted,1,1.0,10,10.0\r\n"
            "2023-06-01,second,sorted,1,0.5,50,25.0\r\n"
            "2023-06-01,second,unsorted,3,0.75,5,3.75\r\n"
        )


def test_get_notifications_sent_by_service_calls_api_and_downloads_data(
    client_request,
    platform_admin_user,
    service_one,
    service_two,
    mocker,
):
    api_data = [
        ["2019-01-01", SERVICE_ONE_ID, service_one["name"], "email", 191, 0, 0, 14, 0, 0],
        ["2019-01-01", SERVICE_ONE_ID, service_one["name"], "sms", 42, 0, 0, 8, 0, 0],
        ["2019-01-01", SERVICE_TWO_ID, service_two["name"], "email", 3, 1, 0, 2, 0, 0],
    ]
    mocker.patch(
        "app.main.views_nl.platform_admin.notification_api_client.get_notification_status_by_service",
        return_value=api_data,
    )
    start_date = datetime.date(2019, 1, 1)
    end_date = datetime.date(2019, 1, 31)

    client_request.login(platform_admin_user)
    response = client_request.post_response(
        "main.notifications_sent_by_service",
        _data={"start_date": start_date, "end_date": end_date},
        _expected_status=200,
    )

    assert response.content_type == "text/csv; charset=utf-8"
    assert response.headers["Content-Disposition"] == (
        f'attachment; filename="{start_date} to {end_date} notification status per service report.csv"'
    )
    assert response.get_data(as_text=True) == (
        "date_created,service_id,service_name,notification_type,count_sending,count_delivered,"
        "count_technical_failure,count_temporary_failure,count_permanent_failure,count_sent\r\n"
        "2019-01-01,596364a0-858e-42c8-9062-a8fe822260eb,service one,email,191,0,0,14,0,0\r\n"
        "2019-01-01,596364a0-858e-42c8-9062-a8fe822260eb,service one,sms,42,0,0,8,0,0\r\n"
        "2019-01-01,147ad62a-2951-4fa1-9ca0-093cd1a52c52,service two,email,3,1,0,2,0,0\r\n"
    )


def test_get_volumes_by_service_report_page(client_request, platform_admin_user, mocker):
    client_request.login(platform_admin_user)
    client_request.get(
        "main.get_volumes_by_service",
        _test_page_title=False,
    )


def test_get_volumes_by_service_report_calls_api_and_download_data(client_request, platform_admin_user, mocker):
    mocker.patch(
        "app.main.views_nl.platform_admin.billing_api_client.get_data_for_volumes_by_service_report",
        return_value=[
            {
                "organisation_id": "7832a1be-a1f0-4f2a-982f-05adfd3d6354",
                "organisation_name": "Org name",
                "service_id": "48e82ac0-c8c4-4e46-8712-c83c35a94006",
                "service_name": "service name",
                "free_allowance": 10000,
                "sms_notifications": 10,
                "sms_chargeable_units": 20,
                "email_totals": 8,
                "letter_totals": 10,
                "letter_cost": 4.5,
                "letter_sheet_totals": 10,
            }
        ],
    )

    client_request.login(platform_admin_user)
    response = client_request.post_response(
        "main.get_volumes_by_service",
        _data={"start_date": "2019-01-01", "end_date": "2019-03-31"},
        _expected_status=200,
    )

    assert response.content_type == "text/csv; charset=utf-8"
    assert response.headers["Content-Disposition"] == (
        'attachment; filename="Volumes by service report from 2019-01-01 to 2019-03-31.csv"'
    )

    assert response.get_data(as_text=True) == (
        "organisation id,organisation name,service id,service name,free allowance,sms notifications,"
        "sms chargeable units,email totals,letter totals,letter cost,letter sheet totals\r\n"
        "7832a1be-a1f0-4f2a-982f-05adfd3d6354,"
        "Org name,"
        "48e82ac0-c8c4-4e46-8712-c83c35a94006,"
        "service name,"
        "10000,"
        "10,"
        "20,"
        "8,"
        "10,"
        "4.5,"
        "10"
        "\r\n"
    )


def test_get_daily_volumes_report_page(client_request, platform_admin_user, mocker):
    client_request.login(platform_admin_user)
    client_request.get(
        "main.get_daily_volumes",
        _test_page_title=False,
    )


def test_get_daily_volumes_report_calls_api_and_download_data(client_request, platform_admin_user, mocker):
    mocker.patch(
        "app.main.views_nl.platform_admin.billing_api_client.get_data_for_daily_volumes_report",
        return_value=[
            {
                "day": "2019-01-01",
                "sms_totals": 20,
                "sms_fragment_totals": 40,
                "sms_chargeable_units": 60,
                "email_totals": 100,
                "letter_totals": 10,
                "letter_sheet_totals": 20,
            }
        ],
    )

    client_request.login(platform_admin_user)
    response = client_request.post_response(
        "main.get_daily_volumes",
        _data={"start_date": "2019-01-01", "end_date": "2019-03-31"},
        _expected_status=200,
    )

    assert response.content_type == "text/csv; charset=utf-8"
    assert response.headers["Content-Disposition"] == (
        'attachment; filename="Daily volumes report from 2019-01-01 to 2019-03-31.csv"'
    )

    assert response.get_data(as_text=True) == (
        "day,sms totals,sms fragment totals,sms chargeable units,email totals,letter totals,letter sheet totals\r\n"
        "2019-01-01,"
        "20,"
        "40,"
        "60,"
        "100,"
        "10,"
        "20"
        "\r\n"
    )


def test_get_daily_sms_provider_volumes_report_page(client_request, platform_admin_user, mocker):
    client_request.login(platform_admin_user)
    client_request.get("main.get_daily_sms_provider_volumes")


def test_get_daily_sms_provider_volumes_report_calls_api_and_download_data(client_request, platform_admin_user, mocker):
    mocker.patch(
        "app.main.views_nl.platform_admin.billing_api_client.get_data_for_daily_sms_provider_volumes_report",
        return_value=[
            {
                "day": "2019-01-01",
                "provider": "foo",
                "sms_totals": 20,
                "sms_fragment_totals": 40,
                "sms_chargeable_units": 60,
                "sms_cost": 80,
            }
        ],
    )

    client_request.login(platform_admin_user)
    response = client_request.post_response(
        "main.get_daily_sms_provider_volumes",
        _data={"start_date": "2019-01-01", "end_date": "2019-03-31"},
        _expected_status=200,
    )

    assert response.content_type == "text/csv; charset=utf-8"
    assert response.headers["Content-Disposition"] == (
        'attachment; filename="Daily SMS provider volumes report from 2019-01-01 to 2019-03-31.csv"'
    )

    assert response.get_data(as_text=True) == (
        "day,provider,sms totals,sms fragment totals,sms chargeable units,sms cost\r\n2019-01-01,foo,20,40,60,80\r\n"
    )


class TestPlatformAdminSearch:
    def test_page_requires_platform_admin(self, client_request):
        client_request.get(".platform_admin_search", _expected_status=403)

    @pytest.mark.skip(reason="[NOTIFYNL] Translation issue")
    def test_page_loads(self, client_request, platform_admin_user):
        client_request.login(platform_admin_user)
        client_request.get(".platform_admin_search")

    @pytest.mark.skip(reason="[NOTIFYNL] Translation issue")
    def test_can_search_for_user(self, client_request, platform_admin_user, active_caseworking_user, mocker):
        mocker.patch(
            "app.main.views_nl.platform_admin.user_api_client.find_users_by_full_or_partial_email",
            return_value={"data": [active_caseworking_user]},
        )
        mocker.patch(
            "app.main.views_nl.platform_admin.service_api_client.find_services_by_name",
            return_value={"data": []},
        )
        mocker.patch(
            "app.main.views_nl.platform_admin.organisations_client.search",
            return_value={"data": []},
        )
        mocker.patch("app.main.views_nl.platform_admin.get_url_for_notify_record", return_value=None)
        client_request.login(platform_admin_user)

        response = client_request.post(".platform_admin_search", _data={"search": "caseworker"}, _expected_status=200)

        assert normalize_spaces(response.select(".govuk-tabs ul")[0]) == "Users (1)"

        found_user_links = response.select(".govuk-tabs ul")[1].select("a")
        assert found_user_links[0].text == "caseworker@example.gov.uk"
        assert found_user_links[0].get("href") == "/users/6ce466d0-fd6a-11e5-82f5-e0accb9d11a6"

    @pytest.mark.skip(reason="[NOTIFYNL] Translation issue")
    def test_can_search_for_services(self, client_request, platform_admin_user, service_one, service_two, mocker):
        mocker.patch(
            "app.main.views_nl.platform_admin.user_api_client.find_users_by_full_or_partial_email",
            return_value={"data": []},
        )
        mocker.patch(
            "app.main.views_nl.platform_admin.service_api_client.find_services_by_name",
            return_value={"data": [service_one, service_two]},
        )
        mocker.patch(
            "app.main.views_nl.platform_admin.organisations_client.search",
            return_value={"data": []},
        )
        mocker.patch("app.main.views_nl.platform_admin.get_url_for_notify_record", return_value=None)
        client_request.login(platform_admin_user)

        response = client_request.post(".platform_admin_search", _data={"search": "service"}, _expected_status=200)

        assert normalize_spaces(response.select(".govuk-tabs ul")[0]) == "Services (2)"

        found_service_links = response.select(".govuk-tabs ul")[1].select("a")
        assert found_service_links[0].text == "service one"
        assert found_service_links[0].get("href") == "/services/596364a0-858e-42c8-9062-a8fe822260eb"
        assert found_service_links[1].text == "service two"
        assert found_service_links[1].get("href") == "/services/147ad62a-2951-4fa1-9ca0-093cd1a52c52"

    @pytest.mark.skip(reason="[NOTIFYNL] Translation issue")
    def test_can_search_for_organisations(self, client_request, platform_admin_user, organisation_one, mocker):
        mocker.patch(
            "app.main.views_nl.platform_admin.user_api_client.find_users_by_full_or_partial_email",
            return_value={"data": []},
        )
        mocker.patch(
            "app.main.views_nl.platform_admin.service_api_client.find_services_by_name",
            return_value={"data": []},
        )
        mocker.patch(
            "app.main.views_nl.platform_admin.organisations_client.search",
            return_value={"data": [organisation_one]},
        )
        mocker.patch("app.main.views_nl.platform_admin.get_url_for_notify_record", return_value=None)
        client_request.login(platform_admin_user)

        response = client_request.post(".platform_admin_search", _data={"search": "service"}, _expected_status=200)

        assert normalize_spaces(response.select(".govuk-tabs ul")[0]) == "Organisations (1)"

        found_service_links = response.select(".govuk-tabs ul")[1].select("a")
        assert found_service_links[0].text == "organisation one"
        assert found_service_links[0].get("href") == "/organisations/c011fa40-4cbe-4524-b415-dde2f421bd9c"

    @pytest.mark.skip(reason="[NOTIFYNL] Translation issue")
    def test_shows_results_from_all_categories(
        self,
        client_request,
        platform_admin_user,
        active_caseworking_user,
        service_one,
        service_two,
        organisation_one,
        mocker,
    ):
        mocker.patch(
            "app.main.views_nl.platform_admin.user_api_client.find_users_by_full_or_partial_email",
            return_value={"data": [active_caseworking_user]},
        )
        mocker.patch(
            "app.main.views_nl.platform_admin.service_api_client.find_services_by_name",
            return_value={"data": [service_one, service_two]},
        )
        mocker.patch(
            "app.main.views_nl.platform_admin.organisations_client.search",
            return_value={"data": [organisation_one]},
        )
        mocker.patch("app.main.views_nl.platform_admin.get_url_for_notify_record", return_value=None)
        client_request.login(platform_admin_user)

        response = client_request.post(".platform_admin_search", _data={"search": "blah"}, _expected_status=200)

        assert normalize_spaces(response.select(".govuk-tabs ul")[0]) == "Users (1) Services (2) Organisations (1)"

        found_user_links = response.select(".govuk-tabs ul")[1].select("a")
        assert found_user_links[0].text == "caseworker@example.gov.uk"
        assert found_user_links[0].get("href") == "/users/6ce466d0-fd6a-11e5-82f5-e0accb9d11a6"

        found_service_links = response.select(".govuk-tabs ul")[2].select("a")
        assert found_service_links[0].text == "service one"
        assert found_service_links[0].get("href") == "/services/596364a0-858e-42c8-9062-a8fe822260eb"
        assert found_service_links[1].text == "service two"
        assert found_service_links[1].get("href") == "/services/147ad62a-2951-4fa1-9ca0-093cd1a52c52"

        found_organisation_links = response.select(".govuk-tabs ul")[3].select("a")
        assert found_organisation_links[0].text == "organisation one"
        assert found_organisation_links[0].get("href") == "/organisations/c011fa40-4cbe-4524-b415-dde2f421bd9c"

    @pytest.mark.parametrize(
        "api_response, expected_redirect",
        (
            ({"type": "organisation"}, "/organisations/abcdef12-3456-7890-abcd-ef1234567890"),
            ({"type": "service"}, "/services/abcdef12-3456-7890-abcd-ef1234567890"),
            (
                {"type": "notification", "context": {"service_id": "abc"}},
                "/services/abc/notification/abcdef12-3456-7890-abcd-ef1234567890",
            ),
            (
                {"type": "template", "context": {"service_id": "abc"}},
                "/services/abc/templates/abcdef12-3456-7890-abcd-ef1234567890",
            ),
            ({"type": "email_branding"}, "/email-branding/abcdef12-3456-7890-abcd-ef1234567890/edit"),
            ({"type": "letter_branding"}, "/letter-branding/abcdef12-3456-7890-abcd-ef1234567890/edit"),
            ({"type": "user"}, "/users/abcdef12-3456-7890-abcd-ef1234567890"),
            ({"type": "provider"}, "/provider/abcdef12-3456-7890-abcd-ef1234567890"),
            (
                {"type": "reply_to_email", "context": {"service_id": "abc"}},
                "/services/abc/service-settings/email-reply-to/abcdef12-3456-7890-abcd-ef1234567890/edit",
            ),
            (
                {"type": "job", "context": {"service_id": "abc"}},
                "/services/abc/jobs/abcdef12-3456-7890-abcd-ef1234567890",
            ),
            (
                {"type": "service_contact_list", "context": {"service_id": "abc"}},
                "/services/abc/contact-list/abcdef12-3456-7890-abcd-ef1234567890",
            ),
            (
                {"type": "service_data_retention", "context": {"service_id": "abc"}},
                "/services/abc/data-retention/abcdef12-3456-7890-abcd-ef1234567890/edit",
            ),
            (
                {"type": "service_sms_sender", "context": {"service_id": "abc"}},
                "/services/abc/service-settings/sms-sender/abcdef12-3456-7890-abcd-ef1234567890/edit",
            ),
            ({"type": "inbound_number"}, "/inbound-sms-admin"),
            ({"type": "api_key", "context": {"service_id": "abc"}}, "/services/abc/api/keys"),
            (
                {"type": "template_folder", "context": {"service_id": "abc"}},
                "/services/abc/templates/all/folders/abcdef12-3456-7890-abcd-ef1234567890",
            ),
            (
                {"type": "service_callback_api", "context": {"service_id": "abc"}},
                "/services/abc/api/callbacks",
            ),
            ({"type": "complaint"}, "/platform-admin/complaints"),
            (
                {"type": "inbound_sms", "context": {"service_id": "abc"}},
                "/services/abc/conversation/abcdef12-3456-7890-abcd-ef1234567890#nabcdef12-3456-7890-abcd-ef1234567890",
            ),
        ),
    )
    def test_find_uuid_redirects(self, client_request, platform_admin_user, api_response, expected_redirect, mocker):
        mocker.patch(
            "app.main.views_nl.platform_admin.user_api_client.find_users_by_full_or_partial_email",
            return_value={"data": []},
        )
        mocker.patch(
            "app.main.views_nl.platform_admin.service_api_client.find_services_by_name", return_value={"data": []}
        )
        mocker.patch(
            "app.main.views_nl.platform_admin.organisations_client.search",
            return_value={"data": []},
        )
        mocker.patch("app.main.views_nl.platform_admin.admin_api_client.find_by_uuid", return_value=api_response)
        client_request.login(platform_admin_user)
        client_request.post(
            ".platform_admin_search",
            _data={"search": "abcdef12-3456-7890-abcd-ef1234567890"},
            _expected_redirect=expected_redirect,
        )

    def test_error_summary(self, client_request, platform_admin_user, mocker):
        client_request.login(platform_admin_user)

        page = client_request.post(".platform_admin_search", _data={"search": ""}, _expected_status=200)

        assert page.select_one(".govuk-error-summary a")["href"] == "#search"


def test_build_live_service_permissions_for_users_list_csv():
    services = [{"id": "1", "name": "Service 1"}, {"id": "2", "name": "Service 2"}, {"id": "3", "name": "Service 3"}]

    permissions = {
        "1": ["manage_users", "manage_settings"],  # equivalent to ui manage_service
        "2": ["send_texts", "send_emails", "send_letters"],  # equivalent to ui send_messages
        "3": ["manage_templates"],
    }

    filtered_permissions = {"manage_service", "send_messages"}

    result = build_live_service_permissions_for_users_list(services, permissions, filtered_permissions)

    assert result == "Service 1: manage_service; Service 2: send_messages"


def test_platform_admin_users_list_without_any_filters(client_request, platform_admin_user, mocker):
    client_request.login(platform_admin_user)

    page = client_request.post(
        "main.platform_admin_users_list",
        _expected_status=200,
        _data={},
    )

    assert "You must provide at least one filter option" in page.select_one(".govuk-error-summary__list").text


def test_platform_admin_users_list_when_no_results_for_filters(client_request, platform_admin_user, mocker):
    client_request.login(platform_admin_user)

    mocker.patch("app.main.views_nl.platform_admin.admin_api_client.fetch_users_list", return_value={"data": []})

    page = client_request.post(
        "main.platform_admin_users_list", _expected_status=200, _data={"created_to_date": "2024-01-01"}
    )

    error = page.select_one(".banner-dangerous")
    assert normalize_spaces(error.text) == "No results for filters selected"


def test_platform_admin_users_list_csv_export(client_request, platform_admin_user, mocker):
    client_request.login(platform_admin_user)

    first_user = create_user(
        name="User 1",
        email_address="user1@example.com",
        created_at="2024-01-01T12:00:00.000Z",
        take_part_in_research=True,
        services=[{"id": "1", "name": "Service A"}],
        permissions={"1": ["manage_users", "manage_settings"]},
    )
    second_user = create_user(
        name="User 2",
        email_address="user2@example.com",
        created_at="2024-01-02T12:00:00.000Z",
        take_part_in_research=False,
    )

    mocker.patch(
        "app.main.views_nl.platform_admin.admin_api_client.fetch_users_list",
        return_value={"data": [first_user, second_user]},
    )

    response = client_request.post_response(
        "main.platform_admin_users_list",
        _data={"created_from_date": "2024-01-01", "created_to_date": "2024-01-02"},
        _expected_status=200,
    )

    assert response.content_type == "text/csv; charset=utf-8"
    assert response.headers["Content-Disposition"].startswith('inline; filename="')

    csv_content = response.get_data(as_text=True)

    expected_csv = (
        "Name,Email,Created At,Research Opt In,Is Org Team Member,Number of Live Services,Live Service Permissions\r\n"
        "User 1,user1@example.com,01-01-2024,Yes,No,1,Service A: manage_service\r\n"
        "User 2,user2@example.com,02-01-2024,No,No,0,\r\n"
    )

    assert csv_content == expected_csv


def test_platform_admin_users_list_with_invalid_date_range(client_request, platform_admin_user, mocker):
    client_request.login(platform_admin_user)

    page = client_request.post(
        "main.platform_admin_users_list",
        _expected_status=200,
        _data={"created_from_date": "2024-01-10", "created_to_date": "2024-01-05"},
    )

    assert "Created (To)' date must be after 'Created (From)" in page.select_one(".govuk-error-message").text
