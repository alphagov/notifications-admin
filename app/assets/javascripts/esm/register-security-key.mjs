import { isSupported } from 'govuk-frontend';
import ErrorBanner from './error-banner.mjs';

// This new way of writing Javascript components is based on the GOV.UK Frontend skeleton Javascript coding standard
// that uses ES2015 Classes -
// https://github.com/alphagov/govuk-frontend/blob/main/docs/contributing/coding-standards/js.md#skeleton
//
// It replaces the previously used way of setting methods on the component's `prototype`.
// We use a class declaration way of defining classes -
// https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Statements/class
//
// More on ES2015 Classes at https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Classes

class RegisterSecurityKey {
  constructor($module) {
    if (!isSupported()) {
      return this;
    }
    this.registerPath = '/webauthn/register';
    this.$module = $module;

    this.$module.addEventListener("click", () => {
      new ErrorBanner().hideBanner();
      this.getAuthentication();
    });
  }
  getAuthentication() {
    fetch(this.registerPath)
      .then((response) => {
        if (!response.ok) {
          throw Error(response.statusText);
        }

        return response.arrayBuffer();
      })
      .then((data) => {
        var options = window.CBOR.decode(data);
        // triggers browser dialogue to select authenticator
        return window.navigator.credentials.create(options);
      })
      .then((credential) => {
        return this.postWebAuthnCreateResponse(
          credential.response, this.$module.dataset.csrfToken
        );
      })
      .then((response) => {
        if (!response.ok) {
          throw Error(response.statusText);
        }

        window.location.reload();
      })
      .catch((error) => {
        console.error(error);
        // some browsers will show an error dialogue for some
        // errors; to be safe we always display an error message on the page.
        new ErrorBanner().showBanner();
      });
  }
  postWebAuthnCreateResponse(response, csrf_token) {
    return fetch(this.registerPath, {
      method: 'POST',
      headers: { 'X-CSRFToken': csrf_token },
      body: window.CBOR.encode({
        attestationObject: new Uint8Array(response.attestationObject),
        clientDataJSON: new Uint8Array(response.clientDataJSON),
      })
    });
  }
}

export default RegisterSecurityKey;
