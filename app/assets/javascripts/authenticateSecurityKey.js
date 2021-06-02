(function (window) {
  "use strict";

  window.GOVUK.Modules.AuthenticateSecurityKey = function () {
    this.start = function (component) {
      $(component)
        .on('click', function (event) {
          event.preventDefault();

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
              return fetch('/webauthn/authenticate', {
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
              if (response.status === 403) {
                // flask will have `flash`ed an error message up
                window.location.reload();
                return;
              }

              return response.arrayBuffer()
                .then(cbor => {
                  return Promise.resolve(window.CBOR.decode(cbor));
                })
                .catch(() => {
                  throw Error(response.statusText);
                })
                .then(data => {
                  window.location.assign(data.redirect_url);
                });
            })
            .catch(error => {
              console.error(error);
              // some browsers will show an error dialogue for some
              // errors; to be safe we always pop up an alert
              var message = error.message || error;
              alert('Error during authentication.\n\n' + message);
            });
        });
    };
  };
}) (window);
