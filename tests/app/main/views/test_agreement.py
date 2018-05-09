from functools import partial
from io import BytesIO

import pytest
from flask import url_for

from tests.conftest import active_user_with_permissions


class _MockS3Object():

    def __init__(self, data=None):
        self.data = data or b''

    def get(self):
        return {'Body': BytesIO(self.data)}


@pytest.mark.parametrize('email_address, expected_links', [
    (
        'test@cabinet-office.gov.uk',
        [
            partial(url_for, 'main.download_agreement'),
        ]
    ),
    (
        'test@aylesburytowncouncil.gov.uk',
        [
            partial(url_for, 'main.download_agreement'),
            lambda: 'mailto:notify-support@digital.cabinet-office.gov.uk',
        ]
    ),
    (
        'test@unknown.gov.uk',
        [
            partial(url_for, 'main.public_download_agreement', variant='crown'),
            partial(url_for, 'main.public_download_agreement', variant='non-crown'),
            partial(url_for, 'main.support'),
            lambda: 'mailto:notify-support@digital.cabinet-office.gov.uk',
        ]
    ),
])
def test_show_agreement_page(
    client_request,
    mocker,
    fake_uuid,
    email_address,
    expected_links,
):
    user = active_user_with_permissions(fake_uuid)
    user.email_address = email_address
    mocker.patch('app.user_api_client.get_user', return_value=user)
    page = client_request.get('main.agreement')
    links = page.select('main .column-two-thirds a')
    assert len(links) == len(expected_links)
    for index, link in enumerate(links):
        assert link['href'] == expected_links[index]()


@pytest.mark.parametrize('email_address, expected_file_fetched, expected_file_served', [
    (
        'test@cabinet-office.gov.uk',
        'crown.pdf',
        'GOV.UK Notify data sharing and financial agreement.pdf',
    ),
    (
        'test@aylesburytowncouncil.gov.uk',
        'non-crown.pdf',
        'GOV.UK Notify data sharing and financial agreement (non-crown).pdf',
    ),
])
def test_downloading_agreement(
    logged_in_client,
    mocker,
    fake_uuid,
    email_address,
    expected_file_fetched,
    expected_file_served,
):
    mock_get_s3_object = mocker.patch(
        'app.main.s3_client.get_s3_object',
        return_value=_MockS3Object(b'foo')
    )
    user = active_user_with_permissions(fake_uuid)
    user.email_address = email_address
    mocker.patch('app.user_api_client.get_user', return_value=user)
    response = logged_in_client.get(url_for('main.download_agreement'))
    assert response.status_code == 200
    assert response.get_data() == b'foo'
    assert response.headers['Content-Type'] == 'application/pdf'
    assert response.headers['Content-Disposition'] == (
        'attachment; filename="{}"'.format(expected_file_served)
    )
    mock_get_s3_object.assert_called_once_with('test-mou', expected_file_fetched)


def test_agreement_cant_be_downloaded_unknown_crown_status(
    logged_in_client,
    mocker,
    fake_uuid,
):
    mock_get_s3_object = mocker.patch(
        'app.main.s3_client.get_s3_object',
        return_value=_MockS3Object()
    )
    user = active_user_with_permissions(fake_uuid)
    user.email_address = 'test@unknown.gov.uk'
    mocker.patch('app.user_api_client.get_user', return_value=user)
    response = logged_in_client.get(url_for('main.download_agreement'))
    assert response.status_code == 404
    assert mock_get_s3_object.call_args_list == []


def test_agreement_requires_login(
    client,
    mocker,
):
    mock_get_s3_object = mocker.patch(
        'app.main.s3_client.get_s3_object',
        return_value=_MockS3Object()
    )
    response = client.get(url_for('main.download_agreement'))
    assert response.status_code == 302
    assert response.location == 'http://localhost/sign-in?next=%2Fagreement.pdf'
    assert mock_get_s3_object.call_args_list == []


@pytest.mark.parametrize('endpoint', (
    'main.public_agreement',
    'main.public_download_agreement',
))
@pytest.mark.parametrize('variant, expected_status', (
    ('crown', 200),
    ('non-crown', 200),
    ('foo', 404),
))
def test_show_public_agreement_page(
    client,
    mocker,
    endpoint,
    variant,
    expected_status,
):
    mocker.patch(
        'app.main.s3_client.get_s3_object',
        return_value=_MockS3Object()
    )
    response = client.get(url_for(
        endpoint,
        variant=variant,
    ))
    assert response.status_code == expected_status
