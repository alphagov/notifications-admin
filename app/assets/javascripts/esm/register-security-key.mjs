import { isSupported } from 'govuk-frontend';
import ErrorBanner from './error-banner.mjs';
import { locationReload } from '../utils/location.mjs';
import { decode, encode } from 'cbor2';

// This new way of writing Javascript components is based on the GOV.UK Frontend skeleton Javascript coding standard
// that uses ES 2015 Classes -
// https://github.com/alphagov/govuk-frontend/blob/main/docs/contributing/coding-standards/js.md#skeleton
//
// It replaces the previously used way of setting methods on the component's `prototype`.
// We use a class declaration way of defining classes -
// https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Statements/class
//
// More on ES2015 Classes at https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Classes

class RegisterSecurityKey {
  constructor($module) {
    if (!isSupported() || !window.TextEncoder) {
      return this;
    }
    this.registerAuthenticationEndpoint = '/webauthn/register';
    this.$module = $module;

    this.$module.addEventListener('click', this.registerKey.bind(this));
  }

  async registerKey(e) {
    e.preventDefault();

    try {
      const options = await this.handleFetch();
      const credential = await this.createCredential(options);
      const response = await this.postCredential(credential);
      this.handleCredentialResponse(response);
    } catch (error) {
      this.handleError(error);
    }
  }

  async handleFetch() {
    const response = await fetch(this.registerAuthenticationEndpoint);

    if (!response.ok) {
      throw Error(response.statusText);
    }

    const data = await response.arrayBuffer();
    return decode(new Uint8Array(data));
  }

  createCredential(options) {
    // triggers browser dialogue to select authenticator
    return window.navigator.credentials.create(options);
  }

  postCredential(credential) {
    return fetch(this.registerAuthenticationEndpoint, {
      method: 'POST',
      headers: { 'X-CSRFToken': this.$module.dataset.csrfToken },
      body: encode({
        attestationObject: new Uint8Array(credential.response.attestationObject),
        clientDataJSON: new Uint8Array(credential.response.clientDataJSON),
      })
    });
  }

  handleCredentialResponse(response) {
    if (!response.ok) {
      throw Error(response.statusText);
    }
    locationReload();
  }

  handleError(error) {
    console.error(error);
    // some browsers will show an error dialogue for some errors;
    // to be safe we always display an error message on the page.
    new ErrorBanner('.webauthn__error').showBanner();
  }
}

export default RegisterSecurityKey;
