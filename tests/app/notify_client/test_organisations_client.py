from app.notify_client.organisations_client import OrganisationsClient


def test_get_organisation(mocker, fake_uuid):
    mock_get = mocker.patch('app.notify_client.organisations_client.OrganisationsClient.get')
    OrganisationsClient().get_organisation(fake_uuid)
    mock_get.assert_called_once_with(
        url='/organisation/{}'.format(fake_uuid)
    )


def test_get_organisations(mocker):
    mock_get = mocker.patch('app.notify_client.organisations_client.OrganisationsClient.get')
    OrganisationsClient().get_organisations()
    mock_get.assert_called_once_with(
        url='/organisation'
    )


def test_get_letter_organisations(mocker):
    mock_get = mocker.patch('app.notify_client.organisations_client.OrganisationsClient.get')
    OrganisationsClient().get_letter_organisations()
    mock_get.assert_called_once_with(
        url='/dvla_organisations'
    )


def test_create_organisations(mocker):
    org_data = {'logo': 'test.png', 'name': 'test name', 'colour': 'red'}

    mock_post = mocker.patch('app.notify_client.organisations_client.OrganisationsClient.post')
    OrganisationsClient().create_organisation(logo=org_data['logo'], name=org_data['name'], colour=org_data['colour'])

    mock_post.assert_called_once_with(
        url='/organisation',
        data=org_data
    )


def test_update_organisations(mocker, fake_uuid):
    org_data = {'logo': 'test.png', 'name': 'test name', 'colour': 'red'}

    mock_post = mocker.patch('app.notify_client.organisations_client.OrganisationsClient.post')
    OrganisationsClient().update_organisation(
        org_id=fake_uuid, logo=org_data['logo'], name=org_data['name'], colour=org_data['colour'])

    mock_post.assert_called_once_with(
        url='/organisation/{}'.format(fake_uuid),
        data=org_data
    )
