from unittest.mock import Mock
from notifications_utils.template import LetterPreviewTemplate

from app.template_previews import TemplatePreview


def test_from_utils_template_calls_through(mocker, mock_get_service_letter_template):
    mock_from_db = mocker.patch('app.template_previews.TemplatePreview.from_database_object')
    template = LetterPreviewTemplate(mock_get_service_letter_template(None, None)['data'])

    ret = TemplatePreview.from_utils_template(template, 'foo')

    assert ret == mock_from_db.return_value
    mock_from_db.assert_called_once_with(template._template, 'foo', template.values)


def test_from_database_object_makes_request(mocker, client):
    resp = Mock(content='a', status_code='b', headers={'c': 'd'})
    request_mock = mocker.patch('app.template_previews.requests.post', return_value=resp)
    mocker.patch('app.template_previews.current_service', __getitem__=Mock(return_value='123'))

    ret = TemplatePreview.from_database_object(template='foo', filetype='bar')

    assert ret[0] == 'a'
    assert ret[1] == 'b'
    assert list(ret[2]) == [('c', 'd')]
    url = 'http://localhost:6013/preview.bar'
    data = {
        'letter_contact_block': '123',
        'template': 'foo',
        'values': None
    }
    headers = {'Authorization': 'Token my-secret-key'}

    request_mock.assert_called_once_with(url, json=data, headers=headers)
