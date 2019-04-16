from unittest.mock import call

from app.notify_client.letter_branding_client import LetterBrandingClient


def test_get_letter_branding(mocker, fake_uuid):
    mock_get = mocker.patch(
        'app.notify_client.letter_branding_client.LetterBrandingClient.get',
        return_value={'foo': 'bar'}
    )
    mock_redis_get = mocker.patch('app.extensions.RedisClient.get', return_value=None)
    mock_redis_set = mocker.patch('app.extensions.RedisClient.set')

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
    mock_redis_get = mocker.patch('app.extensions.RedisClient.get', return_value=None)
    mock_redis_set = mocker.patch('app.extensions.RedisClient.set')

    LetterBrandingClient().get_all_letter_branding()

    mock_get.assert_called_once_with(url='/letter-branding')
    mock_redis_get.assert_called_once_with('letter_branding')
    mock_redis_set.assert_called_once_with(
        'letter_branding',
        '[1, 2, 3]',
        ex=604800,
    )


def test_create_letter_branding(mocker):
    new_branding = {'filename': 'uuid-test', 'name': 'my letters'}

    mock_post = mocker.patch('app.notify_client.letter_branding_client.LetterBrandingClient.post')
    mock_redis_delete = mocker.patch('app.extensions.RedisClient.delete')

    LetterBrandingClient().create_letter_branding(
        filename=new_branding['filename'], name=new_branding['name'],
    )
    mock_post.assert_called_once_with(
        url='/letter-branding',
        data=new_branding
    )

    mock_redis_delete.assert_called_once_with('letter_branding')


def test_update_letter_branding(mocker, fake_uuid):
    branding = {'filename': 'uuid-test', 'name': 'my letters'}

    mock_post = mocker.patch('app.notify_client.letter_branding_client.LetterBrandingClient.post')
    mock_redis_delete = mocker.patch('app.extensions.RedisClient.delete')
    LetterBrandingClient().update_letter_branding(
        branding_id=fake_uuid, filename=branding['filename'], name=branding['name'])

    mock_post.assert_called_once_with(
        url='/letter-branding/{}'.format(fake_uuid),
        data=branding
    )
    assert mock_redis_delete.call_args_list == [
        call('letter_branding'),
        call('letter_branding-{}'.format(fake_uuid)),
    ]
