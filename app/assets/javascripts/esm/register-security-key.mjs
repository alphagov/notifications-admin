import { isSupported } from 'govuk-frontend';
import ErrorBanner from './error-banner.mjs';
import { locationReload } from './utils.mjs';

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
    // parseCreationOptionsFromJSON is needed to read the JSON options the server sends
    if (!isSupported() || !window.PublicKeyCredential?.parseCreationOptionsFromJSON) {
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

    return response.json();
  }

  createCredential(options) {
    // triggers browser dialogue to select authenticator
    return window.navigator.credentials.create({
      publicKey: window.PublicKeyCredential.parseCreationOptionsFromJSON(options.publicKey),
    });
  }

  postCredential(credential) {
    return fetch(this.registerAuthenticationEndpoint, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': this.$module.dataset.csrfToken,
      },
      // JSON.stringify calls credential.toJSON(), which base64url-encodes the binary fields
      body: JSON.stringify(credential),
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
