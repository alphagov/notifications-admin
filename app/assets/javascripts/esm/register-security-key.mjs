import { isSupported } from 'govuk-frontend';

class RegisterSecurityKey {
  constructor($module) {
    if (!isSupported()) {
      return this;
    }
    this.registerAuthenticationEndpoint = '/webauthn/register';
    this.$module = $module;

    this.$module.addEventListener('click', this.registerKey.bind(this));
  }

  async registerKey(e) {
    e.preventDefault();

    // hide any existing error prompt
    window.GOVUK.ErrorBanner.hideBanner();

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
    return window.CBOR.decode(data);
  }

  createCredential(options) {
    // triggers browser dialogue to select authenticator
    return window.navigator.credentials.create(options);
  }

  postCredential(credential) {
    return fetch(this.registerAuthenticationEndpoint, {
      method: 'POST',
      headers: { 'X-CSRFToken': this.$module.dataset.csrfToken },
      body: window.CBOR.encode({
        attestationObject: new Uint8Array(credential.response.attestationObject),
        clientDataJSON: new Uint8Array(credential.response.clientDataJSON),
      })
    });
  }

  handleCredentialResponse(response) {
    if (!response.ok) {
      throw Error(response.statusText);
    }
    window.location.reload();
  }

  handleError(error) {
    console.error(error);
    // some browsers will show an error dialogue for some errors;
    // to be safe we always display an error message on the page.
    window.GOVUK.ErrorBanner.showBanner();
  }
}

export default RegisterSecurityKey;
