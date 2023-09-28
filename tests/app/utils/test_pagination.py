import pytest

from app.utils.pagination import generate_next_dict, generate_optional_previous_and_next_dicts, generate_previous_dict


def test_generate_previous_dict(client_request):
    result = generate_previous_dict("main.view_jobs", "foo", 2, {})
    assert "page=1" in result["url"]
    assert result["title"] == "Previous page"
    assert result["label"] == "page 1"


def test_generate_next_dict(client_request):
    result = generate_next_dict("main.view_jobs", "foo", 2, {})
    assert "page=3" in result["url"]
    assert result["title"] == "Next page"
    assert result["label"] == "page 3"


def test_generate_previous_next_dict_adds_other_url_args(client_request):
    result = generate_next_dict("main.view_notifications", "foo", 2, {"message_type": "blah"})
    assert "notifications/blah" in result["url"]


@pytest.mark.parametrize(
    "page, num_pages, expect_previous_page, expect_next_page",
    (
        (1, 1, None, None),
        (1, 2, None, {"url": "/services/s/templates/t/versions?page=2", "title": "Next page", "label": "page 2"}),
        (2, 2, {"url": "/services/s/templates/t/versions?page=1", "title": "Previous page", "label": "page 1"}, None),
        (
            2,
            3,
            {"url": "/services/s/templates/t/versions?page=1", "title": "Previous page", "label": "page 1"},
            {"url": "/services/s/templates/t/versions?page=3", "title": "Next page", "label": "page 3"},
        ),
    ),
)
def test_generate_optional_previous_and_next_dicts(
    client_request, page, num_pages, expect_previous_page, expect_next_page
):
    previous_page, next_page = generate_optional_previous_and_next_dicts(
        "main.view_template_versions", service_id="s", page=page, num_pages=num_pages, url_args={"template_id": "t"}
    )
    assert previous_page == expect_previous_page
    assert next_page == expect_next_page
