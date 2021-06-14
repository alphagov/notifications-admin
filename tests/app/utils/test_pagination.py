from app.utils.pagination import generate_next_dict, generate_previous_dict


def test_generate_previous_dict(client):
    ret = generate_previous_dict('main.view_jobs', 'foo', 2, {})
    assert 'page=1' in ret['url']
    assert ret['title'] == 'Previous page'
    assert ret['label'] == 'page 1'


def test_generate_next_dict(client):
    ret = generate_next_dict('main.view_jobs', 'foo', 2, {})
    assert 'page=3' in ret['url']
    assert ret['title'] == 'Next page'
    assert ret['label'] == 'page 3'


def test_generate_previous_next_dict_adds_other_url_args(client):
    ret = generate_next_dict('main.view_notifications', 'foo', 2, {'message_type': 'blah'})
    assert 'notifications/blah' in ret['url']
