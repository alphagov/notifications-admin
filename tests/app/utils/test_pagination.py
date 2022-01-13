from app.utils.pagination import generate_next_dict, generate_previous_dict


def test_generate_previous_dict(client_request):
    result = generate_previous_dict('main.view_jobs', 'foo', 2, {})
    assert 'page=1' in result['url']
    assert result['title'] == 'Previous page'
    assert result['label'] == 'page 1'


def test_generate_next_dict(client_request):
    result = generate_next_dict('main.view_jobs', 'foo', 2, {})
    assert 'page=3' in result['url']
    assert result['title'] == 'Next page'
    assert result['label'] == 'page 3'


def test_generate_previous_next_dict_adds_other_url_args(client_request):
    result = generate_next_dict('main.view_notifications', 'foo', 2, {'message_type': 'blah'})
    assert 'notifications/blah' in result['url']
