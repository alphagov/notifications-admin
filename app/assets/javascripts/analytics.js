(function(Modules) {
  "use strict";

  if (!ga) return;

  function sendEvent(category, action, label) {

    ga('send', 'event', category, action, label);

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

})(window.GOVUK.Modules);
