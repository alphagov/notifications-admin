from functools import partial
from io import BytesIO

import pytest
from flask import url_for

from tests.conftest import mock_get_organisation_by_domain


class _MockS3Object():

    def __init__(self, data=None):
        self.data = data or b''

    def get(self):
        return {'Body': BytesIO(self.data)}


@pytest.mark.parametrize('agreement_signed, crown, expected_links', [
    (
        True, True,
        [
            partial(url_for, 'main.download_agreement'),
        ]
    ),
    (
        False, False,
        [
            partial(url_for, 'main.download_agreement'),
            lambda: 'mailto:notify-support@digital.cabinet-office.gov.uk',
        ]
    ),
    (
        None, None,
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
    agreement_signed,
    crown,
    expected_links,
):
    mock_get_organisation_by_domain(
        mocker,
        crown=crown,
        agreement_signed=agreement_signed,
    )
    page = client_request.get('main.agreement')
    links = page.select('main .column-two-thirds a')
    assert len(links) == len(expected_links)
    for index, link in enumerate(links):
        assert link['href'] == expected_links[index]()


@pytest.mark.parametrize('crown, expected_file_fetched, expected_file_served', [
    (
        True,
        'crown.pdf',
        'GOV.UK Notify data sharing and financial agreement.pdf',
    ),
    (
        False,
        'non-crown.pdf',
        'GOV.UK Notify data sharing and financial agreement (non-crown).pdf',
    ),
])
def test_downloading_agreement(
    logged_in_client,
    mocker,
    fake_uuid,
    crown,
    expected_file_fetched,
    expected_file_served,
):
    mock_get_s3_object = mocker.patch(
        'app.s3_client.s3_mou_client.get_s3_object',
        return_value=_MockS3Object(b'foo')
    )
    mock_get_organisation_by_domain(
        mocker,
        crown=crown,
    )
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
        'app.s3_client.s3_mou_client.get_s3_object',
        return_value=_MockS3Object()
    )
    mock_get_organisation_by_domain(
        mocker,
        crown=None,
    )
    response = logged_in_client.get(url_for('main.download_agreement'))
    assert response.status_code == 404
    assert mock_get_s3_object.call_args_list == []


def test_agreement_requires_login(
    client,
    mocker,
):
    mock_get_s3_object = mocker.patch(
        'app.s3_client.s3_mou_client.get_s3_object',
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
        'app.s3_client.s3_mou_client.get_s3_object',
        return_value=_MockS3Object()
    )
    response = client.get(url_for(
        endpoint,
        variant=variant,
    ))
    assert response.status_code == expected_status
