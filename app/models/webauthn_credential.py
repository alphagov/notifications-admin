import base64

from fido2 import cbor
from fido2.client import ClientData
from fido2.cose import UnsupportedKey
from fido2.ctap2 import AttestationObject, AttestedCredentialData
from flask import current_app

from app.models import JSONModel, ModelList
from app.notify_client.user_api_client import user_api_client


class RegistrationError(Exception):
    pass


class WebAuthnCredential(JSONModel):
    ALLOWED_PROPERTIES = {
        'id',
        'name',
        'credential_data',  # contains public key and credential ID for auth
        'registration_response',  # sent to API for later auditing (not used)
        'created_at',
        'updated_at'
    }

    @classmethod
    def from_registration(cls, state, response):
        server = current_app.webauthn_server

        try:
            auth_data = server.register_complete(
                state,
                ClientData(response["clientDataJSON"]),
                AttestationObject(response["attestationObject"]),
            )
        except ValueError as e:
            raise RegistrationError(e)

        if isinstance(auth_data.credential_data.public_key, UnsupportedKey):
            raise RegistrationError("Encryption algorithm not supported")

        return cls({
            'name': 'Unnamed key',
            'credential_data': base64.b64encode(
                cbor.encode(auth_data.credential_data),
            ).decode('utf-8'),
            'registration_response': base64.b64encode(
                cbor.encode(response),
            ).decode('utf-8')
        })

    def to_credential_data(self):
        return AttestedCredentialData(
            cbor.decode(base64.b64decode(self.credential_data.encode()))
        )

    def serialize(self):
        return {
            'name': self.name,
            'credential_data': self.credential_data,
            'registration_response': self.registration_response,
        }


class WebAuthnCredentials(ModelList):

    model = WebAuthnCredential
    client_method = user_api_client.get_webauthn_credentials_for_user

    @property
    def as_cbor(self):
        return [credential.to_credential_data() for credential in self]

    def by_id(self, key_id):
        return next((key for key in self if key.id == key_id), None)
