from app.notify_client.letter_branding_client import LetterBrandingClient


def test_get_letter_branding(mocker, fake_uuid):
    mock_get = mocker.patch(
        'app.notify_client.letter_branding_client.LetterBrandingClient.get',
        return_value={'foo': 'bar'}
    )
    mock_redis_get = mocker.patch('app.notify_client.RedisClient.get', return_value=None)
    mock_redis_set = mocker.patch('app.notify_client.RedisClient.set')

    LetterBrandingClient().get_letter_branding(fake_uuid)

    mock_get.assert_called_once_with(url='/letter-branding/{}'.format(fake_uuid))
    mock_redis_get.assert_called_once_with('letter_branding-{}'.format(fake_uuid))
    mock_redis_set.assert_called_once_with(
        'letter_branding-{}'.format(fake_uuid),
        '{"foo": "bar"}',
        ex=604800,
    )


def test_get_all_letter_branding(mocker):
    mock_get = mocker.patch('app.notify_client.letter_branding_client.LetterBrandingClient.get', return_value=[1, 2, 3])
    mock_redis_get = mocker.patch('app.notify_client.RedisClient.get', return_value=None)
    mock_redis_set = mocker.patch('app.notify_client.RedisClient.set')

    LetterBrandingClient().get_all_letter_branding()

    mock_get.assert_called_once_with(url='/letter-branding')
    mock_redis_get.assert_called_once_with('letter_branding')
    mock_redis_set.assert_called_once_with(
        'letter_branding',
        '[1, 2, 3]',
        ex=604800,
    )


def test_create_letter_branding(mocker):
    new_branding = {'filename': 'uuid-test', 'name': 'my letters', 'domain': 'example.com'}

    mock_post = mocker.patch('app.notify_client.letter_branding_client.LetterBrandingClient.post')
    mock_redis_delete = mocker.patch('app.notify_client.RedisClient.delete')

    LetterBrandingClient().create_letter_branding(
        filename=new_branding['filename'], name=new_branding['name'], domain=new_branding['domain']
    )
    mock_post.assert_called_once_with(
        url='/letter-branding',
        data=new_branding
    )

    mock_redis_delete.assert_called_once_with('letter_branding')
