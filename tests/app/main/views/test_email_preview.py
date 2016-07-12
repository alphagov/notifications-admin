import pytest
from flask import url_for


@pytest.mark.parametrize(
    "query_args, params", [
        ({}, {'govuk_banner': True}),
        ({'govuk_banner': 'false'}, {'govuk_banner': False})
    ]
)
def test_renders(app_, mocker, query_args, params):
    with app_.test_request_context(), app_.test_client() as client:

        mock_html_email = mocker.patch(
            'app.main.views.index.HTMLEmail',
            return_value=lambda x: 'rendered'
        )

        response = client.get(url_for('main.email_template', **query_args))

        assert response.status_code == 200
        assert response.get_data(as_text=True) == 'rendered'
        mock_html_email.assert_called_once_with(**params)
