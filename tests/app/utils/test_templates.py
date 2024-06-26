from unittest import mock

import pytest
from bs4 import BeautifulSoup
from freezegun import freeze_time
from markupsafe import Markup
from notifications_utils.template import SubjectMixin, Template
from ordered_set import OrderedSet

from app import load_service_before_request
from app.utils.templates import TemplatedLetterImageTemplate, get_sample_template
from tests import template_json
from tests.conftest import SERVICE_ONE_ID, do_mock_get_page_counts_for_letter


@pytest.fixture(scope="function", autouse=True)
def app_context(notify_admin, fake_uuid, mock_get_service, mock_get_page_counts_for_letter):
    with notify_admin.test_request_context(f"/services/{SERVICE_ONE_ID}/templates/{fake_uuid}"):
        load_service_before_request()
        yield notify_admin


@pytest.mark.parametrize("template_type", ["sms", "letter", "email"])
def test_get_sample_template_returns_template(template_type):
    template = get_sample_template(template_type)
    assert isinstance(template, Template)


def test_get_page_counts_for_letter_caches(
    client_request,
    service_one,
    api_user_active,
    mocker,
    fake_uuid,
):
    client_request.login(api_user_active, service_one)

    mock_redis_get = mocker.patch(
        "app.extensions.RedisClient.get",
        return_value=None,
    )
    mock_redis_set = mocker.patch(
        "app.extensions.RedisClient.set",
    )
    mock_get_page_count = do_mock_get_page_counts_for_letter(mocker, count=5)

    template = TemplatedLetterImageTemplate(
        template_json(
            service_id=SERVICE_ONE_ID,
            id_=fake_uuid,
            type_="letter",
        )
    )

    for _ in range(3):
        assert template.page_count == 5

    # Redis and template preview only get called once each because the instance also caches the value
    mock_redis_get.assert_called_once_with(f"service-{SERVICE_ONE_ID}-template-{fake_uuid}-version-1-all-page-counts")
    mock_redis_set.assert_called_once_with(
        f"service-{SERVICE_ONE_ID}-template-{fake_uuid}-version-1-all-page-counts",
        '{"count": 5, "welsh_page_count": 0, "attachment_page_count": 0}',
        ex=2_419_200,
    )
    assert len(mock_get_page_count.call_args_list) == 1


def test_get_page_counts_for_letter_returns_cached_value(
    client_request,
    service_one,
    api_user_active,
    mocker,
    fake_uuid,
):
    client_request.login(api_user_active, service_one)

    mock_redis_get = mocker.patch(
        "app.extensions.RedisClient.get",
        return_value=b'{"count": 5, "welsh_page_count": 0, "attachment_page_count": 0}',
    )

    template = TemplatedLetterImageTemplate(
        template_json(
            service_id=SERVICE_ONE_ID,
            id_=fake_uuid,
            type_="letter",
        )
    )

    for _ in range(3):
        assert template.page_count == 5

    # Redis only gets called once because the instance also caches the value
    mock_redis_get.assert_called_once_with(f"service-{SERVICE_ONE_ID}-template-{fake_uuid}-version-1-all-page-counts")


def test_get_page_counts_for_letter_does_not_cache_for_personalised_letters(
    client_request,
    service_one,
    api_user_active,
    mocker,
    fake_uuid,
):
    client_request.login(api_user_active, service_one)

    mock_get_page_count = do_mock_get_page_counts_for_letter(mocker, count=5)

    template = TemplatedLetterImageTemplate(
        template_json(
            service_id=SERVICE_ONE_ID,
            id_=fake_uuid,
            type_="letter",
        )
    )

    for _ in range(3):
        # We’re changing the values so the page count might change
        template.values = {"foo": "bar"}
        assert template.page_count == 5

    # No calls to Redis here
    assert len(mock_get_page_count.call_args_list) == 3


@freeze_time("2012-12-12 12:12:12")
@pytest.mark.parametrize(
    "postage_argument",
    (
        None,
        "first",
        "second",
        "europe",
        "rest-of-world",
    ),
)
def test_letter_image_renderer_shows_international_post(
    mocker,
    postage_argument,
):
    mock_render = mocker.patch("app.utils.templates.render_template")
    str(
        TemplatedLetterImageTemplate(
            {
                "service": SERVICE_ONE_ID,
                "content": "Content",
                "subject": "Subject",
                "template_type": "letter",
                "postage": postage_argument,
            },
            {
                "address line 1": "123 Example Street",
                "address line 2": "Lima",
                "address line 3": "Peru",
            },
            image_url="http://example.com/endpoint.png",
        )
    )
    assert mock_render.call_args_list[0][1]["postage_description"] == "international"


