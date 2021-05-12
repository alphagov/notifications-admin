(function(window) {
  "use strict";

  window.GOVUK.Modules.RegisterSecurityKey = function() {
    this.start = function(component) {
      $(component)
        .on('click', function(event) {
          event.preventDefault();

          fetch('/webauthn/register')
            .then((response) => {
              return response.arrayBuffer();
            })
            .then((data) => {
              var options = window.CBOR.decode(data);
              // triggers browser dialogue to select authenticator
              return window.navigator.credentials.create(options);
            })
            .then((credential) => {
              return postWebAuthnCreateResponse(
                credential.response, component.data('csrfToken')
              );
            })
            .then(() => {
              window.location.reload();
            })
            .catch((error) => {
              console.error(error);
              // some browsers will show an error dialogue for some
              // errors; to be safe we always pop up an alert
              var message = error.message || error;
              alert('Error during registration.\n\n' + message);
            });
        });
    };
  };

  function postWebAuthnCreateResponse(response, csrf_token) {
    return fetch('/webauthn/register', {
      method: 'POST',
      headers: { 'X-CSRFToken': csrf_token },
      body: window.CBOR.encode({
        attestationObject: new Uint8Array(response.attestationObject),
        clientDataJSON: new Uint8Array(response.clientDataJSON),
      })
    });
  }
})(window);
