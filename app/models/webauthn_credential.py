from app.models import JSONModel


class WebAuthnCredential(JSONModel):
    ALLOWED_PROPERTIES = {
        'id',
        'name',
        'credential_data',
        'created_at',
        'updated_at'
    }