def test_letter_image_template_renders_visually_hidden_address():
    template = BeautifulSoup(
        str(
            TemplatedLetterImageTemplate(
                {"content": "", "subject": "", "template_type": "letter"},
                {
                    "address_line_1": "line 1",
                    "address_line_2": "line 2",
                    "postcode": "postcode",
                },
                image_url="http://example.com/endpoint.png",
            )
        ),
        features="html.parser",
    )
    assert str(template.select_one(".govuk-visually-hidden ul")) == (
        "<ul><li>line 1</li><li>line 2</li><li>postcode</li></ul>"
    )


@pytest.mark.parametrize(
    "page_image_url",
    [
        pytest.param("http://example.com/endpoint.png?page=0", marks=pytest.mark.xfail),
        "http://example.com/endpoint.png?page=1",
        "http://example.com/endpoint.png?page=2",
        "http://example.com/endpoint.png?page=3",
        pytest.param("http://example.com/endpoint.png?page=4", marks=pytest.mark.xfail),
    ],
)
def test_letter_image_renderer_pagination(mocker, page_image_url):
    do_mock_get_page_counts_for_letter(mocker, count=3)
    assert page_image_url in str(
        TemplatedLetterImageTemplate(
            {"service": SERVICE_ONE_ID, "content": "", "subject": "", "template_type": "letter"},
            image_url="http://example.com/endpoint.png",
        )
    )


# FIXME: current_service required
# @pytest.mark.parametrize(
#     "kwargs, expected_exception, expected_exception_value",
#     (
#         (
#             {"image_url": "foo"},
#             TypeError,
#             "page_count is required to render TemplatedLetterImageTemplate",
#         ),
#         (
#             {"image_url": "foo", "page_count": "foo"},
#             TypeError,
#             "'<' not supported between instances of 'int' and 'str'",
#         ),
#     ),
# )
# def test_letter_image_renderer_requires_page_count_to_render(
#     mocker, kwargs, service_one, expected_exception, expected_exception_value
# ):
#     template = TemplatedLetterImageTemplate(
#         {"service": SERVICE_ONE_ID, "content": "", "subject": "", "template_type": "letter"}, **kwargs
#     )
#     with pytest.raises(expected_exception) as exception:
#         str(template)
#     assert str(exception.value) == expected_exception_value


def test_letter_image_renderer_requires_valid_postage():
    with pytest.raises(TypeError) as exception:
        TemplatedLetterImageTemplate(
            {"service": SERVICE_ONE_ID, "content": "", "subject": "", "template_type": "letter", "postage": "third"},
            image_url="foo",
        )
    assert str(exception.value) == ("postage must be None, 'first', 'second', 'europe' or 'rest-of-world'")


@pytest.mark.parametrize(
    "initial_postage_value",
    (
        {},
        {"postage": None},
        {"postage": "first"},
        {"postage": "second"},
        {"postage": "europe"},
        {"postage": "rest-of-world"},
    ),
)
@pytest.mark.parametrize(
    "postage_value",
    (
        None,
        "first",
        "second",
        "europe",
        "rest-of-world",
        pytest.param("other", marks=pytest.mark.xfail(raises=TypeError)),
    ),
)
def test_letter_image_renderer_postage_can_be_overridden(initial_postage_value, postage_value):
    template = TemplatedLetterImageTemplate(
        {"service": SERVICE_ONE_ID, "content": "", "subject": "", "template_type": "letter"} | initial_postage_value
    )
    assert template.postage == initial_postage_value.get("postage")

    template.postage = postage_value
    assert template.postage == postage_value


def test_letter_image_renderer_requires_image_url_to_render():
    template = TemplatedLetterImageTemplate(
        {"service": SERVICE_ONE_ID, "content": "", "subject": "", "template_type": "letter"},
    )
    with pytest.raises(TypeError) as exception:
        str(template)
    assert str(exception.value) == "image_url is required to render TemplatedLetterImageTemplate"


