from collections import namedtuple
from unittest.mock import call

import pytest

from app.s3_client.s3_logo_client import (
    EMAIL_LOGO_LOCATION_STRUCTURE,
    LETTER_TEMP_LOGO_LOCATION,
    LETTER_TEMP_TAG,
    TEMP_TAG,
    delete_email_temp_file,
    delete_email_temp_files_created_by,
    delete_letter_temp_file,
    delete_letter_temp_files_created_by,
    letter_filename_for_db,
    permanent_email_logo_name,
    persist_logo,
    upload_email_logo,
    upload_letter_temp_logo,
)

bucket = 'test_bucket'
data = {'data': 'some_data'}
filename = 'test.png'
svg_filename = 'test.svg'
upload_id = 'test_uuid'
region = 'eu-west1'


@pytest.fixture
def upload_filename(fake_uuid):
    return EMAIL_LOGO_LOCATION_STRUCTURE.format(
        temp=TEMP_TAG.format(user_id=fake_uuid), unique_id=upload_id, filename=filename)


@pytest.fixture
def letter_upload_filename(fake_uuid):
    return LETTER_TEMP_LOGO_LOCATION.format(
        user_id=fake_uuid,
        unique_id=upload_id,
        filename=svg_filename
    )


def test_upload_email_logo_calls_correct_args(client_request, mocker, fake_uuid, upload_filename):
    mocker.patch('uuid.uuid4', return_value=upload_id)
    mocker.patch.dict('flask.current_app.config', {'LOGO_UPLOAD_BUCKET_NAME': bucket})
    mocked_s3_upload = mocker.patch('app.s3_client.s3_logo_client.utils_s3upload')

    upload_email_logo(filename=filename, user_id=fake_uuid, filedata=data, region=region)

    mocked_s3_upload.assert_called_once_with(
        filedata=data,
        region=region,
        file_location=upload_filename,
        bucket_name=bucket,
        content_type='image/png'
    )


def test_upload_letter_temp_logo_calls_correct_args(mocker, fake_uuid, letter_upload_filename):
    mocker.patch('uuid.uuid4', return_value=upload_id)
    mocker.patch.dict('flask.current_app.config', {'LOGO_UPLOAD_BUCKET_NAME': bucket})
    mocked_s3_upload = mocker.patch('app.s3_client.s3_logo_client.utils_s3upload')

    new_filename = upload_letter_temp_logo(filename=svg_filename, user_id=fake_uuid, filedata=data, region=region)

    mocked_s3_upload.assert_called_once_with(
        filedata=data,
        region=region,
        bucket_name=bucket,
        file_location=letter_upload_filename,
        content_type='image/svg+xml'
    )
    assert new_filename == 'letters/static/images/letter-template/temp-{}_test_uuid-test.svg'.format(fake_uuid)


def test_persist_logo(client_request, mocker, fake_uuid, upload_filename):
    mocker.patch.dict('flask.current_app.config', {'LOGO_UPLOAD_BUCKET_NAME': bucket})
    mocked_get_s3_object = mocker.patch('app.s3_client.s3_logo_client.get_s3_object')
    mocked_delete_s3_object = mocker.patch('app.s3_client.s3_logo_client.delete_s3_object')

    new_filename = permanent_email_logo_name(upload_filename, fake_uuid)

    persist_logo(upload_filename, new_filename)

    mocked_get_s3_object.assert_called_once_with(bucket, new_filename)
    mocked_delete_s3_object.assert_called_once_with(upload_filename)


def test_persist_logo_returns_if_not_temp(client_request, mocker, fake_uuid):
    filename = 'logo.png'
    persist_logo(filename, filename)

    mocked_get_s3_object = mocker.patch('app.s3_client.s3_logo_client.get_s3_object')
    mocked_delete_s3_object = mocker.patch('app.s3_client.s3_logo_client.delete_s3_object')

    assert mocked_get_s3_object.called is False
    assert mocked_delete_s3_object.called is False


