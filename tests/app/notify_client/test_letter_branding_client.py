from app.notify_client.letter_branding_client import LetterBrandingClient


def test_get_letter_branding(mocker):
    mock_get = mocker.patch('app.notify_client.letter_branding_client.LetterBrandingClient.get')
    LetterBrandingClient().get_letter_branding()
    mock_get.assert_called_once_with(
        url='/dvla_organisations'
    )


def test_create_letter_branding(mocker):
    new_branding = {'filename': 'uuid-test', 'name': 'my letters', 'domain': 'example.com'}

    mock_post = mocker.patch('app.notify_client.letter_branding_client.LetterBrandingClient.post')

    LetterBrandingClient().create_letter_branding(
        filename=new_branding['filename'], name=new_branding['name'], domain=new_branding['domain']
    )
    mock_post.assert_called_once_with(
        url='/letter-branding',
        data=new_branding
    )
