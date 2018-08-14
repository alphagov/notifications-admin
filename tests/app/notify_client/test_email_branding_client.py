from app.notify_client.email_branding_client import EmailBrandingClient


def test_get_email_branding(mocker, fake_uuid):
    mock_get = mocker.patch('app.notify_client.email_branding_client.EmailBrandingClient.get')
    EmailBrandingClient().get_email_branding(fake_uuid)
    mock_get.assert_called_once_with(
        url='/email-branding/{}'.format(fake_uuid)
    )


def test_get_all_email_branding(mocker):
    mock_get = mocker.patch('app.notify_client.email_branding_client.EmailBrandingClient.get')
    EmailBrandingClient().get_all_email_branding()
    mock_get.assert_called_once_with(
        url='/email-branding'
    )


def test_get_letter_email_branding(mocker):
    mock_get = mocker.patch('app.notify_client.email_branding_client.EmailBrandingClient.get')
    EmailBrandingClient().get_letter_email_branding()
    mock_get.assert_called_once_with(
        url='/dvla_organisations'
    )


def test_create_email_branding(mocker):
    org_data = {'logo': 'test.png', 'name': 'test name', 'text': 'test name', 'colour': 'red'}

    mock_post = mocker.patch('app.notify_client.email_branding_client.EmailBrandingClient.post')
    EmailBrandingClient().create_email_branding(
        logo=org_data['logo'], name=org_data['name'], text=org_data['text'], colour=org_data['colour'])

    mock_post.assert_called_once_with(
        url='/email-branding',
        data=org_data
    )


def test_update_email_branding(mocker, fake_uuid):
    org_data = {'logo': 'test.png', 'name': 'test name', 'text': 'test name', 'colour': 'red'}

    mock_post = mocker.patch('app.notify_client.email_branding_client.EmailBrandingClient.post')
    EmailBrandingClient().update_email_branding(
        branding_id=fake_uuid, logo=org_data['logo'], name=org_data['name'], text=org_data['text'],
        colour=org_data['colour'])

    mock_post.assert_called_once_with(
        url='/email-branding/{}'.format(fake_uuid),
        data=org_data
    )