def test_permanent_email_logo_name_removes_TEMP_TAG_from_filename(upload_filename, fake_uuid):
    new_name = permanent_email_logo_name(upload_filename, fake_uuid)

    assert new_name == 'test_uuid-test.png'


def test_permanent_email_logo_name_does_not_change_filenames_with_no_TEMP_TAG():
    filename = 'logo.png'
    new_name = permanent_email_logo_name(filename, filename)

    assert new_name == filename


def test_letter_filename_for_db_when_file_has_a_temp_tag(fake_uuid):
    temp_filename = LETTER_TEMP_LOGO_LOCATION.format(user_id=fake_uuid, unique_id=upload_id, filename=svg_filename)
    assert letter_filename_for_db(temp_filename, fake_uuid) == 'test_uuid-test'


def test_letter_filename_for_db_when_file_does_not_have_a_temp_tag(fake_uuid):
    filename = 'letters/static/images/letter-template/{}-test.svg'.format(fake_uuid)
    assert letter_filename_for_db(filename, fake_uuid) == '{}-test'.format(fake_uuid)


def test_delete_email_temp_files_created_by_user(client_request, mocker, fake_uuid):
    obj = namedtuple("obj", ["key"])
    objs = [obj(key='test1'), obj(key='test2')]

    mocker.patch('app.s3_client.s3_logo_client.get_s3_objects_filter_by_prefix', return_value=objs)
    mocked_delete_s3_object = mocker.patch('app.s3_client.s3_logo_client.delete_s3_object')

    delete_email_temp_files_created_by(fake_uuid)

    for index, arg in enumerate(mocked_delete_s3_object.call_args_list):
        assert arg == call(objs[index].key)


def test_delete_letter_temp_files_created_by_user(mocker, fake_uuid):
    obj = namedtuple("obj", ["key"])
    objs = [obj(key='test1'), obj(key='test2')]

    mocker.patch('app.s3_client.s3_logo_client.get_s3_objects_filter_by_prefix', return_value=objs)
    mocked_delete_s3_object = mocker.patch('app.s3_client.s3_logo_client.delete_s3_object')

    delete_letter_temp_files_created_by(fake_uuid)

    for index, arg in enumerate(mocked_delete_s3_object.call_args_list):
        assert arg == call(objs[index].key)


def test_delete_single_email_temp_file(client_request, mocker, upload_filename):
    mocked_delete_s3_object = mocker.patch('app.s3_client.s3_logo_client.delete_s3_object')

    delete_email_temp_file(upload_filename)

    mocked_delete_s3_object.assert_called_with(upload_filename)


def test_does_not_delete_non_temp_email_file(client_request, mocker):
    filename = 'logo.png'
    mocked_delete_s3_object = mocker.patch('app.s3_client.s3_logo_client.delete_s3_object')

    with pytest.raises(ValueError) as error:
        delete_email_temp_file(filename)

    assert mocked_delete_s3_object.called is False
    assert str(error.value) == 'Not a temp file: {}'.format(filename)


def test_delete_single_temp_letter_file(mocker, fake_uuid, upload_filename):
    mocked_delete_s3_object = mocker.patch('app.s3_client.s3_logo_client.delete_s3_object')

    upload_filename = LETTER_TEMP_TAG.format(user_id=fake_uuid) + svg_filename

    delete_letter_temp_file(upload_filename)

    mocked_delete_s3_object.assert_called_with(upload_filename)


def test_does_not_delete_non_temp_letter_file(mocker, fake_uuid):
    mocked_delete_s3_object = mocker.patch('app.s3_client.s3_logo_client.delete_s3_object')

    with pytest.raises(ValueError) as error:
        delete_letter_temp_file(svg_filename)

    assert mocked_delete_s3_object.called is False
    assert str(error.value) == 'Not a temp file: {}'.format(svg_filename)
