let stripUUIDs = string => string.replace(
  /[a-f0-9]{8}-?[a-f0-9]{4}-?4[a-f0-9]{3}-?[89ab][a-f0-9]{3}-?[a-f0-9]{12}/g, '…'
);

(function(Modules) {
  "use strict";

  function sendEvent(category, action, label) {

    if (!ga) return;
    ga('send', 'event', category, action, label);

  }

  function sendVirtualPageView(path) {

    if (!ga) return;
    ga('send', 'pageview', stripUUIDs('/virtual' + path));

  }

  Modules.TrackError = function() {

    this.start = component => sendEvent(
      'Error',
      $(component).data('error-type'),
      $(component).data('error-label')
    );

  };

  Modules.TrackEvent = function() {

    this.start = component => sendEvent(
      $(component).data('event-category'),
      $(component).data('event-action'),
      $(component).data('event-label')
    );

  };

  Modules.TrackFormSubmission = function() {

    this.start = component => {

      $(component).on('submit', function() {

        let formData = $('input[name!=csrf_token]', this).serialize();
        sendVirtualPageView(window.location.pathname + '?' + formData);

      });
    };

  };

})(window.GOVUK.Modules);