@pytest.mark.parametrize(
    "postage, expected_attribute_value, expected_postage_text",
    (
        (None, None, None),
        (
            "first",
            ["letter-postage", "letter-postage-first"],
            "Postage: first class",
        ),
        (
            "second",
            ["letter-postage", "letter-postage-second"],
            "Postage: second class",
        ),
        (
            "europe",
            ["letter-postage", "letter-postage-international"],
            "Postage: international",
        ),
        (
            "rest-of-world",
            ["letter-postage", "letter-postage-international"],
            "Postage: international",
        ),
    ),
)
def test_letter_image_renderer_passes_postage_to_html_attribute(
    postage,
    expected_attribute_value,
    expected_postage_text,
):
    template = BeautifulSoup(
        str(
            TemplatedLetterImageTemplate(
                {
                    "service": SERVICE_ONE_ID,
                    "content": "",
                    "subject": "",
                    "template_type": "letter",
                    "postage": postage,
                },
                image_url="foo",
            )
        ),
        features="html.parser",
    )
    if expected_attribute_value:
        assert template.select_one(".letter-postage")["class"] == expected_attribute_value
        assert template.select_one(".letter-postage").text.strip() == expected_postage_text
    else:
        assert not template.select(".letter-postage")


@freeze_time("2012-12-12 12:12:12")
# @mock.patch("app.utils.templates.TemplatedLetterImageTemplate.jinja_template.render")
@pytest.mark.parametrize(
    "page_count, expected_oversized, expected_page_numbers",
    [
        (
            1,
            False,
            [1],
        ),
        (
            5,
            False,
            [1, 2, 3, 4, 5],
        ),
        (
            10,
            False,
            [1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
        ),
        (
            11,
            True,
            [1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
        ),
        (
            99,
            True,
            [1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
        ),
    ],
)
@pytest.mark.parametrize(
    "postage_args, expected_show_postage, expected_postage_class_value, expected_postage_description",
    (
        pytest.param({}, False, None, None),
        pytest.param({"postage": None}, False, None, None),
        pytest.param({"postage": "first"}, True, "letter-postage-first", "first class"),
        pytest.param({"postage": "second"}, True, "letter-postage-second", "second class"),
        pytest.param({"postage": "europe"}, True, "letter-postage-international", "international"),
        pytest.param({"postage": "rest-of-world"}, True, "letter-postage-international", "international"),
        pytest.param(
            {"postage": "third"},
            True,
            "letter-postage-third",
            "third class",
            marks=pytest.mark.xfail(raises=TypeError),
        ),
    ),
)
def test_letter_image_renderer(
    mocker,
    page_count,
    expected_page_numbers,
    expected_oversized,
    postage_args,
    expected_show_postage,
    expected_postage_class_value,
    expected_postage_description,
):
    do_mock_get_page_counts_for_letter(mocker, count=page_count)
    mock_render = mocker.patch("app.utils.templates.render_template")
    str(
        TemplatedLetterImageTemplate(
            {"service": SERVICE_ONE_ID, "content": "Content", "subject": "Subject", "template_type": "letter"}
            | postage_args,
            image_url="http://example.com/endpoint.png",
            contact_block="10 Downing Street",
        )
    )
    assert mock_render.call_args_list == [
        mocker.call(
            mocker.ANY,
            image_url="http://example.com/endpoint.png",
            page_numbers=expected_page_numbers,
            first_page_of_attachment=None,
            first_page_of_english=1,
            address=[
                Markup("<span class='placeholder-no-brackets'>address line 1</span>"),
                Markup("<span class='placeholder-no-brackets'>address line 2</span>"),
                Markup("<span class='placeholder-no-brackets'>address line 3</span>"),
                Markup("<span class='placeholder-no-brackets'>address line 4</span>"),
                Markup("<span class='placeholder-no-brackets'>address line 5</span>"),
                Markup("<span class='placeholder-no-brackets'>address line 6</span>"),
                Markup("<span class='placeholder-no-brackets'>address line 7</span>"),
            ],
            contact_block="10 Downing Street",
            date="12 December 2012",
            subject="Subject",
            message="<p>Content</p>",
            show_postage=expected_show_postage,
            postage_class_value=expected_postage_class_value,
            postage_description=expected_postage_description,
            template=mocker.ANY,
        )
    ]


@pytest.mark.parametrize(
    "page_count, expected_classes",
    (
        (
            1,
            [
                ["letter", "page--odd", "page--first", "page--last"],
            ],
        ),
        (
            2,
            [
                ["letter", "page--odd", "page--first"],
                ["letter", "page--even", "page--last"],
            ],
        ),
        (
            5,
            [
                ["letter", "page--odd", "page--first"],
                ["letter", "page--even"],
                ["letter", "page--odd"],
                ["letter", "page--even"],
                ["letter", "page--odd", "page--last"],
            ],
        ),
    ),
)
def test_letter_image_renderer_adds_classes_to_pages(
    mocker,
    page_count,
    expected_classes,
):
    do_mock_get_page_counts_for_letter(mocker, count=page_count)
    template = BeautifulSoup(
        str(
            TemplatedLetterImageTemplate(
                {"service": SERVICE_ONE_ID, "content": "Content", "subject": "Subject", "template_type": "letter"},
                image_url="http://example.com/endpoint.png",
            )
        ),
        features="html.parser",
    )
    assert [page["class"] for page in template.select(".letter")] == expected_classes


@pytest.mark.parametrize(
    "page_count, expected_too_many_pages",
    (
        (1, False),
        (10, False),
        (11, True),
        (99, True),
    ),
)
def test_letter_image_renderer_knows_if_letter_is_too_long(
    mocker,
    page_count,
    expected_too_many_pages,
):
    do_mock_get_page_counts_for_letter(mocker, count=page_count)
    template = TemplatedLetterImageTemplate(
        {"service": SERVICE_ONE_ID, "content": "Content", "subject": "Subject", "template_type": "letter"},
    )
    assert template.too_many_pages is expected_too_many_pages
    assert template.max_page_count == 10
    assert template.max_sheet_count == 5


def test_subject_line_gets_applied_to_correct_template_types():
    assert issubclass(TemplatedLetterImageTemplate, SubjectMixin)


def test_subject_line_gets_replaced():
    template = TemplatedLetterImageTemplate(
        {"service": SERVICE_ONE_ID, "content": "", "template_type": "letter", "subject": "((name))"},
        image_url="http://example.com",
    )
    assert template.subject == Markup("<span class='placeholder'>&#40;&#40;name&#41;&#41;</span>")
    template.values = {"name": "Jo"}
    assert template.subject == "Jo"


@mock.patch("notifications_utils.template.Field.__init__", return_value=None)
@mock.patch("notifications_utils.template.Field.__str__", return_value="1\n2\n3\n4\n5\n6\n7\n8")
def test_templates_handle_html_and_redacting(
    mock_field_str,
    mock_field_init,
):
    assert str(
        TemplatedLetterImageTemplate(
            {"service": SERVICE_ONE_ID, "content": "content", "subject": "subject", "template_type": "letter"},
            image_url="http://example.com",
            contact_block="www.gov.uk",
        )
    )
    assert mock_field_init.call_args_list == [
        mock.call(
            (
                "((address line 1))\n"
                "((address line 2))\n"
                "((address line 3))\n"
                "((address line 4))\n"
                "((address line 5))\n"
                "((address line 6))\n"
                "((address line 7))"
            ),
            {},
            with_brackets=False,
            html="escape",
        ),
        mock.call("www.gov.uk", {}, html="escape", redact_missing_personalisation=False),
        mock.call("subject", {}, html="escape", redact_missing_personalisation=False),
        mock.call("content", {}, html="escape", markdown_lists=True, redact_missing_personalisation=False),
    ]


def test_templates_extract_placeholders():
    assert TemplatedLetterImageTemplate(
        {"service": SERVICE_ONE_ID, "content": "((content))", "subject": "((subject))", "template_type": "letter"},
        contact_block="((contact_block))",
        image_url="http://example.com",
    ).placeholders == OrderedSet(["contact_block", "subject", "content"])


def test_message_too_long_limit_bigger_or_nonexistent_for_non_sms_templates():
    body = "a" * 1000
    template = TemplatedLetterImageTemplate(
        {"service": SERVICE_ONE_ID, "content": body, "subject": "foo", "template_type": "letter"},
        image_url="foo",
    )
    assert template.is_message_too_long() is False


def test_letter_preview_template_lazy_loads_images(mocker):
    do_mock_get_page_counts_for_letter(mocker, count=3)
    page = BeautifulSoup(
        str(
            TemplatedLetterImageTemplate(
                {"service": SERVICE_ONE_ID, "content": "Content", "subject": "Subject", "template_type": "letter"},
                image_url="http://example.com/endpoint.png",
            )
        ),
        "html.parser",
    )
    assert [(img["src"], img["loading"]) for img in page.select("img")] == [
        ("http://example.com/endpoint.png?page=1", "eager"),
        ("http://example.com/endpoint.png?page=2", "lazy"),
        ("http://example.com/endpoint.png?page=3", "lazy"),
    ]


def test_letter_image_template_marks_first_page_of_attachment(mocker, fake_uuid):
    do_mock_get_page_counts_for_letter(mocker, count=8, attachment_page_count=3)

    template = BeautifulSoup(
        str(
            TemplatedLetterImageTemplate(
                {
                    "service": SERVICE_ONE_ID,
                    "content": "Content",
                    "subject": "Subject",
                    "template_type": "letter",
                    "letter_attachment": {"id": fake_uuid, "page_count": 3},
                },
                image_url="http://example.com/endpoint.png",
            )
        ),
        features="html.parser",
    )

    assert [str(element) for element in template.select(".letter *")] == [
        '<img alt="" loading="eager" src="http://example.com/endpoint.png?page=1"/>',
        '<img alt="" loading="lazy" src="http://example.com/endpoint.png?page=2"/>',
        '<img alt="" loading="lazy" src="http://example.com/endpoint.png?page=3"/>',
        '<img alt="" loading="lazy" src="http://example.com/endpoint.png?page=4"/>',
        '<img alt="" loading="lazy" src="http://example.com/endpoint.png?page=5"/>',
        '<div id="first-page-of-attachment"></div>',
        '<img alt="" loading="eager" src="http://example.com/endpoint.png?page=6"/>',
        '<img alt="" loading="lazy" src="http://example.com/endpoint.png?page=7"/>',
        '<img alt="" loading="lazy" src="http://example.com/endpoint.png?page=8"/>',
    ]


class TestTemplatedLetterImageTemplate:
    @pytest.mark.parametrize(
        "mocker_kwargs, expected_english_pages, expected_welsh_pages, expected_attachment_pages",
        (
            ({"count": 1}, 1, 0, 0),
            ({"count": 5}, 5, 0, 0),
            ({"count": 2, "welsh_page_count": 1}, 1, 1, 0),
            ({"count": 5, "welsh_page_count": 3}, 2, 3, 0),
            ({"count": 4, "attachment_page_count": 2}, 2, 0, 2),
            ({"count": 7, "welsh_page_count": 2, "attachment_page_count": 3}, 2, 2, 3),
        ),
    )
    def test_page_count_attributes(
        self,
        mocker,
        fake_uuid,
        mocker_kwargs,
        expected_english_pages,
        expected_welsh_pages,
        expected_attachment_pages,
    ):
        do_mock_get_page_counts_for_letter(mocker, **mocker_kwargs)
        t = TemplatedLetterImageTemplate(template_json(service_id=SERVICE_ONE_ID, id_=fake_uuid, type_="letter"))

        assert t.english_page_count == expected_english_pages
        assert t.welsh_page_count == expected_welsh_pages
        assert t.attachment_page_count == expected_attachment_pages

    @pytest.mark.parametrize(
        "mocker_kwargs, expected_value",
        (
            ({"count": 1}, 1),
            ({"count": 5}, 1),
            ({"count": 2, "welsh_page_count": 1}, 2),
            ({"count": 5, "welsh_page_count": 3}, 4),
            ({"count": 4, "attachment_page_count": 2}, 1),
            ({"count": 7, "welsh_page_count": 2, "attachment_page_count": 3}, 3),
        ),
    )
    def test_first_english_page(self, mocker, fake_uuid, mocker_kwargs, expected_value):
        do_mock_get_page_counts_for_letter(mocker, **mocker_kwargs)
        t = TemplatedLetterImageTemplate(template_json(service_id=SERVICE_ONE_ID, id_=fake_uuid, type_="letter"))

        assert t.first_english_page == expected_value

    @pytest.mark.parametrize(
        "mocker_kwargs, expected_value",
        (
            ({"count": 1}, None),
            ({"count": 5}, None),
            ({"count": 2, "welsh_page_count": 1}, None),
            ({"count": 5, "welsh_page_count": 3}, None),
            ({"count": 4, "attachment_page_count": 2}, 3),
            ({"count": 7, "welsh_page_count": 2, "attachment_page_count": 3}, 5),
        ),
    )
    def test_first_attachment_page(self, mocker, fake_uuid, mocker_kwargs, expected_value):
        do_mock_get_page_counts_for_letter(mocker, **mocker_kwargs)
        t = TemplatedLetterImageTemplate(
            template_json(
                service_id=SERVICE_ONE_ID,
                id_=fake_uuid,
                type_="letter",
                letter_attachment=(
                    {
                        "id": "abc",
                        "original_filename": "blah.pdf",
                        "page_count": mocker_kwargs["attachment_page_count"],
                    }
                    if expected_value
                    else {}
                ),
            ),
        )

        assert t.first_attachment_page == expected_value
