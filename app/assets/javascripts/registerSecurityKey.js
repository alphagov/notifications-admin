(function(window) {
  "use strict";

  window.GOVUK.Modules.RegisterSecurityKey = function() {
    this.start = function(component) {
      $(component)
        .on('click', function(event) {
          event.preventDefault();

          fetchWebAuthnCreateOptions()
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
              // there may be other kinds of error we should catch here
              // https://github.com/w3c/webauthn/issues/876
              if (error instanceof DOMException) {
                console.error(error);
                // not all browsers show an error dialogue, so to be safe
                // we manually pop one open here (to be improved in future!)
                alert('Error communicating with device.\n\n' + error.message);
              } else {
                // for web requests we need to manually alert the user
                // $.ajax seems to log by itself, but that's not visible
                alert('Error during registration. Please try again.');
              }
            });
        });
    };
  };

  function fetchWebAuthnCreateOptions() {
    var xhrOverride = new XMLHttpRequest();
    xhrOverride.responseType = 'arraybuffer';

    return $.ajax({
      url: '/webauthn/register',
      xhr: () => xhrOverride,
      dataType: 'x-binary',
      converters: { '* x-binary': (value) => value }
    });
  }

  function postWebAuthnCreateResponse(response, csrf_token) {
    return $.ajax({
      url: '/webauthn/register',
      method: 'POST',
      headers: {
        'X-CSRFToken': csrf_token
      },
      processData: false,
      contentType: 'application/cbor',
      data: window.CBOR.encode({
        attestationObject: new Uint8Array(response.attestationObject),
        clientDataJSON: new Uint8Array(response.clientDataJSON),
      })
    });
  }
})(window);
