from collections import namedtuple
from unittest.mock import call
import pytest

from app.main.s3_client import (
    upload_logo,
    persist_logo,
    delete_temp_file,
    delete_temp_files_created_by,
    get_temp_truncated_filename,
    LOGO_LOCATION_STRUCTURE,
    TEMP_TAG
)

bucket = 'test_bucket'
data = {'data': 'some_data'}
filename = 'test.png'
upload_id = 'test_uuid'
region = 'eu-west1'


@pytest.fixture
def upload_filename(fake_uuid):
    return LOGO_LOCATION_STRUCTURE.format(
        temp=TEMP_TAG.format(user_id=fake_uuid), unique_id=upload_id, filename=filename)


def test_upload_logo_calls_correct_args(client, mocker, fake_uuid, upload_filename):
    mocker.patch('uuid.uuid4', return_value=upload_id)
    mocker.patch.dict('flask.current_app.config', {'LOGO_UPLOAD_BUCKET_NAME': bucket})
    mocked_s3_upload = mocker.patch('app.main.s3_client.utils_s3upload')

    upload_logo(filename=filename, user_id=fake_uuid, filedata=data, region=region)

    assert mocked_s3_upload.called_once_with(
        filedata=data,
        region=region,
        file_location=upload_filename,
        bucket_name=bucket
    )


def test_persist_logo(client, mocker, fake_uuid, upload_filename):
    mocker.patch.dict('flask.current_app.config', {'LOGO_UPLOAD_BUCKET_NAME': bucket})
    mocked_rename_s3_object = mocker.patch('app.main.s3_client.rename_s3_object')

    persisted_filename = persist_logo(filename=upload_filename, user_id=fake_uuid)

    assert mocked_rename_s3_object.called_once_with(
        upload_filename, get_temp_truncated_filename(upload_filename, fake_uuid))
    assert persisted_filename == get_temp_truncated_filename(upload_filename, fake_uuid)


def test_persist_logo_returns_if_not_temp(client, mocker, fake_uuid):
    filename = 'logo.png'
    mocker.patch.dict('flask.current_app.config', {'LOGO_UPLOAD_BUCKET_NAME': bucket})
    mocked_rename_s3_object = mocker.patch('app.main.s3_client.rename_s3_object')

    persisted_filename = persist_logo(filename=filename, user_id=fake_uuid)

    assert not mocked_rename_s3_object.called
    assert persisted_filename == filename


def test_delete_temp_files_created_by_user(client, mocker, fake_uuid):
    obj = namedtuple("obj", ["key"])
    objs = [obj(key='test1'), obj(key='test2')]

    mocker.patch('app.main.s3_client.get_s3_objects_filter_by_prefix', return_value=objs)
    mocked_delete_s3_object = mocker.patch('app.main.s3_client.delete_s3_object')

    delete_temp_files_created_by(fake_uuid)

    assert mocked_delete_s3_object.called_with_args(objs[0].key)
    for index, arg in enumerate(mocked_delete_s3_object.call_args_list):
        assert arg == call(objs[index].key)


def test_delete_single_temp_file(client, mocker, fake_uuid, upload_filename):
    mocked_delete_s3_object = mocker.patch('app.main.s3_client.delete_s3_object')

    delete_temp_file(upload_filename)

    assert mocked_delete_s3_object.called_with_args(upload_filename)


def test_does_not_delete_non_temp_file(client, mocker, fake_uuid):
    filename = 'logo.png'
    mocked_delete_s3_object = mocker.patch('app.main.s3_client.delete_s3_object')

    with pytest.raises(ValueError) as error:
        delete_temp_file(filename)

    assert mocked_delete_s3_object.called_with_args(filename)
    assert str(error.value) == 'Not a temp file: {}'.format(filename)
