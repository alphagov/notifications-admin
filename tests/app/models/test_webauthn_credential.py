import base64

import pytest
from fido2 import cbor
from fido2.cose import ES256
from fido2.webauthn import Aaguid

from app.models.webauthn_credential import RegistrationError, WebAuthnCredential

# adapted from https://github.com/duo-labs/py_webauthn/blob/90e3d97e0182899a35a70fc510280b4082cce19b/tests/test_webauthn.py#L14-L24
SESSION_STATE = {"challenge": "bPzpX3hHQtsp9evyKYkaZtVc9UN07PUdJ22vZUdDp94", "user_verification": "discouraged"}
CLIENT_DATA_JSON = b'{"type": "webauthn.create", "clientExtensions": {}, "challenge": "bPzpX3hHQtsp9evyKYkaZtVc9UN07PUdJ22vZUdDp94", "origin": "https://webauthn.io"}'  # noqa

# had to use the cbor2 library to re-encode the attestationObject due to implementation differences
ATTESTATION_OBJECT = base64.b64decode(
    b"o2NmbXRoZmlkby11MmZnYXR0U3RtdKJjc2lnWEgwRgIhAI1qbvWibQos/t3zsTU05IXw1Ek3SDApATok09uc4UBwAiEAv0fB/lgb5Ot3zJ691Vje6iQLAtLhJDiA8zDxaGjcE3hjeDVjgVkCUzCCAk8wggE3oAMCAQICBDxoKU0wDQYJKoZIhvcNAQELBQAwLjEsMCoGA1UEAxMjWXViaWNvIFUyRiBSb290IENBIFNlcmlhbCA0NTcyMDA2MzEwIBcNMTQwODAxMDAwMDAwWhgPMjA1MDA5MDQwMDAwMDBaMDExLzAtBgNVBAMMJll1YmljbyBVMkYgRUUgU2VyaWFsIDIzOTI1NzM0ODExMTE3OTAxMFkwEwYHKoZIzj0CAQYIKoZIzj0DAQcDQgAEvd9nk9t3lMNQMXHtLE1FStlzZnUaSLql2fm1ajoggXlrTt8rzXuSehSTEPvEaEdv/FeSqX22L6Aoa8ajIAIOY6M7MDkwIgYJKwYBBAGCxAoCBBUxLjMuNi4xLjQuMS40MTQ4Mi4xLjUwEwYLKwYBBAGC5RwCAQEEBAMCBSAwDQYJKoZIhvcNAQELBQADggEBAKrADVEJfuwVpIazebzEg0D4Z9OXLs5qZ/ukcONgxkRZ8K04QtP/CB5x6olTlxsj+SXArQDCRzEYUgbws6kZKfuRt2a1P+EzUiqDWLjRILSr+3/o7yR7ZP/GpiFKwdm+czb94POoGD+TS1IYdfXj94mAr5cKWx4EKjh210uovu/pLdLjc8xkQciUrXzZpPR9rT2k/q9HkZhHU+NaCJzky+PTyDbq0KKnzqVhWtfkSBCGw3ezZkTS+5lrvOKbIa24lfeTgu7FST5OwTPCFn8HcfWZMXMSD/KNU+iBqJdAwTLPPDRoLLvPTl29weCAIh+HUpmBQd0UltcPOrA/LFvAf61oYXV0aERhdGFYwnSm6pITyZwvdLIkkrMgz0AmKpTBqVCgOX8pJQtghB7wQQAAAAAAAAAAAAAAAAAAAAAAAAAAAECKU1ppjl9gmhHWyDkgHsUvZmhr6oF3/lD3llzLE2SaOSgOGIsIuAQqgp8JQSUu3r/oOaP8RS44dlQjrH+ALfYtpAECAyYhWCAxnqAfESXOYjKUc2WACuXZ3ch0JHxV0VFrrTyjyjIHXCJYIFnx8H87L4bApR4M+hPcV+fHehEOeW+KCyd0H+WGY8s6"
)

