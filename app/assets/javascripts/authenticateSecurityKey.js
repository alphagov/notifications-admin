(function (window) {
  "use strict";

  window.GOVUK.Modules.AuthenticateSecurityKey = function () {
    this.start = function (component) {
      $(component)
        .on('click', function (event) {
          event.preventDefault();

          // hide any existing error prompt
          window.GOVUK.ErrorBanner.hideBanner();

          fetch('/webauthn/authenticate')
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
              const authenticateURL = new URL('/webauthn/authenticate', window.location.href);

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
                headers: { 'X-CSRFToken': component.data('csrfToken') },
                body: window.CBOR.encode({
                  credentialId: new Uint8Array(credential.rawId),
                  authenticatorData: new Uint8Array(credential.response.authenticatorData),
                  signature: new Uint8Array(credential.response.signature),
                  clientDataJSON: new Uint8Array(credential.response.clientDataJSON),
                })
              });
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
              window.GOVUK.ErrorBanner.showBanner();
            });
        });
    };
  };
}) (window);
