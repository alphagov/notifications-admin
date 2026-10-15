import { isSupported } from 'govuk-frontend';
import ErrorBanner from './error-banner.mjs';
import { locationAssign } from './utils.mjs';

// This new way of writing Javascript components is based on the GOV.UK Frontend skeleton Javascript coding standard
// that uses ES 2015 Classes -
// https://github.com/alphagov/govuk-frontend/blob/main/docs/contributing/coding-standards/js.md#skeleton
//
// It replaces the previously used way of setting methods on the component's `prototype`.
// We use a class declaration way of defining classes -
// https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Statements/class
//
// More on ES2015 Classes at https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Classes

class AuthenticateSecurityKey {
  constructor($module) {
    // parseRequestOptionsFromJSON is needed to read the JSON options the server sends
    if (!isSupported() || !window.PublicKeyCredential?.parseRequestOptionsFromJSON) {
      return this;
    }
    this.authenticationEndpoint = '/webauthn/authenticate';
    this.$module = $module;

    this.$module.addEventListener('click', this.authenticateKey.bind(this));
  }

  async authenticateKey(e) {
    e.preventDefault();

    try {
      const options = await this.handleFetch();
      const credential = await this.getCredential(options);
      const response = await this.postCredential(credential);
      await this.handleCredentialResponse(response);
    } catch (error) {
      this.handleError(error);
    }
  }

  async handleFetch() {
    const response = await fetch(this.authenticationEndpoint);

    if (!response.ok) {
      throw Error(response.statusText);
    }

    return response.json();
  }

  async getCredential(options) {
    // triggers browser dialogue to login with authenticator
    return window.navigator.credentials.get({
      publicKey: window.PublicKeyCredential.parseRequestOptionsFromJSON(options.publicKey),
    });
  }

  async postCredential(credential) {
    const currentURL = new URL(window.location.href);

    // create authenticateURL from admin hostname plus authentication endpoint path
    const authenticateURL = new URL(this.authenticationEndpoint, window.location.href);

    const nextUrl = currentURL.searchParams.get('next');
    if (nextUrl) {
      // takes nextUrl from the query string on the current browser URL
      // (which should be /two-factor-webauthn) and pass it through to
      // the POST. put it in a query string so it's consistent with how
      // the other login flows manage it
      authenticateURL.searchParams.set('next', nextUrl);
    }

    return fetch(authenticateURL, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': this.$module.dataset.csrfToken,
      },
      // JSON.stringify calls credential.toJSON(), which base64url-encodes the binary fields
      body: JSON.stringify(credential),
    });
  }

  async handleCredentialResponse(response) {
    if (!response.ok) {
      throw Error(response.statusText);
    }

    const data = await response.json();

    // Redirect the user on successful authentication
    locationAssign(data.redirect_url);
  }

  handleError(error) {
    console.error(error);
    // some browsers will show an error dialogue for some errors;
    // to be safe we always display an error message on the page.
    new ErrorBanner('.webauthn__error').showBanner();
  }
}

export default AuthenticateSecurityKey;