# manually adapted by working out which character in the encoded CBOR corresponds to the public key algorithm ID
UNSUPPORTED_ATTESTATION_OBJECT = base64.b64decode(
    b"o2NmbXRoZmlkby11MmZnYXR0U3RtdKJjc2lnWEgwRgIhAI1qbvWibQos/t3zsTU05IXw1Ek3SDApATok09uc4UBwAiEAv0fB/lgb5Ot3zJ691Vje6iQLAtLhJDiA8zDxaGjcE3hjeDVjgVkCUzCCAk8wggE3oAMCAQICBDxoKU0wDQYJKoZIhvcNAQELBQAwLjEsMCoGA1UEAxMjWXViaWNvIFUyRiBSb290IENBIFNlcmlhbCA0NTcyMDA2MzEwIBcNMTQwODAxMDAwMDAwWhgPMjA1MDA5MDQwMDAwMDBaMDExLzAtBgNVBAMMJll1YmljbyBVMkYgRUUgU2VyaWFsIDIzOTI1NzM0ODExMTE3OTAxMFkwEwYHKoZIzj0CAQYIKoZIzj0DAQcDQgAEvd9nk9t3lMNQMXHtLE1FStlzZnUaSLql2fm1ajoggXlrTt8rzXuSehSTEPvEaEdv/FeSqX22L6Aoa8ajIAIOY6M7MDkwIgYJKwYBBAGCxAoCBBUxLjMuNi4xLjQuMS40MTQ4Mi4xLjUwEwYLKwYBBAGC5RwCAQEEBAMCBSAwDQYJKoZIhvcNAQELBQADggEBAKrADVEJfuwVpIazebzEg0D4Z9OXLs5qZ/ukcONgxkRZ8K04QtP/CB5x6olTlxsj+SXArQDCRzEYUgbws6kZKfuRt2a1P+EzUiqDWLjRILSr+3/o7yR7ZP/GpiFKwdm+czb94POoGD+TS1IYdfXj94mAr5cKWx4EKjh210uovu/pLdLjc8xkQciUrXzZpPR9rT2k/q9HkZhHU+NaCJzky+PTyDbq0KKnzqVhWtfkSBCGw3ezZkTS+5lrvOKbIa24lfeTgu7FST5OwTPCFn8HcfWZMXMSD/KNU+iBqJdAwTLPPDRoLLvPTl29weCAIh+HUpmBQd0UltcPOrA/LFvAf61oYXV0aERhdGFYwnSm6pITyZwvdLIkkrMgz0AmKpTBqVCgOX8pJQtghB7wQQAAAAAAAAAAAAAAAAAAAAAAAAAAAECKU1ppjl9gmhHWyDkgHsUvZmhr6oF3/lD3llzLE2SaOSgOGIsIuAQqgp8JQSUu3r/oOaP8RS44dlQjrH+ALfYtpAECAyUhWCAxnqAfESXOYjKUc2WACuXZ3ch0JHxV0VFrrTyjyjIHXCJYIFnx8H87L4bApR4M+hPcV+fHehEOeW+KCyd0H+WGY8s6"
)


def test_from_registration_verifies_response(webauthn_dev_server):
    registration_response = {
        "clientDataJSON": CLIENT_DATA_JSON,
        "attestationObject": ATTESTATION_OBJECT,
    }

    credential = WebAuthnCredential.from_registration(SESSION_STATE, registration_response)
    assert credential.name == "Unnamed key"
    assert credential.registration_response == base64.b64encode(cbor.encode(registration_response)).decode("utf-8")

    credential_data = credential.to_credential_data()
    assert isinstance(credential_data.credential_id, bytes)
    assert isinstance(credential_data.aaguid, Aaguid)
    assert isinstance(credential_data.aaguid, bytes)
    assert credential_data.public_key[3] == ES256.ALGORITHM


def test_from_registration_encodes_as_unicode(webauthn_dev_server):
    registration_response = {
        "clientDataJSON": CLIENT_DATA_JSON,
        "attestationObject": ATTESTATION_OBJECT,
    }

    credential = WebAuthnCredential.from_registration(SESSION_STATE, registration_response)

    serialized_credential = credential.serialize()

    assert isinstance(serialized_credential["credential_data"], str)
    assert isinstance(serialized_credential["registration_response"], str)


def test_serialize_returns_valid_typeddict(webauthn_dev_server):
    # Create a test credential with known values
    from datetime import datetime

    now = datetime.now()

    credential = WebAuthnCredential(
        {
            "id": "123",
            "name": "Test Key",
            "credential_data": "test_credential_data",
            "registration_response": "test_response",
            "created_at": now,
            "updated_at": now,
            "logged_in_at": None,  # Test the Optional case
        }
    )

    # Get serialized form
    serialized = credential.serialize()

    # Verify it matches our TypedDict structure
    assert set(serialized.keys()) == {"name", "credential_data", "registration_response"}

    assert isinstance(serialized.get("name"), str)
    assert isinstance(serialized.get("credential_data"), str)
    assert isinstance(serialized.get("registration_response"), str)

    assert serialized.get("name") == "Test Key"
    assert serialized.get("credential_data") == "test_credential_data"
    assert serialized.get("registration_response") == "test_response"
    assert serialized.get("id") is None  # Not included in TypedDict
    assert serialized.get("created_at") is None  # Not included in TypedDict
    assert serialized.get("updated_at") is None  # Not included in TypedDict
    assert serialized.get("logged_in_at") is None  # Not included in TypedDict


def test_from_registration_handles_library_errors(notify_admin):
    registration_response = {
        "clientDataJSON": CLIENT_DATA_JSON,
        "attestationObject": ATTESTATION_OBJECT,
    }

    with pytest.raises(RegistrationError) as exc_info:
        WebAuthnCredential.from_registration(SESSION_STATE, registration_response)

    assert "Invalid origin" in str(exc_info.value)


def test_from_registration_handles_unsupported_keys(webauthn_dev_server):
    registration_response = {
        "clientDataJSON": CLIENT_DATA_JSON,
        "attestationObject": UNSUPPORTED_ATTESTATION_OBJECT,
    }

    with pytest.raises(RegistrationError) as exc_info:
        WebAuthnCredential.from_registration(SESSION_STATE, registration_response)

    assert "Encryption algorithm not supported" in str(exc_info.value)
