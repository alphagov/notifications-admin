import base64

from fido2 import cbor
from fido2.client import ClientData
from fido2.ctap2 import AttestationObject, AttestedCredentialData
from flask import current_app

from app.models import JSONModel


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

        auth_data = server.register_complete(
            state,
            ClientData(response["clientDataJSON"]),
            AttestationObject(response["attestationObject"]),
        )

        return cls({
            'name': 'Unnamed key',
            'credential_data': base64.b64encode(
                cbor.encode(auth_data.credential_data),
            ),
            'registration_response': base64.b64encode(
                cbor.encode(response),
            )
        })

    def to_credential_data(self):
        return AttestedCredentialData(
            cbor.decode(base64.b64decode(self.credential_data))
        )

    def serialize(self):
        return {
            'name': self.name,
            'credential_data': self.credential_data,
            'registration_response': self.registration_response,
        }
