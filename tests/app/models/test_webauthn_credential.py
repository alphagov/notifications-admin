import base64

import pytest
from fido2 import cbor
from fido2.cose import ES256

from app import webauthn_server
from app.models.webauthn_credential import WebAuthnCredential

# noqa adapted from https://github.com/duo-labs/py_webauthn/blob/90e3d97e0182899a35a70fc510280b4082cce19b/tests/test_webauthn.py#L14-L24
SESSION_STATE = {'challenge': 'bPzpX3hHQtsp9evyKYkaZtVc9UN07PUdJ22vZUdDp94', 'user_verification': 'discouraged'}
CLIENT_DATA_JSON = b'{"type": "webauthn.create", "clientExtensions": {}, "challenge": "bPzpX3hHQtsp9evyKYkaZtVc9UN07PUdJ22vZUdDp94", "origin": "https://webauthn.io"}'  # noqa

# had to use the cbor2 library to re-encode the attestationObject due to implementation differences
ATTESTATION_OBJECT = base64.b64decode(b'o2NmbXRoZmlkby11MmZnYXR0U3RtdKJjc2lnWEgwRgIhAI1qbvWibQos/t3zsTU05IXw1Ek3SDApATok09uc4UBwAiEAv0fB/lgb5Ot3zJ691Vje6iQLAtLhJDiA8zDxaGjcE3hjeDVjgVkCUzCCAk8wggE3oAMCAQICBDxoKU0wDQYJKoZIhvcNAQELBQAwLjEsMCoGA1UEAxMjWXViaWNvIFUyRiBSb290IENBIFNlcmlhbCA0NTcyMDA2MzEwIBcNMTQwODAxMDAwMDAwWhgPMjA1MDA5MDQwMDAwMDBaMDExLzAtBgNVBAMMJll1YmljbyBVMkYgRUUgU2VyaWFsIDIzOTI1NzM0ODExMTE3OTAxMFkwEwYHKoZIzj0CAQYIKoZIzj0DAQcDQgAEvd9nk9t3lMNQMXHtLE1FStlzZnUaSLql2fm1ajoggXlrTt8rzXuSehSTEPvEaEdv/FeSqX22L6Aoa8ajIAIOY6M7MDkwIgYJKwYBBAGCxAoCBBUxLjMuNi4xLjQuMS40MTQ4Mi4xLjUwEwYLKwYBBAGC5RwCAQEEBAMCBSAwDQYJKoZIhvcNAQELBQADggEBAKrADVEJfuwVpIazebzEg0D4Z9OXLs5qZ/ukcONgxkRZ8K04QtP/CB5x6olTlxsj+SXArQDCRzEYUgbws6kZKfuRt2a1P+EzUiqDWLjRILSr+3/o7yR7ZP/GpiFKwdm+czb94POoGD+TS1IYdfXj94mAr5cKWx4EKjh210uovu/pLdLjc8xkQciUrXzZpPR9rT2k/q9HkZhHU+NaCJzky+PTyDbq0KKnzqVhWtfkSBCGw3ezZkTS+5lrvOKbIa24lfeTgu7FST5OwTPCFn8HcfWZMXMSD/KNU+iBqJdAwTLPPDRoLLvPTl29weCAIh+HUpmBQd0UltcPOrA/LFvAf61oYXV0aERhdGFYwnSm6pITyZwvdLIkkrMgz0AmKpTBqVCgOX8pJQtghB7wQQAAAAAAAAAAAAAAAAAAAAAAAAAAAECKU1ppjl9gmhHWyDkgHsUvZmhr6oF3/lD3llzLE2SaOSgOGIsIuAQqgp8JQSUu3r/oOaP8RS44dlQjrH+ALfYtpAECAyYhWCAxnqAfESXOYjKUc2WACuXZ3ch0JHxV0VFrrTyjyjIHXCJYIFnx8H87L4bApR4M+hPcV+fHehEOeW+KCyd0H+WGY8s6')  # noqa


@pytest.fixture
def disable_webauthn_origin_verification(app_, mocker):
    mocker.patch.dict(
        app_.config, values={
            'NOTIFY_ENVIRONMENT': 'development',
            'ADMIN_BASE_URL': 'https://webauthn.io',
        }
    )

    # disable origin verification for non-HTTPS test
    webauthn_server.init_app(app_)


def test_from_registration_verifies_response(disable_webauthn_origin_verification):
    registration_response = {
       'clientDataJSON': CLIENT_DATA_JSON,
       'attestationObject': ATTESTATION_OBJECT,
    }

    credential = WebAuthnCredential.from_registration(SESSION_STATE, registration_response)
    assert credential.name == 'Unnamed key'
    assert credential.registration_response == base64.b64encode(cbor.encode(registration_response)).decode('utf-8')

    credential_data = credential.to_credential_data()
    assert type(credential_data.credential_id) is bytes
    assert type(credential_data.aaguid) is bytes
    assert credential_data.public_key[3] == ES256.ALGORITHM


def test_from_registration_encodes_as_unicode(disable_webauthn_origin_verification):
    registration_response = {
       'clientDataJSON': CLIENT_DATA_JSON,
       'attestationObject': ATTESTATION_OBJECT,
    }

    credential = WebAuthnCredential.from_registration(SESSION_STATE, registration_response)

    serialized_credential = credential.serialize()

    assert type(serialized_credential['credential_data']) == str
    assert type(serialized_credential['registration_response']) == str
