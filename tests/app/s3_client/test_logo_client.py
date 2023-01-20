from io import BytesIO

import boto3
import pytest

LOGO_TYPES = ["email", "letter"]


class TestLogoClientSlugify:
    @pytest.mark.parametrize(
        "text, expected_slug",
        (
            ("blah", "blah"),
            ("replace stuff", "replace-stuff"),
            ("replace [] stuff", "replace-stuff"),
            ("a110w numb3r5", "a110w-numb3r5"),
            ("only \x03😈alphanumeric\t\nstuff", "only-alphanumeric-stuff"),
            ("LOWERCASE", "lowercase"),
            ("remove----many------dashes", "remove-many-dashes"),
            ("[] (no leading or trailing dashes))] ][", "no-leading-or-trailing-dashes"),
        ),
    )
    def test_expected_slugs(self, logo_client, text, expected_slug):
        assert logo_client._slugify(text) == expected_slug


class TestLogoClientGetTemporaryLogoAbsolutePath:
    @pytest.mark.parametrize(
        "file_name, logo_type, expected_path",
        (
            ("my-logo.png", "email", "temporary/email/my-logo.png"),
            ("my-logo.svg", "letter", "temporary/letter/my-logo.svg"),
        ),
    )
    def test_expected_path(self, logo_client, file_name, logo_type, expected_path):
        assert logo_client._get_temporary_logo_key(file_name, logo_type=logo_type) == expected_path


class TestLogoClientGetPermanentLogoAbsolutePath:
    @pytest.mark.parametrize(
        "file_name, logo_type, file_name_extra, expected_path",
        (
            ("my-logo.png", "email", None, "email/my-logo.png"),
            ("my-logo.png", "email", "extra-stuff", "email/my-logo-extra-stuff.png"),
            ("my-logo.png", "email", "NON standard *&^%$£ extras", "email/my-logo-non-standard-extras.png"),
            ("my-logo.svg", "letter", None, "letters/static/images/letter-template/my-logo.svg"),
            ("my-logo.svg", "letter", "extra-stuff", "letters/static/images/letter-template/my-logo-extra-stuff.svg"),
            (
                "my-logo.png",
                "letter",
                "NON standard *&^%$£ extras",
                "letters/static/images/letter-template/my-logo-non-standard-extras.png",
            ),
        ),
    )
    def test_expected_path(self, logo_client, file_name, logo_type, file_name_extra, expected_path):
        assert (
            logo_client._get_permanent_logo_key(file_name, logo_type=logo_type, logo_key_extra=file_name_extra)
            == expected_path
        )


class TestLogoClientSaveTemporaryLogo:
    @pytest.mark.parametrize(
        "logo_type, file_extension, content_type, expected_location",
        (
            ("email", ".png", "image/png", "temporary/email/uuid.png"),
            ("letter", ".svg", "image/svg+xml", "temporary/letter/uuid.svg"),
        ),
    )
    def test_expected_s3upload_call(
        self, mocker, logo_client, logo_type, file_extension, content_type, expected_location
    ):
        mock_utils_s3upload = mocker.patch("app.s3_client.logo_client.utils_s3upload")
        mock_uui4 = mocker.patch("app.s3_client.logo_client.uuid.uuid4")
        mock_uui4.return_value = "uuid"

        file_data = BytesIO()

        retval = logo_client.save_temporary_logo(
            file_data, logo_type=logo_type, file_extension=file_extension, content_type=content_type
        )

        assert mock_utils_s3upload.call_args_list == [
            mocker.call(
                filedata=file_data,
                region="eu-west-1",
                bucket_name="public-logos-test",
                file_location=expected_location,
                content_type=content_type,
            )
        ]
        assert retval == expected_location


class TestLogoClientSavePermanentLogo:
    def s3_setup(self, app):
        s3 = boto3.client("s3", region_name=app.config["AWS_REGION"])
        s3.create_bucket(Bucket=app.config["LOGO_UPLOAD_BUCKET_NAME"])

    @pytest.mark.parametrize(
        "temporary_logo_key, logo_type, logo_key_extra, expected_location",
        (
            ("temporary/email/uuid.png", "email", None, "email/uuid.png"),
            ("temporary/email/uuid.png", "email", "some extra", "email/uuid-some-extra.png"),
            ("temporary/letter/uuid.png", "letter", None, "letters/static/images/letter-template/uuid.png"),
            (
                "temporary/letter/uuid.png",
                "letter",
                "some extra",
                "letters/static/images/letter-template/uuid-some-extra.png",
            ),
        ),
    )
    def test_copies_object(
        self,
        mocker,
        notify_admin,
        logo_client,
        temporary_logo_key,
        logo_type,
        logo_key_extra,
        expected_location,
    ):
        mock_s3_resource = mocker.patch.object(logo_client, "client")
        mock_s3_object = mock_s3_resource.Object()

        retval = logo_client.save_permanent_logo(temporary_logo_key, logo_type=logo_type, logo_key_extra=logo_key_extra)

        assert mock_s3_object.copy_from.call_args_list == [
            mocker.call(CopySource=f"public-logos-test/{temporary_logo_key}")
        ]
        assert retval == expected_location
