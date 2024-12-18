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

class AuthenticateSecurityKey {
  constructor($module) {
    if (!isSupported()) {
      return this;
    }
    this.authenticatePath = '/webauthn/authenticate';
    this.$module = $module;

    this.$module.addEventListener("click", () => {
      new ErrorBanner().hideBanner();
      this.getAuthentication();
    });
  }
  getAuthentication() {
    fetch(this.authenticatePath)
      .then(response => {
        if (!response.ok) {
          throw Error(response.statusText);
        }

        return response.arrayBuffer();
      })
      .then(data => {
        var options = window.CBOR.decode(data);
        // triggers browser dialogue to login with authenticator
        return window.navigator.credentials.get(options);
      })
      .then(credential => {
        const currentURL = new URL(window.location.href);

        // create authenticateURL from admin hostname plus /webauthn/authenticate path
        const authenticateURL = new URL(this.authenticatePath, window.location.href);

        const nextUrl = currentURL.searchParams.get('next');
        if (nextUrl) {
          // takes nextUrl from the query string on the current browser URL
          // (which should be /two-factor-webauthn) and pass it through to
          // the POST. put it in a query string so it's consistent with how
          // the other login flows manage it
          authenticateURL.searchParams.set('next', nextUrl);
        }

        return this.postWebAuthnCreateResponse(
          credential, this.$module.dataset.csrfToken
        );
      })
      .then(response => {
        if (!response.ok) {
          throw Error(response.statusText);
        }

        return response.arrayBuffer();
      })
      .then(cbor => {
        return Promise.resolve(window.CBOR.decode(cbor));
      })
      .then(data => {
        window.location.assign(data.redirect_url);
      })
      .catch(error => {
        console.error(error);
        // some browsers will show an error dialogue for some
        // errors; to be safe we always display an error message on the page.
        new ErrorBanner().showBanner();
      });
  }
  postWebAuthnCreateResponse(credential, csrf_token) {
    return fetch(this.authenticatePath, {
      method: 'POST',
      headers: { 'X-CSRFToken': csrf_token },
      body: window.CBOR.encode({
        credentialId: new Uint8Array(credential.rawId),
        authenticatorData: new Uint8Array(credential.response.authenticatorData),
        signature: new Uint8Array(credential.response.signature),
        clientDataJSON: new Uint8Array(credential.response.clientDataJSON),
      })
    });
  }
}

export default AuthenticateSecurityKey;
