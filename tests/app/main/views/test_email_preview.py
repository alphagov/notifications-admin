import pytest
from flask import url_for


@pytest.mark.parametrize(
    "query_args, result", [
        ({}, True),
        ({'govuk_banner': 'false'}, 'false')
    ]
)
def test_renders(client, mocker, query_args, result):

    mock_convert_to_boolean = mocker.patch('app.main.views.index.convert_to_boolean')
    mocker.patch('app.main.views.index.HTMLEmailTemplate.__str__', return_value='rendered')

    response = client.get(url_for('main.email_template', **query_args))

    assert response.status_code == 200
    assert response.get_data(as_text=True) == 'rendered'
    mock_convert_to_boolean.assert_called_once_with(result)
